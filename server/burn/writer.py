"""L'incisione vera, e i modi in cui puo' andare storta.

E' il punto di non ritorno del programma. Dappertutto altrove un errore
significa riprovare; qui significa un CD-R consumato. Per questo meta' del
modulo non incide ma spiega: ``_hresult`` e ``_spiega_errore`` traducono i
numeri esadecimali che restituisce IMAPI2 in una frase che dica cosa fare -
abbassare la velocita', cambiare disco, chiudere il programma che tiene
occupata l'unita'.
"""
from __future__ import annotations

from rich.progress import (
    Progress, SpinnerColumn, BarColumn, MofNCompleteColumn, TextColumn,
    TaskProgressColumn, TimeElapsedColumn,
)
from rich.table import Column

from server.config import i18n
from server.state.progress import Spiato
from server.utils.console import SYM_ARROW, console, setup_logger
from server.burn.redbook import velocita_x

t = i18n.t

log = setup_logger('burndex', 'burndex.log')

# Le stesse due di drives.py: se pywin32 non c'e', qui non si incide
# niente, e il perche' lo dice la sezione Masterizzazione.
try:
    import pythoncom          # noqa: F401
    import win32com.client    # noqa: F401
except ImportError:
    pythoncom = None          # type: ignore[assignment]
    win32com = None           # type: ignore[assignment]

# Codice IMAPI del comando andato in timeout (HRESULT 0xC0AA020D come intero
# con segno). E' l'errore che si vede quando l'unita' smette di rispondere a
# meta' scrittura, tipicamente perche' resta senza alimentazione.
HR_COMMAND_TIMEOUT = -1062600179

DEFAULT_SPEED_X = 8       # Scrittura lenta = incisioni piu' nette = piu'


def _progress(descrizione_larghezza: int = 32) -> Progress:
    """Barra di avanzamento uniforme per decodifica e scrittura.

    La colonna della descrizione ha larghezza fissa: senza, ogni titolo di
    lunghezza diversa sposterebbe la barra a destra e a sinistra a ogni
    traccia, con un effetto di tremolio molto sgradevole.

    E' uno ``Spiato`` e non un ``Progress`` per una ragione sola: a terminale
    non cambia niente, ma quando a chiamare e' l'interfaccia grafica i numeri
    contati qui arrivano anche alla sua barra. Vedi server/state/progress.
    """
    return Spiato(
        SpinnerColumn(style='bright_blue'),
        TextColumn('{task.description}', table_column=Column(
            width=descrizione_larghezza, no_wrap=True, overflow='ellipsis')),
        BarColumn(bar_width=None, style='grey37',
                  complete_style='bright_blue', finished_style='bright_green'),
        TaskProgressColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
    )


def _crea_writer(recorder, velocita: int | None):
    """Crea il writer Track-At-Once e vi imposta la velocita' di scrittura.

    ``velocita`` e' un valore grezzo in settori/secondo gia' scelto tra quelli
    che l'unita' dichiara, oppure None per lasciar decidere il masterizzatore.
    """
    audio = win32com.client.Dispatch('IMAPI2.MsftDiscFormat2TrackAtOnce')
    audio.ClientName = 'BurnDex'
    audio.Recorder = recorder

    if not audio.IsCurrentMediaSupported(recorder):
        console.print(t('disc.not_writable_audio'))
        return None

    if velocita is None:
        console.print(t('speed.writing_at', arrow=SYM_ARROW,
                        speed=t('common.automatic')))
        return audio

    try:
        audio.SetWriteSpeed(velocita, False)
        console.print(t('speed.writing_at', arrow=SYM_ARROW, speed=velocita_x(velocita)))
    except Exception as exc:
        log.warning('SetWriteSpeed(%d settori/s) rifiutata: %s', velocita, exc)
        console.print(t('speed.refused'))

    return audio


def _hresult(exc: Exception) -> int | None:
    """Estrae il codice di errore COM da un'eccezione pywintypes.com_error.

    Le eccezioni COM di pywin32 hanno una struttura annidata e poco comoda:
    il codice specifico che identifica il guasto — quello che permette di
    distinguere "disco assente" da "unita' che non risponde" — sta nel sesto
    elemento della tupla contenuta nel terzo argomento.

    L'accesso e' protetto perche' questa funzione riceve anche eccezioni che
    con COM non c'entrano nulla: in quel caso ritorna None e il chiamante
    ripiega sul messaggio grezzo.
    """
    try:
        return exc.args[2][5]
    except (AttributeError, IndexError, TypeError):
        return None


def _spiega_errore(exc: Exception) -> None:
    """Traduce gli errori IMAPI ricorrenti in una diagnosi utile.

    Il messaggio grezzo di IMAPI dice cosa non ha funzionato ma non perche':
    un timeout sul primo comando di scrittura, in particolare, quasi mai
    dipende dal disco e quasi sempre dall'alimentazione dell'unita'.
    """
    codice = _hresult(exc)
    if codice == HR_COMMAND_TIMEOUT:
        console.print(t('burn.timeout'))
        console.print(t('burn.timeout_why'))
    else:
        console.print(t('burn.write_error', error=exc))


def _masterizza(audio, pcm_files: list[str], nomi: list[str]) -> tuple[bool, int]:
    """Scrive le tracce sul disco e lo finalizza.

    Ritorna (esito, tracce effettivamente scritte): il secondo valore non e'
    ridondante, perche' un guasto a meta' lascia il disco con solo una parte
    dei brani e il riepilogo deve dire il vero.
    """
    audio.PrepareMedia()
    scritte = 0
    esito = True
    try:
        with _progress() as progress:
            task = progress.add_task(t('burn.starting'), total=len(pcm_files))
            for pcm, nome in zip(pcm_files, nomi):
                progress.update(task, description=nome)
                # Lo stream va costruito in memoria: IMAPI2 vuole un IStream,
                # non un percorso. Un brano occupa ~50-100 MB, quindi si
                # carica una traccia alla volta e non tutto il disco.
                stream = pythoncom.CreateStreamOnHGlobal()
                with open(pcm, 'rb') as fh:
                    stream.Write(fh.read())
                stream.Seek(0, 0)
                audio.AddAudioTrack(stream)
                scritte += 1
                progress.advance(task)
            progress.update(task, description=t('burn.all_written'))
    except Exception as exc:
        log.exception('Masterizzazione fallita dopo %d tracce', scritte)
        _spiega_errore(exc)
        esito = False
    finally:
        # Chiude la sessione e finalizza: da qui il disco e' definitivo.
        # Va tentata anche in caso di errore, altrimenti l'unita' resta
        # bloccata in accesso esclusivo. Se pero' e' stata proprio l'unita'
        # a sparire, anche questa fallisce: non deve coprire l'errore vero.
        try:
            console.print(t('burn.closing'))
            audio.ReleaseMedia()
        except Exception as exc:
            log.warning('ReleaseMedia fallita: %s', exc)
            console.print(t('burn.close_failed'))

    return esito, scritte
