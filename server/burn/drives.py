"""Quali masterizzatori ci sono, cosa hanno dentro, e se va bene cosi'.

Tutto quello che si sa dell'hardware prima di scrivere una riga sul disco:
l'elenco delle unita', il tipo di supporto inserito, se e' vuoto o
riscrivibile, e che computer sia questo - perche' su un portatile a batteria
incidere a 48x e' un modo efficiente di rovinare un CD-R.

Da qui in giu' si passa per COM e IMAPI2, che sono API di Windows: su altri
sistemi questo modulo si importa ma non trova niente, ed e' il comportamento
voluto - BurnDex e' l'unico dei quattro mestieri che non e' multipiattaforma,
e lo dice invece di fallire a meta'.
"""
from __future__ import annotations

from rich.box import ROUNDED
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from server.config import i18n
from server.utils.console import LARGHEZZA, console, setup_logger
from server.burn.redbook import SECTORS_PER_SECOND

t = i18n.t

log = setup_logger('burndex', 'burndex.log')

# Senza pywin32 non c'e' nessun modo di chiedere a Windows quali unita' ci
# siano: qui non si fallisce, si registra che non si sa, e la sezione
# Masterizzazione lo dice appena si entra invece di scoprirlo al primo clic.
# Basta chiedere win32com.client, che di pythoncom ha bisogno per caricarsi:
# se arriva quello, c'e' tutto il pacchetto.
try:
    import win32com.client
    _HAS_PYWIN32 = True
except ImportError:
    win32com = None           # type: ignore[assignment]
    _HAS_PYWIN32 = False

# IMAPI_MEDIA_PHYSICAL_TYPE: solo i valori che possono capitare in un
# masterizzatore CD/DVD di consumo.
# Le sigle commerciali (CD-R, DVD+RW, BD-RE...) sono internazionali e restano
# identiche in ogni lingua. Solo le due voci generiche vanno tradotte, e per
# quelle qui c'e' la chiave di catalogo invece del testo.
MEDIA_TYPES = {
    0: 'media.unknown', 1: 'CD-ROM', 2: 'CD-R', 3: 'CD-RW',
    4: 'DVD-ROM', 5: 'DVD-RAM', 6: 'DVD+R', 7: 'DVD+RW',
    8: 'DVD+R DL', 9: 'DVD-R', 10: 'DVD-RW', 11: 'DVD-R DL',
    12: 'media.disc', 13: 'BD-ROM', 14: 'BD-R', 15: 'BD-RE',
}

# Solo su questi tre supporti esiste il formato Red Book: un "CD audio" su
# DVD o Blu-ray non e' definito da nessuno standard, e nessun lettore da auto
# saprebbe cosa farsene.
TIPI_CD = frozenset({1, 2, 3})


# I tre a cui serve un nome, perche' _valuta_supporto li distingue uno per
# uno: un CD-ROM stampato non si scrive, un CD-RW pieno si cancella, un
# CD-R pieno e' finito.
CD_ROM, CD_R, CD_RW = 1, 2, 3

# Win32_SystemEnclosure.ChassisTypes: i valori che indicano una macchina
# trasportabile. Sono quelle che di norma non hanno un lettore interno e che
# alimentano il masterizzatore esterno dalla sola porta dati.
CHASSIS_PORTATILE = frozenset({8, 9, 10, 11, 12, 14, 18, 21, 30, 31, 32})


CHASSIS_FISSO = frozenset({3, 4, 5, 6, 7, 13, 15, 16, 17, 23, 24})

def elenca_unita() -> list:
    """Restituisce un MsftDiscRecorder2 inizializzato per ogni masterizzatore.

    E' il primo dei cinque passaggi IMAPI2. ``MsftDiscMaster2`` e' solo un
    elenco di identificativi opachi: da soli non dicono nulla, e per sapere
    marca, modello e lettera di unita' bisogna costruire un
    ``MsftDiscRecorder2`` e inizializzarlo su ciascuno. Qui si fa una volta
    sola e si restituiscono gli oggetti pronti.

    Una lista vuota significa che nessun masterizzatore e' raggiungibile: o
    non ce n'e', oppure quello esterno si e' scollegato — succede davvero,
    dopo un'interruzione di corrente durante la scrittura.
    """
    master = win32com.client.Dispatch('IMAPI2.MsftDiscMaster2')
    unita = []
    for i in range(master.Count):
        rec = win32com.client.Dispatch('IMAPI2.MsftDiscRecorder2')
        rec.InitializeDiscRecorder(master.Item(i))
        unita.append(rec)
    return unita


def _info_sistema() -> dict:
    """Riconosce il tipo di computer e le unita' ottiche presenti.

    Serve a rispondere prima ancora di provare: questo PC puo' masterizzare
    da solo o serve un lettore esterno? E se e' esterno, e' collegato in USB
    e quindi esposto al calo di tensione che fa fallire le scritture?

    Ritorna {'macchina', 'modello', 'unita': {lettera: {'nome', 'connessione'}}}.
    Un fallimento di WMI non e' bloccante: si perde solo il consiglio.
    """
    info = {'macchina': 'sconosciuta', 'modello': '', 'unita': {}}
    try:
        wmi = win32com.client.GetObject('winmgmts:')

        for enclosure in wmi.InstancesOf('Win32_SystemEnclosure'):
            for tipo in (enclosure.ChassisTypes or ()):
                if tipo in CHASSIS_PORTATILE:
                    info['macchina'] = 'portatile'
                elif tipo in CHASSIS_FISSO:
                    info['macchina'] = 'fisso'

        for sistema in wmi.InstancesOf('Win32_ComputerSystem'):
            info['modello'] = (sistema.Model or '').strip()

        for unita in wmi.InstancesOf('Win32_CDROMDrive'):
            lettera = (unita.Drive or '').rstrip('\\')
            # Le unita' esterne si riconoscono dal ramo USBSTOR dell'albero
            # PnP; quelle interne stanno sotto SCSI o IDE.
            pnp = (unita.PNPDeviceID or '').upper()
            info['unita'][lettera] = {
                'nome': (unita.Caption or '').strip(),
                'connessione': 'USB' if pnp.startswith('USBSTOR') else 'interna',
            }
    except Exception as exc:
        log.debug('Ricognizione WMI fallita: %s', exc)

    return info


def _pannello_sistema(info: dict) -> None:
    """Scheda con tipo di computer, unita' ottiche e cosa serve per masterizzare.

    Apre la modalita' ``--info`` e risponde alla domanda che viene prima di
    ogni altra: questo computer puo' masterizzare da solo, oppure serve un
    lettore esterno? Su un portatile recente la risposta e' quasi sempre la
    seconda, e conviene saperlo prima di cercare un'unita' che non c'e'.

    Mostra i dati grezzi; il giudizio su cosa farne e' delegato a
    ``_consiglio_sistema``, chiamata subito dopo.
    """
    tabella = Table(show_header=False, box=None, padding=(0, 1), expand=True)
    tabella.add_column('Campo', style='dim_label', no_wrap=True, width=14)
    tabella.add_column('Valore', style='white', ratio=1, overflow='ellipsis')

    macchina = {'portatile': t('system.laptop'), 'fisso': t('system.desktop')}.get(
        info['macchina'], t('system.unknown_type'))
    modello = f"  [dim]{escape(info['modello'])}[/dim]" if info['modello'] else ''
    tabella.add_row(t('system.computer'), f'[bold]{macchina}[/bold]{modello}')

    if not info['unita']:
        tabella.add_row(t('system.cd_drive'), t('system.none_detected'))
    for lettera, unita in sorted(info['unita'].items()):
        esterna = unita['connessione'] == 'USB'
        tabella.add_row(
            t('system.drive_label', letter=escape(lettera)),
            f"[bold]{escape(unita['nome'])}[/bold]\n"
            + (t('system.usb_external') if esterna else t('system.internal')))

    console.print()
    console.print(Panel(
        tabella,
        title=t('system.panel_title'),
        border_style='bright_blue',
        box=ROUNDED,
        width=LARGHEZZA,
        padding=(1, 1),
    ))

    _consiglio_sistema(info)


def _consiglio_sistema(info: dict) -> None:
    """Stampa cosa serve per masterizzare, in base a quello che c'e'.

    Tre esiti, tre consigli diversi. Senza alcun lettore serve un
    masterizzatore esterno USB, e vale la pena dirlo esplicitamente perche'
    su un portatile senza unita' ottica il programma sembrerebbe rotto. Con
    un'unita' USB si avverte del problema di alimentazione **prima** della
    scrittura: e' la causa piu' frequente di masterizzazioni interrotte a
    meta', e i tre rimedi sono elencati in ordine di efficacia. Con un'unita'
    interna si conferma solo che non servono precauzioni.

    L'avviso resta legato alla connessione e non al tipo di computer: anche
    un PC fisso puo' avere un masterizzatore USB, e anche un portatile puo'
    averne uno interno.
    """
    if not info['unita']:
        console.print(t('system.advice_none'))
        return

    usb = [l for l, u in info['unita'].items() if u['connessione'] == 'USB']
    console.print(t('system.advice_usb') if usb else t('system.advice_internal'))


def _valuta_supporto(supporto: dict) -> tuple[bool, str, str]:
    """Decide se il disco inserito puo' diventare un CD audio.

    Ritorna (utilizzabile, descrizione, spiegazione). La distinzione serve
    perche' i motivi per cui un disco non va bene sono molto diversi tra
    loro, e ognuno ha un rimedio diverso: comprarne uno nuovo, cancellarlo,
    o rendersi conto di aver inserito un DVD.
    """
    codice = supporto['codice']
    tipo = supporto['tipo']

    if codice == 0:
        return False, t('disc.unknown_type'), t('disc.unknown_type_why')

    if codice not in TIPI_CD:
        return False, f'{tipo}', t('disc.not_a_cd_why')

    if codice == CD_ROM:
        return False, t('disc.pressed_cdrom'), t('disc.pressed_cdrom_why')

    if not supporto['vuoto']:
        if codice == CD_RW:
            return False, t('disc.cdrw_written'), t('disc.cdrw_written_why')
        return False, t('disc.cdr_written'), t('disc.cdr_written_why')

    if codice == CD_RW:
        return True, t('disc.cdrw_blank'), t('disc.cdrw_blank_why')

    return True, t('disc.cdr_blank'), ''


def nome_unita(rec) -> str:
    """Marca e modello del masterizzatore.

    IMAPI2 espone i due campi separati e con spazi di riempimento in coda,
    perche' arrivano dalla stringa di identificazione SCSI, che ha campi a
    lunghezza fissa. Qui vengono ripuliti e uniti nell'etichetta usata in
    tutte le tabelle e le schede, cosi' la stessa unita' compare ovunque con
    lo stesso nome.
    """
    return f'{rec.VendorId.strip()} {rec.ProductId.strip()}'


def _lettera_unita(rec) -> str:
    """Lettera assegnata all'unita', senza la barra finale.

    La barra rovescia va tolta: nei markup di Rich e' il carattere di escape,
    e una stringa che finisce con '\\' si mangerebbe il tag successivo.
    """
    return (rec.VolumePathNames or ('',))[0].rstrip('\\') or '-'


def _leggi_supporto(recorder) -> dict | None:
    """Legge tipo, stato e capacita' del disco inserito, senza impegnare l'unita'.

    Le stesse proprieta' sul writer Track-At-Once esistono, ma sono leggibili
    solo dopo PrepareMedia(), che pero' apre gia' la sessione di scrittura:
    troppo tardi per decidere se il disco va bene. Il formatter dati invece
    risponde appena gli si assegna il recorder, quindi lo si usa come sonda
    di sola lettura e si tiene il Track-At-Once per la scrittura vera.

    Ritorna None se non c'e' un disco leggibile nell'unita'.
    """
    sonda = win32com.client.Dispatch('IMAPI2.MsftDiscFormat2Data')
    sonda.ClientName = 'BurnDex'
    try:
        sonda.Recorder = recorder
        return {
            'codice': int(sonda.CurrentPhysicalMediaType),
            # Le sigle passano attraverso t() invariate — una chiave assente
            # dal catalogo viene restituita tale e quale — mentre le due voci
            # generiche vengono tradotte.
            'tipo': t(MEDIA_TYPES.get(sonda.CurrentPhysicalMediaType, '?')),
            'vuoto': bool(sonda.MediaPhysicallyBlank),
            'settori': int(sonda.FreeSectorsOnMedia),
            # Valori grezzi in settori/secondo, come li dichiara l'unita'.
            'velocita': sorted({int(v) for v in (sonda.SupportedWriteSpeeds or ())}),
        }
    except Exception as exc:
        log.debug('Lettura supporto fallita: %s', exc)
        return None


def _scegli_velocita(supportate: list[int], richiesta_x: int) -> int | None:
    """La velocita' supportata piu' vicina a quella richiesta, senza superarla.

    ``supportate`` e ``richiesta_x`` sono in unita' diverse: le prime in
    settori/secondo come le dichiara l'unita', la seconda in multipli di 1x
    come la scrive l'utente. Le unita' espongono pochi gradini discreti (qui
    solo 8x e 24x), quindi chiedere i 4x non rallenta: fa fallire la chiamata.
    Si scende al gradino disponibile piu' vicino, e se non ce n'e' nessuno
    sotto la soglia si prende il piu' lento in assoluto.

    Ritorna None se l'unita' non dichiara velocita': in quel caso si lascia
    fare a lei.
    """
    if not supportate:
        return None
    soglia = richiesta_x * SECTORS_PER_SECOND
    ammesse = [v for v in supportate if v <= soglia]
    return max(ammesse) if ammesse else min(supportate)
