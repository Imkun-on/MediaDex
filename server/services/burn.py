"""La procedura di masterizzazione, dall'inizio alla fine.

Una sola, per due interfacce
    Questo e' l'unico modulo di ``server/`` che parla con un terminale, e non
    e' una dimenticanza: e' una scelta, e vale la pena spiegarla.

    La procedura e' una - leggere la cartella, ordinare, misurare, scegliere
    le tracce, scegliere unita' e velocita', confermare, decodificare,
    incidere - e i due modi di usarla differiscono solo in QUANTO viene
    chiesto. Con ``auto_si=True`` non si chiede niente: tutte le tracce,
    velocita' da parametro, nessuna conferma. E' la via che prende la
    finestra. Senza, ogni passaggio mostra un pannello e si puo' annullare.

    Averne due copie - una silenziosa per la finestra e una a pannelli per il
    terminale - vorrebbe dire due sequenze da tenere allineate su un'operazione
    che consuma un disco quando sbaglia. Una sola, con i rami guardati da
    ``auto_si``, e' piu' sicura di due pulite.

Cosa garantisce che la finestra non si pianti
    Ogni ``chiedi()`` di questo file sta sotto un ``if not auto_si``, e l'unico
    controllo che chiedeva anche senza - lo spazio per i file temporanei - ha
    il suo ``muto=True``. La finestra passa da questo codice senza che una sola
    riga si metta in attesa di una risposta che nessuno puo' dare.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile

from rich.align import Align
from rich.box import DOUBLE, HEAVY_HEAD, ROUNDED
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from server.config import i18n
from server.utils.console import (
    LARGHEZZA, SYM_ARROW, SYM_FAIL, SYM_OK, chiedi, console, passo,
    setup_logger)
from server.burn.redbook import (
    CD_NOMINALE, PREGAP_SECTORS, SAFE_MINUTES, SECTORS_PER_SECOND,
    format_duration, sectors_to_minutes, settori_totali, velocita_x)
from server.burn.order import durata_traccia, ordina_tracce
from server.burn.encode import (
    _decodifica, _guadagno_livellamento, _misura_loudness)
from server.burn.drives import (
    _HAS_PYWIN32, _info_sistema, _leggi_supporto, _lettera_unita,
    _scegli_velocita, _valuta_supporto, elenca_unita, nome_unita)
from server.burn.writer import (
    DEFAULT_SPEED_X, _crea_writer, _masterizza, _progress, pythoncom)

t = i18n.t

log = setup_logger('burndex', 'burndex.log')

SYM_DISC = '[accent]💿[/accent]'


                          # compatibilita' con autoradio e lettori vecchi
MIN_FREE_MB = 1200        # Spazio temporaneo per il PCM: ~10 MB al minuto


def _check_temp_space(muto: bool = False) -> bool:
    """Controlla lo spazio per i file PCM temporanei (~850 MB per un CD pieno).

    Come in AudioDex: avvisa e chiede conferma, ma un errore di lettura non
    blocca nulla. Meglio tentare che fermarsi per un controllo accessorio.

    Con ``muto`` l'avviso resta e la domanda no: chi chiama senza un terminale
    - l'interfaccia grafica - non potrebbe rispondere, e resterebbe fermo
    davanti a una richiesta invisibile. Si tira dritto perche' questo e'
    davvero un controllo accessorio: se lo spazio non basta se ne accorge la
    decodifica, che fallisce dicendo su quale traccia.
    """
    try:
        free_mb = shutil.disk_usage(tempfile.gettempdir()).free / 1048576
        if free_mb < MIN_FREE_MB:
            log.warning('Spazio temporaneo basso: %.0f MB liberi', free_mb)
            console.print(t('temp.low', free=f'{free_mb:.0f}', need=MIN_FREE_MB))
            return True if muto else i18n.is_yes(chiedi(t('common.continue')))
        return True
    except OSError:
        return True


def _barra_capienza(usati: int, capienza: int, larghezza: int = 40) -> Text:
    """Indicatore grafico di quanto disco si occupa.

    Un numero in minuti dice poco a chi non ha in mente che un CD ne regge 80:
    la barra rende immediato quanto margine resta, e cambia colore man mano
    che ci si avvicina al limite oltre il quale i lettori iniziano a sbagliare.
    """
    quota = min(usati / capienza, 1.0) if capienza else 0.0
    pieni = round(quota * larghezza)

    if usati >= SAFE_MINUTES * 60 * SECTORS_PER_SECOND:
        colore = 'red'
    elif quota >= 0.85:
        colore = 'yellow'
    else:
        colore = 'bright_green'

    barra = Text()
    barra.append('█' * pieni, style=colore)
    barra.append('░' * (larghezza - pieni), style='grey37')
    barra.append(f'  {sectors_to_minutes(usati):.1f}', style='bold white')
    barra.append(f" / {sectors_to_minutes(capienza):.0f} {t('common.min')}", style='dim')
    return barra


def _mostra_scaletta(tracce: list[str], durate: list[float | None],
                     criterio: str, titolo: str, capienza: int = CD_NOMINALE) -> int:
    """Stampa la scaletta numerata e ritorna i settori totali stimati.

    Con ``capienza`` (settori del disco inserito) aggiunge sotto la tabella
    la barra di riempimento: e' il colpo d'occhio che dice se ci sta.
    """
    totale = settori_totali(durate)
    minuti = sectors_to_minutes(totale)
    tabella = Table(
        box=HEAVY_HEAD, border_style='bright_blue', width=LARGHEZZA,
        title=f'[bold bright_magenta]{escape(titolo)}[/bold bright_magenta]',
        title_justify='center', header_style='bold bright_blue',
        show_footer=True, footer_style='bold', padding=(0, 1),
    )
    tabella.add_column('#', style='dim_label', justify='right', width=2, footer='')
    tabella.add_column(t('tracklist.column'), style='white', overflow='ellipsis',
                       no_wrap=True, ratio=1, footer=t('tracklist.count', n=len(tracce)))
    tabella.add_column(t('tracklist.duration'), justify='right', style='info', width=9,
                       footer=f"[bold white]{minuti:.1f} {t('common.min')}[/bold white]")

    for i, (path, dur) in enumerate(zip(tracce, durate), 1):
        tabella.add_row(str(i), escape(os.path.basename(path)), format_duration(dur))

    console.print()
    console.print(tabella)

    if capienza:
        console.print(_barra_capienza(totale, capienza, LARGHEZZA - 24))

    console.print(t('tracklist.order_note', criterion=escape(criterio)))
    return totale


def _seleziona_tracce(tracce: list[str],
                      durate: list[float | None]) -> tuple[list[str], list[float | None]]:
    """Chiede quali tracce mettere sul disco tra quelle elencate.

    Stessa sintassi di selezione di AudioDex: numero singolo (3), intervallo
    (1-5), elenco (1,3,7), 'all' o invio per tutte, 'q' per annullare. Serve
    soprattutto quando una raccolta supera gli 80 minuti: invece di
    rinunciare si sceglie cosa portarsi dietro. L'ordine di masterizzazione
    resta quello della scaletta, non quello in cui si digitano i numeri: su
    un album la sequenza dei brani e' voluta.
    """
    console.print(t('select.hint.burn'))

    while True:
        scelta = chiedi(t('select.prompt')).lower()
        if i18n.is_quit(scelta):
            return [], []
        if not scelta or i18n.is_all(scelta):
            return tracce, durate

        indici: set[int] = set()
        try:
            for parte in scelta.replace(' ', ',').split(','):
                parte = parte.strip()
                if not parte:
                    continue
                if '-' in parte:
                    inizio, fine = parte.split('-', 1)
                    for n in range(int(inizio), int(fine) + 1):
                        if 1 <= n <= len(tracce):
                            indici.add(n - 1)
                else:
                    n = int(parte)
                    if 1 <= n <= len(tracce):
                        indici.add(n - 1)
        except ValueError:
            indici.clear()

        if indici:
            ordinati = sorted(indici)
            return [tracce[i] for i in ordinati], [durate[i] for i in ordinati]

        console.print(t('common.invalid_selection'))


def _pannello_unita(recorder, supporto: dict, sistema: dict | None = None) -> None:
    """Scheda dell'unita' e del disco inserito, pronta per la scrittura.

    Raccoglie in un unico riquadro quello che prima erano righe sparse:
    masterizzatore, tipo di disco, capienza e velocita' disponibili. E' la
    conferma visiva che il programma sta parlando con l'unita' giusta —
    dettaglio non ovvio quando ce n'e' piu' d'una collegata.

    Il parametro ``sistema`` e' opzionale perche' la ricognizione WMI puo'
    fallire o non essere stata fatta: quando c'e', accanto alla lettera
    compare l'etichetta (USB) che segnala un'unita' esterna, cioe' quella
    esposta al calo di tensione in scrittura.
    """
    tabella = Table(show_header=False, box=None, padding=(0, 1), expand=True)
    tabella.add_column('Campo', style='dim_label', no_wrap=True, width=14)
    tabella.add_column('Valore', style='white', ratio=1, overflow='ellipsis')

    lettera = _lettera_unita(recorder)
    collegamento = ((sistema or {}).get('unita', {}).get(lettera) or {}).get('connessione')
    nota_usb = '  [warning](USB)[/warning]' if collegamento == 'USB' else ''

    tabella.add_row(t('drive.burner'),
                    f'[bold]{escape(nome_unita(recorder))}[/bold]'
                    f'  [dim]{escape(lettera)}[/dim]{nota_usb}')
    tabella.add_row(t('drive.disc'),
                    f"[bold]{supporto['tipo']}[/bold] "
                    + t('drive.capacity',
                        min=f"{sectors_to_minutes(supporto['settori']):.0f}"))
    if supporto['velocita']:
        tabella.add_row(t('drive.speed'), '[dim]' +
                        ', '.join(velocita_x(v) for v in supporto['velocita']) + '[/dim]')

    console.print()
    console.print(Panel(
        tabella,
        title=t('drive.panel_title'),
        border_style='bright_blue',
        box=ROUNDED,
        width=LARGHEZZA,
        padding=(1, 1),
    ))


def _chiedi_velocita(supportate: list[int]) -> int | None:
    """Pannello di scelta della velocita', costruito sui valori reali dell'unita'.

    Non si propone una scala fissa: ogni masterizzatore espone i suoi gradini
    (qui 8x e 24x) e chiedere un valore fuori elenco farebbe fallire
    SetWriteSpeed. Invio sceglie la piu' adatta all'ascolto in auto.
    """
    if not supportate:
        return None

    consigliata = _scegli_velocita(supportate, DEFAULT_SPEED_X)

    tabella = Table(box=HEAVY_HEAD, border_style='bright_blue', width=LARGHEZZA,
                    header_style='bold bright_blue', padding=(0, 1))
    tabella.add_column('#', style='dim_label', justify='right', width=2)
    tabella.add_column(t('speed.column'), style='bold white', width=9)
    tabella.add_column(t('speed.result'), overflow='fold', ratio=1)

    for i, v in enumerate(supportate, 1):
        if v == consigliata:
            etichetta = f'{velocita_x(v)} [success]★[/success]'
            nota = t('speed.recommended')
        elif v == max(supportate):
            etichetta = velocita_x(v)
            nota = t('speed.fastest')
        else:
            etichetta = velocita_x(v)
            nota = t('speed.middle')
        tabella.add_row(str(i), etichetta, nota)

    console.print()
    console.print(tabella)

    while True:
        scelta = chiedi(t('speed.prompt', n=len(supportate),
                           default=velocita_x(consigliata)))
        if not scelta:
            return consigliata
        try:
            n = int(scelta)
            if 1 <= n <= len(supportate):
                return supportate[n - 1]
        except ValueError:
            pass
        console.print(t('common.invalid_choice_retry'))


def _card_conferma(recorder, supporto: dict, velocita: int | None,
                   n_tracce: int, settori: int,
                   livella: bool = False, rifila: bool = False) -> bool:
    """Scheda riepilogativa e ultima conferma prima di scrivere.

    E' l'unico punto di non ritorno del programma: da qui in poi il CD-R
    e' consumato comunque, anche se qualcosa va storto a meta'.
    """
    tabella = Table(show_header=False, box=None, padding=(0, 1), expand=True)
    tabella.add_column('Campo', style='dim_label', no_wrap=True, width=16)
    tabella.add_column('Valore', style='white', ratio=1, overflow='ellipsis')

    residuo = supporto['settori'] - settori
    tabella.add_row(t('confirm.drive'), escape(nome_unita(recorder)))
    tabella.add_row(t('confirm.disc'),
                    f"[bold]{supporto['tipo']}[/bold] [dim]{t('common.empty')}[/dim]")
    tabella.add_row(t('confirm.speed'),
                    f"[bold]{velocita_x(velocita) if velocita else t('common.automatic')}[/bold]")
    tabella.add_row(t('confirm.tracks'), f'[bold]{n_tracce}[/bold]')
    trattamenti = []
    if livella:
        trattamenti.append(t('confirm.levelled'))
    if rifila:
        trattamenti.append(t('confirm.trimmed'))
    tabella.add_row(t('confirm.audio'),
                    ' · '.join(trattamenti) if trattamenti
                    else f"[dim]{t('confirm.audio_untouched')}[/dim]")
    tabella.add_row(t('confirm.duration'),
                    f"[bold]{sectors_to_minutes(settori):.1f} {t('common.min')}[/bold]  "
                    + t('confirm.free_after', min=f'{sectors_to_minutes(residuo):.1f}'))

    contenuto = Table.grid(padding=(0, 0), expand=True)
    contenuto.add_column()
    contenuto.add_row(tabella)
    contenuto.add_row('')
    contenuto.add_row(Align.center(_barra_capienza(settori, supporto['settori'], 36)))

    console.print()
    console.print(Panel(
        contenuto,
        title=t('confirm.title'),
        subtitle=t('confirm.subtitle'),
        border_style='bright_magenta',
        box=DOUBLE,
        width=LARGHEZZA,
        padding=(1, 2),
    ))

    return i18n.is_yes(chiedi(t('confirm.prompt')))


def _scegli_unita(indice: int | None = None, muto: bool = False):
    """Sceglie il masterizzatore da usare.

    Con un'unica unita' collegata — il caso normale — la sceglie da sola
    senza chiedere nulla: una domanda con una sola risposta possibile e'
    solo un ostacolo. Con piu' unita' le elenca e lascia decidere.

    Parametri
    ---------
    indice : int | None
        Indice passato da ``--drive``, che salta la domanda anche quando le
        unita' sono piu' d'una: serve agli usi automatizzati, dove un prompt
        bloccherebbe lo script. Un indice fuori intervallo produce un errore
        esplicito invece di ricadere silenziosamente sulla prima unita'.
    muto : bool
        Nessuna domanda, in nessun caso: con piu' unita' collegate prende la
        prima e lo dice. Lo passa chi non ha un terminale a cui rispondere -
        l'interfaccia grafica - dove la domanda finirebbe in un'uscita che
        nessuno vede e il programma resterebbe fermo ad aspettare per sempre
        una riga che non puo' arrivare.

    Ritorna None quando non c'e' nulla da usare o la scelta non e' valida.
    """
    unita = elenca_unita()
    if not unita:
        console.print(t('drive.none_detected'))
        return None

    if indice is not None:
        if not 0 <= indice < len(unita):
            console.print(t('drive.index_missing', index=indice, total=len(unita)))
            return None
        return unita[indice]

    if len(unita) == 1:
        # Senza scelta da fare non serve annunciarla: l'unita' viene comunque
        # mostrata subito dopo dalla scheda _pannello_unita().
        return unita[0]

    console.print(t('drive.available'))
    for i, rec in enumerate(unita):
        console.print(f'  [accent]{i}[/accent]  {escape(nome_unita(rec))}'
                      f'  [dim]{escape(_lettera_unita(rec))}[/dim]')

    if muto:
        # Detto, non chiesto: chi guarda la finestra ha comunque il menu delle
        # unita' e puo' rifare la scelta, mentre qui una domanda sarebbe una
        # attesa senza fine.
        console.print(t('drive.auto_first', name=escape(nome_unita(unita[0]))))
        return unita[0]

    try:
        return unita[int(chiedi(t('drive.which')))]
    except (ValueError, IndexError):
        console.print(t('common.invalid_choice.burn'))
        return None


def _mostra_riepilogo(scritte: int, totali: int, minuti: float, esito: bool) -> None:
    """Pannello finale con l'esito della masterizzazione.

    Riporta le tracce **effettivamente incise**, non quelle preparate: e' la
    differenza che dice se il disco e' ancora utilizzabile. A zero tracce il
    CD-R e' rimasto vergine e si puo' riprovare; a meta' e' compromesso in
    modo irreversibile e va sostituito. Sono due situazioni molto diverse, e
    confonderle costa un disco.

    La durata totale compare solo in caso di successo: dopo un fallimento
    indicherebbe quanto *sarebbe* durato il disco, un dato senza significato
    che si presterebbe a essere letto come quanto e' stato scritto.
    """
    tabella = Table(show_header=False, box=None, padding=(0, 1), expand=True)
    tabella.add_column('Label', style='dim_label', no_wrap=True, width=16)
    tabella.add_column('Value', ratio=1)

    tabella.add_row(t('result.tracks_written'),
                    f'[bold]{scritte}[/bold] ' + t('result.out_of', total=totali))
    if esito:
        tabella.add_row(t('result.total_duration'),
                        f"[bold]{minuti:.1f} {t('common.min')}[/bold]")
        tabella.add_row(t('result.outcome'), f"{SYM_OK} {t('result.finalised')}")
        tabella.add_row('', t('result.ready_to_play'))
    else:
        tabella.add_row(t('result.outcome'), f"{SYM_FAIL} {t('result.aborted')}")
        tabella.add_row(t('result.disc'),
                        t('result.disc_still_good') if scritte == 0
                        else t('result.disc_ruined'))

    console.print()
    console.print(Panel(
        tabella,
        title=t('result.ok_title') if esito else t('result.fail_title'),
        border_style='bright_green' if esito else 'red',
        box=DOUBLE,
        width=LARGHEZZA,
        padding=(1, 2),
    ))


def masterizza_cartella(cartella: str, *, speed_x: int | None, dry_run: bool,
                        auto_si: bool, espelli: bool, indice_unita: int | None,
                        livella: bool = True, rifila: bool = False) -> int:
    """Prepara e masterizza il contenuto di una cartella. Ritorna il codice di uscita.

    Con ``auto_si`` non viene posta alcuna domanda: tutte le tracce, velocita'
    da riga di comando o predefinita, nessuna conferma. Altrimenti il flusso
    e' a pannelli come in AudioDex - scaletta, selezione, velocita', scheda
    finale - e ogni passaggio si puo' annullare.
    """
    nome_raccolta = os.path.basename(cartella) or t('collection.default_name')
    tracce, criterio = ordina_tracce(cartella)
    if not tracce:
        console.print(t('collection.no_audio', path=cartella))
        return 1

    if not auto_si:
        passo(2, 4, t('step.tracklist'))
    # Percorso accorciato in testa invece che mandato a capo: la coda e' la
    # parte che identifica la raccolta, l'inizio si intuisce.
    percorso = (cartella if len(cartella) <= LARGHEZZA
                else '…' + cartella[-(LARGHEZZA - 1):])
    console.print(f'[dim]{escape(percorso)}[/dim]')

    durate = [durata_traccia(p) for p in tracce]
    if any(d is None for d in durate):
        illeggibili = [os.path.basename(p) for p, d in zip(tracce, durate) if d is None]
        console.print(t('tracklist.unreadable', files=', '.join(illeggibili)))
        return 1

    stimati = _mostra_scaletta(tracce, durate, criterio, nome_raccolta)
    minuti = sectors_to_minutes(stimati)

    if not auto_si:
        # La selezione arriva prima di ogni controllo di capienza: se la
        # raccolta sfora gli 80 minuti, la via d'uscita e' proprio scegliere
        # meno tracce, non vedersi respingere l'intera operazione.
        if minuti > SAFE_MINUTES:
            console.print(t('select.too_long_pick',
                            over=f'{minuti - SAFE_MINUTES:.1f}', limit=SAFE_MINUTES))

        scelte, durate_scelte = _seleziona_tracce(tracce, durate)
        if not scelte:
            console.print(t('common.cancelled.burn'))
            return 1

        if len(scelte) != len(tracce):
            tracce, durate = scelte, durate_scelte
            stimati = _mostra_scaletta(
                tracce, durate, criterio,
                t('collection.selection_suffix', name=nome_raccolta))
            minuti = sectors_to_minutes(stimati)

    if minuti > SAFE_MINUTES:
        console.print(t('disc.too_long', limit=SAFE_MINUTES,
                        over=f'{minuti - SAFE_MINUTES:.1f}'))
        console.print(t('disc.trim_hint'))
        return 1

    if not _HAS_PYWIN32:
        if dry_run:
            console.print(t('dry.tracklist_ok', ok=SYM_OK))
            console.print(t('tools.no_pywin32_skip'))
            return 0
        console.print(t('tools.no_pywin32_burn'))
        console.print(t('tools.install_pywin32'))
        return 1

    pythoncom.CoInitialize()

    if not auto_si:
        passo(3, 4, t('step.disc_speed'))

    recorder = _scegli_unita(indice_unita, muto=auto_si)
    if recorder is None:
        return 1

    # Tutti i controlli sul disco vengono prima della decodifica: accorgersi
    # che manca il CD dopo due minuti di ffmpeg sarebbe solo tempo buttato.
    supporto = _leggi_supporto(recorder)
    if supporto is None:
        console.print(t('drive.no_readable_disc'))
        console.print(t('drive.insert_blank'))
        return 1

    liberi = supporto['settori']

    utilizzabile, descrizione, spiegazione = _valuta_supporto(supporto)
    if not utilizzabile:
        console.print(t('disc.unusable', reason=descrizione))
        console.print(f'[dim]{spiegazione}[/dim]\n')
        return 1

    sistema = _info_sistema()
    _pannello_unita(recorder, supporto, sistema)

    if spiegazione:
        console.print(f'[warning]{spiegazione}[/warning]')

    # Avviso sull'alimentazione solo dove serve davvero, cioe' su un'unita'
    # esterna: su una interna sarebbe rumore inutile a ogni masterizzazione.
    if (sistema['unita'].get(_lettera_unita(recorder)) or {}).get('connessione') == 'USB':
        console.print(t('drive.external_warning'))

    if stimati > liberi:
        console.print(t('disc.does_not_fit', need=f'{minuti:.1f}',
                        have=f'{sectors_to_minutes(liberi):.1f}'))
        return 1

    # Velocita': esplicita da riga di comando, altrimenti la si chiede; con
    # --yes si prende la predefinita senza disturbare.
    if speed_x is not None or auto_si:
        velocita = _scegli_velocita(supporto['velocita'], speed_x or DEFAULT_SPEED_X)
    else:
        velocita = _chiedi_velocita(supporto['velocita'])

    if dry_run:
        console.print(t(
            'speed.would_use',
            arrow=SYM_ARROW,
            speed=velocita_x(velocita) if velocita else t('common.automatic'),
            supported=', '.join(velocita_x(v) for v in supporto['velocita']) or t('speed.none'),
        ))
        console.print(t('dry.passed', ok=SYM_OK))
        console.print(t('dry.nothing_touched'))
        return 0

    if not _check_temp_space(muto=auto_si):
        console.print(t('common.cancelled_op'))
        return 1

    if not auto_si:
        passo(4, 4, t('step.burning'))

    audio = _crea_writer(recorder, velocita)
    if audio is None:
        return 1

    # Il livellamento richiede una passata di sola analisi su ogni traccia,
    # prima di decodificare: si deve conoscere la loudness di *tutte* per
    # sapere di quanto spostare ciascuna. E' il motivo per cui e' opzionale —
    # su un disco pieno sono alcuni minuti in piu'.
    guadagni: dict[str, float] = {}
    if livella:
        with _progress() as progress:
            task = progress.add_task(t('burn.measuring'), total=len(tracce))
            for src in tracce:
                progress.update(task, description=os.path.basename(src))
                guadagni[src] = _guadagno_livellamento(_misura_loudness(src))
                progress.advance(task)
            progress.update(task, description=t('burn.measured'))

    with tempfile.TemporaryDirectory(prefix='burndex_') as tmp:
        pcm_files, totale = [], 0
        with _progress() as progress:
            task = progress.add_task(t('burn.decoding'), total=len(tracce))
            for i, src in enumerate(tracce, 1):
                progress.update(task, description=os.path.basename(src))
                dst = os.path.join(tmp, f'{i:03d}.pcm')
                try:
                    totale += _decodifica(src, dst, guadagni.get(src, 0.0),
                                          rifila) + PREGAP_SECTORS
                except subprocess.CalledProcessError as exc:
                    log.error('ffmpeg fallito su %s: %s', src, exc.stderr)
                    console.print(t('burn.decode_failed', file=os.path.basename(src)))
                    return 1
                pcm_files.append(dst)
                progress.advance(task)
            progress.update(task, description=t('burn.decoded'))

        # Ricontrollo con i valori esatti: la stima da ffprobe puo' scostarsi
        # di qualche settore, e qui non c'e' piu' margine di errore.
        if totale > liberi:
            console.print(t('disc.does_not_fit_exact',
                            need=f'{sectors_to_minutes(totale):.1f}',
                            have=f'{sectors_to_minutes(liberi):.1f}'))
            return 1

        if not auto_si:
            if not _card_conferma(recorder, supporto, velocita, len(pcm_files),
                                  totale, livella, rifila):
                console.print(t('confirm.disc_intact'))
                return 1

        nomi = [os.path.basename(p) for p in tracce]
        esito, scritte = _masterizza(audio, pcm_files, nomi)

    _mostra_riepilogo(scritte, len(pcm_files), sectors_to_minutes(totale), esito)

    if esito and espelli:
        try:
            recorder.EjectMedia()
        except Exception as exc:
            log.warning('Espulsione fallita: %s', exc)

    log.info('Masterizzazione %s: %d/%d tracce scritte da %s',
             'riuscita' if esito else 'fallita', scritte, len(pcm_files), cartella)
    return 0 if esito else 1
