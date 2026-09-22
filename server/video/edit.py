"""Le sei operazioni di montaggio: tagliare, unire, convertire.

Cosa le tiene insieme
    Non migliorano niente. E' la differenza con ``remaster.py``, che sta nella
    stessa cartella: li' si rifa' un video per renderlo migliore di com'era,
    qui lo si prende com'e' e lo si mette in un'altra forma. Da questo discende
    tutto il resto, a cominciare dalla scelta che governa ogni operazione: se
    si puo' COPIARE il flusso invece di ricodificarlo, si copia. Copiare e'
    istantaneo e non perde un bit; ricodificare costa minuti e un po' di
    qualita', e si fa solo quando e' inevitabile.

Le sei
    ``taglia``   estrae uno spezzone. Copia, a meno che non si chieda il
                 taglio preciso al fotogramma.
    ``unisci``   mette in fila piu' file. Copia se sono omogenei.
    ``gif``      ricava un'animazione, con la sua tavolozza calcolata.
    ``webp``     come sopra, nel formato che pesa meno.
    ``provino``  una griglia di fotogrammi per capire cosa c'e' dentro.
    ``compat``   rifa' il file nella forma che leggono anche gli apparecchi
                 datati.

Il file non parla con nessuna interfaccia. Stampa sulla console condivisa -
i pannelli di esito, la barra - perche' quello serve al terminale e non
disturba la finestra, che quei pannelli non li vede. Le domande, i menu e gli
argomenti da riga di comando stanno in ``cli/clip.py``.
"""
from __future__ import annotations

import os
import subprocess
import tempfile

from rich.box import ROUNDED
from rich.markup import escape
from rich.panel import Panel
from rich.progress import (
    Progress, SpinnerColumn, BarColumn, TextColumn,
    TaskProgressColumn, TimeElapsedColumn, TimeRemainingColumn,
)
from rich.table import Column, Table

from server.config import i18n
from server.state.progress import Spiato
from server.utils.console import LARGHEZZA, SYM_OK, console, setup_logger
from server.utils.media import VIDEO_EXTS
from server.utils.text import fmt_durata, fmt_peso
from server.video.probe import probe

t = i18n.t

log = setup_logger('clipdex', 'clipdex.log')

# ── Valori di riferimento per GIF e WebP ─────────────────────────────────────
#
# La palette di una GIF ha 256 colori e basta: usare quella generica di FFmpeg
# su un video con sfumature produce una poltiglia di puntini. Calcolarla sul
# filmato costa un passaggio in piu' ed e' l'unico modo di ottenere qualcosa di
# guardabile.
#
# Misurato su tre secondi di un video reale, a 480 px e 15 fps, contro gli
# stessi fotogrammi non ridotti a palette:
#
#     un passaggio, palette generica      24.85 dB    1414 KB
#     due passaggi, palette su misura     26.57 dB    2479 KB
#     due passaggi, dither sierra2_4a     26.56 dB    3133 KB
#     WebP animato                             —       283 KB
#
# Da qui i default: due passaggi (+1.72 dB, si vede), dither ordinato di Bayer
# (il sierra2_4a costa un quarto di peso in piu' senza dare nulla in cambio) e
# la spinta verso il WebP, che a parita' di contenuto pesa quasi nove volte
# meno perche' non e' vincolato ai 256 colori.
GIF_FPS = 15                 # sopra i 15 il peso raddoppia senza guadagno visibile


GIF_LARGHEZZA = 480          # la larghezza e' il fattore che pesa di piu'


GIF_DITHER = 'bayer:bayer_scale=5'


WEBP_QUALITA = 70

# Griglia del provino: 4x4 fotogrammi presi a intervalli regolari bastano a
# capire di cosa parla un file senza aprirlo.
PROVINO_RIGHE = 4


PROVINO_COLONNE = 4


PROVINO_LARGHEZZA = 320

# Qualita' di ricodifica. 20 e' un gradino sotto il 18 di PixDex: qui non si
# sta rimasterizzando, si sta rimontando, e il sorgente e' gia' compresso.
CRF_DEFAULT = 20


def _progress() -> Progress:
    """Barra di avanzamento comune a tutte le operazioni che ricodificano.

    E' uno ``Spiato`` e non un ``Progress`` per una ragione sola: a terminale
    non cambia niente, ma quando a chiamare e' l'interfaccia grafica i
    fotogrammi contati qui arrivano anche alla sua barra. Vedi
    server/state/progress.
    """
    return Spiato(
        SpinnerColumn(style='bright_blue'),
        TextColumn('{task.description}', table_column=Column(
            width=26, no_wrap=True, overflow='ellipsis')),
        BarColumn(bar_width=None, style='grey37',
                  complete_style='bright_blue', finished_style='bright_green'),
        TaskProgressColumn(),
        TextColumn('{task.fields[extra]}', style='dim'),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    )


def _esegui(cmd: list[str], descrizione: str, fotogrammi: int = 0) -> bool:
    """Lancia FFmpeg mostrando l'avanzamento. True se ha funzionato.

    Lo standard error finisce su file: lasciato in una pipe non letta,
    riempirebbe il buffer del sistema operativo e bloccherebbe FFmpeg a meta'
    lavoro senza dire niente.
    """
    log.info('Comando: %s', ' '.join(cmd))
    completo = [*cmd[:-1], '-progress', 'pipe:1', '-nostats', cmd[-1]]

    with tempfile.TemporaryFile(mode='w+', encoding='utf-8', errors='replace') as err:
        proc = subprocess.Popen(completo, stdout=subprocess.PIPE, stderr=err,
                                text=True, encoding='utf-8', errors='replace',
                                bufsize=1)
        with _progress() as prog:
            task = prog.add_task(descrizione, total=fotogrammi or None, extra='')
            try:
                for riga in proc.stdout:
                    riga = riga.strip()
                    if riga.startswith('frame='):
                        try:
                            n = int(riga.split('=', 1)[1])
                        except ValueError:
                            continue
                        prog.update(task, completed=min(n, fotogrammi) if fotogrammi else n)
                    elif riga.startswith('speed='):
                        prog.update(task, extra=riga.split('=', 1)[1].strip())
            except KeyboardInterrupt:
                proc.terminate()
                console.print(t('run.interrupted'))
                return False
            finally:
                proc.stdout.close()

        if proc.wait() != 0:
            err.seek(0)
            righe = err.read().strip().splitlines()
            ultima = righe[-1] if righe else 'exit != 0'
            log.error('FFmpeg fallito: %s', ultima)
            console.print(t('run.failed', reason=escape(ultima[:120])))
            return False
    return True


def _pannello_esito(dst: str, sorgente: dict | None = None,
                    nota: str | None = None) -> None:
    """Riepilogo finale con il file prodotto e quanto pesa."""
    tab = Table(box=ROUNDED, show_header=False, border_style='grey37',
                width=LARGHEZZA, padding=(0, 1))
    tab.add_column(style='dim_label', no_wrap=True, width=18)
    tab.add_column(style='white', overflow='fold')

    nuovo = probe(dst) if os.path.splitext(dst)[1].lower() in VIDEO_EXTS else None
    tab.add_row(t('result.file'), escape(dst))
    peso = os.path.getsize(dst) if os.path.exists(dst) else 0
    if sorgente:
        tab.add_row(t('result.size'),
                    f"{fmt_peso(sorgente['size'])} [dim]→[/dim] "
                    f'[bold]{fmt_peso(peso)}[/bold]')
    else:
        tab.add_row(t('result.size'), f'[bold]{fmt_peso(peso)}[/bold]')
    if nuovo:
        tab.add_row(t('result.video'),
                    f"{nuovo['width']}×{nuovo['height']}  ·  {nuovo['fps']:.0f} fps"
                    f"  ·  {fmt_durata(nuovo['duration'])}")
    if nota:
        tab.add_row('', f'[dim]{nota}[/dim]')

    console.print()
    console.print(Panel(tab, title=f"{SYM_OK} {t('result.title')}", title_align='left',
                        border_style='bright_green', box=ROUNDED,
                        width=LARGHEZZA, padding=(0, 0)))

def taglia(src: str, dst: str, inizio: float, fine: float | None,
           preciso: bool = False, crf: int = CRF_DEFAULT) -> bool:
    """Estrae lo spezzone fra ``inizio`` e ``fine``.

    In copia il taglio si aggancia al fotogramma chiave precedente, perche' i
    pacchetti compressi insieme non si spezzano a meta': l'inizio puo'
    scostarsi di qualche secondo, ma costa un istante e non perde nulla. Con
    ``preciso`` si ricodifica e il taglio cade dove e' stato chiesto.

    Sull'audio la differenza non esiste: i fotogrammi durano millisecondi.
    """
    info = probe(src)
    if not info:
        console.print(t('error.unreadable', path=escape(os.path.basename(src))))
        return False

    durata = (fine - inizio) if fine else max(info['duration'] - inizio, 0)
    if durata <= 0:
        console.print(t('error.empty_range'))
        return False

    cmd = ['ffmpeg', '-hide_banner', '-v', 'error', '-y',
           '-ss', f'{inizio:.3f}', '-t', f'{durata:.3f}', '-i', src]
    if preciso:
        cmd += ['-c:v', 'libx264', '-crf', str(crf), '-preset', 'medium',
                '-c:a', 'aac', '-b:a', '192k']
    else:
        cmd += ['-c', 'copy']
    cmd += ['-avoid_negative_ts', 'make_zero', '-movflags', '+faststart', dst]

    if not _esegui(cmd, t('run.cutting'), int(durata * info['fps'])):
        return False

    nota = t('cut.note_precise') if preciso else t('cut.note_copy')

    # In copia lo scostamento non e' un difetto ma una conseguenza, e va detto
    # con un numero: chiedere quattro secondi e riceverne sette sorprende, e
    # senza una spiegazione sembra un errore del programma. Su un file con i
    # fotogrammi chiave molto distanziati puo' arrivare a dieci secondi.
    if not preciso:
        prodotto = probe(dst)
        if prodotto:
            scostamento = abs(prodotto['duration'] - durata)
            if scostamento > 0.5:
                nota = t('cut.note_drift',
                         chiesta=f'{durata:.1f}', reale=f"{prodotto['duration']:.1f}",
                         scarto=f'{scostamento:.1f}')

    _pannello_esito(dst, info, nota)
    return True

def _omogenei(infos: list[dict]) -> bool:
    """True se i file si possono incollare senza ricodificare.

    Il concat demuxer accosta i pacchetti cosi' come sono: pretende quindi
    che codec, risoluzione, formato dei pixel e frequenza coincidano. Basta
    che un file sia stato scaricato in un'altra qualita' perche' il risultato
    sia un video che si blocca a meta'. Meglio accorgersene prima.
    """
    if len(infos) < 2:
        return True
    primo = infos[0]
    chiavi = ('codec', 'width', 'height', 'pix_fmt', 'audio_codec',
              'audio_rate', 'audio_ch')
    return all(
        all(i[k] == primo[k] for k in chiavi)
        and abs(i['fps'] - primo['fps']) < 0.01
        for i in infos[1:]
    )


# Cosa sa ospitare il contenitore MP4. Gli elenchi sono volutamente corti e
# conservativi: ci stanno i codec che arrivano davvero dai file che si
# montano, e per tutto il resto si ricodifica. Sbagliare per eccesso di
# prudenza costa una ricodifica; sbagliare nell'altro verso non produce nulla.
_VIDEO_DA_MP4 = frozenset({'h264', 'hevc', 'mpeg4', 'av1', 'vp9', 'mpeg2video'})


_AUDIO_DA_MP4 = frozenset({'aac', 'mp3', 'ac3', 'eac3', 'alac', 'opus', 'mp2'})


def _copiabile(infos: list[dict], dst: str) -> bool:
    """True se i flussi si possono travasare cosi' come sono nel file d'arrivo.

    Essere omogenei fra loro non basta: bisogna anche starci dentro. La
    destinazione qui e' sempre un .mp4, mentre i sorgenti possono essere .wmv
    o .avi, che ospitano codec che l'MP4 non sa scrivere — msmpeg4v2 per il
    video, wmav2 per l'audio. Copiandoli comunque, FFmpeg si fermava su
    "Could not write header" e sul disco restava un file da zero byte: unire
    due .wmv non riusciva mai, e il messaggio non diceva perche'.

    Quando la risposta e' no non si perde niente: si prende la strada che
    ricodifica, che esiste gia' ed e' quella che il programma usa per i file
    disomogenei. Piu' lenta, ma un file lo produce.
    """
    if os.path.splitext(dst)[1].lower() not in ('.mp4', '.m4v', '.mov'):
        return True         # altri contenitori sono molto piu' permissivi
    if any((i['codec'] or '').lower() not in _VIDEO_DA_MP4 for i in infos):
        return False
    return all((i['audio_codec'] or '').lower() in _AUDIO_DA_MP4
               for i in infos if i['has_audio'])


def _scrivi_capitoli(infos: list[dict], percorso: str) -> None:
    """Scrive un file ffmetadata con un capitolo per ogni file di partenza.

    Cosi' il video unito resta navigabile: si salta da un pezzo all'altro
    come in un DVD, invece di andare a cercare il minuto a mano.
    """
    righe = [';FFMETADATA1']
    inizio_ms = 0
    for info in infos:
        fine_ms = inizio_ms + int(info['duration'] * 1000)
        titolo = os.path.splitext(os.path.basename(info['path']))[0]
        righe += ['[CHAPTER]', 'TIMEBASE=1/1000',
                  f'START={inizio_ms}', f'END={fine_ms}',
                  f'title={titolo}']
        inizio_ms = fine_ms
    with open(percorso, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(righe) + '\n')


def unisci(sorgenti: list[str], dst: str, *, capitoli: bool = True,
           crf: int = CRF_DEFAULT) -> bool:
    """Mette in fila i file in un unico video.

    Se sono omogenei li incolla in copia — secondi, nessuna perdita. Se non lo
    sono li porta tutti alla risoluzione del primo e ricodifica, perche' non
    c'e' altro modo: i pacchetti di due codifiche diverse non si possono
    accostare.
    """
    infos = []
    for s in sorgenti:
        info = probe(s)
        if not info:
            console.print(t('error.unreadable', path=escape(os.path.basename(s))))
            return False
        infos.append(info)

    # Due condizioni, e servono tutt'e due: che i file siano compatibili fra
    # loro, e che i loro flussi ci stiano nel contenitore d'arrivo.
    copia = _omogenei(infos) and _copiabile(infos, dst)
    console.print(t('merge.mode_copy') if copia else t('merge.mode_encode'))

    with tempfile.TemporaryDirectory(prefix='clipdex_') as tmp:
        meta = os.path.join(tmp, 'capitoli.txt')
        if capitoli:
            _scrivi_capitoli(infos, meta)

        if copia:
            lista = os.path.join(tmp, 'lista.txt')
            with open(lista, 'w', encoding='utf-8', newline='\n') as fh:
                for s in sorgenti:
                    # L'apice singolo nel nome va raddoppiato con la sequenza
                    # di uscita del formato concat, altrimenti chiude la
                    # stringa e il file successivo diventa illeggibile.
                    fh.write("file '%s'\n" % os.path.abspath(s).replace("'", r"'\''"))
            cmd = ['ffmpeg', '-hide_banner', '-v', 'error', '-y',
                   '-f', 'concat', '-safe', '0', '-i', lista]
            if capitoli:
                cmd += ['-i', meta, '-map_metadata', '1', '-map_chapters', '1']
            cmd += ['-c', 'copy', '-movflags', '+faststart', dst]
        else:
            larghezza, altezza = infos[0]['width'], infos[0]['height']
            fps = infos[0]['fps'] or 25
            cmd = ['ffmpeg', '-hide_banner', '-v', 'error', '-y']
            for s in sorgenti:
                cmd += ['-i', s]
            if capitoli:
                cmd += ['-i', meta]

            catena, etichette = [], []
            for i, info in enumerate(infos):
                # force_original_aspect_ratio + pad: un file di proporzioni
                # diverse viene incorniciato invece che stirato.
                catena.append(
                    f'[{i}:v]scale={larghezza}:{altezza}:'
                    'force_original_aspect_ratio=decrease,'
                    f'pad={larghezza}:{altezza}:-1:-1,setsar=1,fps={fps:.4f}[v{i}]')
                if info['has_audio']:
                    catena.append(f'[{i}:a]aresample=48000,aformat=channel_layouts=stereo[a{i}]')
                else:
                    # Un file muto in mezzo sfaserebbe il montaggio audio:
                    # gli si mette sotto il silenzio della stessa durata.
                    catena.append(
                        f"anullsrc=r=48000:cl=stereo,atrim=0:{info['duration']:.3f},"
                        f'asetpts=PTS-STARTPTS[a{i}]')
                etichette.append(f'[v{i}][a{i}]')
            catena.append(''.join(etichette) + f'concat=n={len(infos)}:v=1:a=1[v][a]')

            cmd += ['-filter_complex', ';'.join(catena), '-map', '[v]', '-map', '[a]']
            if capitoli:
                cmd += ['-map_metadata', str(len(sorgenti)),
                        '-map_chapters', str(len(sorgenti))]
            cmd += ['-c:v', 'libx264', '-crf', str(crf), '-preset', 'medium',
                    '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', dst]

        totale = int(sum(i['duration'] * (i['fps'] or 25) for i in infos))
        if not _esegui(cmd, t('run.merging'), totale):
            return False

    _pannello_esito(dst, None,
                    t('merge.note_chapters', n=len(sorgenti)) if capitoli else None)
    return True

def _finestra(info: dict, inizio: float | None, durata: float | None,
              durata_default: float) -> tuple[float, float]:
    """Sceglie da dove e per quanto prendere lo spezzone.

    Senza indicazioni parte da un terzo del video: l'inizio e' quasi sempre
    una sigla o una schermata nera, e una GIF di nulla non serve a niente.
    """
    if inizio is None:
        inizio = info['duration'] / 3 if info['duration'] else 0.0
    if durata is None:
        durata = min(durata_default, max(info['duration'] - inizio, 1.0))
    return max(inizio, 0.0), max(durata, 0.1)


def gif(src: str, dst: str, inizio: float | None = None,
        durata: float | None = None, fps: int = GIF_FPS,
        larghezza: int = GIF_LARGHEZZA) -> bool:
    """Ricava una GIF calcolando la palette sul filmato stesso.

    La GIF ha 256 colori e basta. La palette generica di FFmpeg su un video
    con sfumature produce una poltiglia di puntini; calcolarla sui fotogrammi
    veri costa un passaggio in piu' e su contenuto reale vale 1.7 dB di
    fedelta' in piu'. ``split`` serve proprio a questo: manda lo stesso flusso
    sia al generatore di palette sia all'applicatore, senza file temporanei.
    """
    info = probe(src)
    if not info:
        console.print(t('error.unreadable', path=escape(os.path.basename(src))))
        return False
    inizio, durata = _finestra(info, inizio, durata, 5.0)

    catena = (f'fps={fps},scale={larghezza}:-1:flags=lanczos,split[a][b];'
              '[a]palettegen=stats_mode=diff[p];'
              f'[b][p]paletteuse=dither={GIF_DITHER}:diff_mode=rectangle')
    cmd = ['ffmpeg', '-hide_banner', '-v', 'error', '-y',
           '-ss', f'{inizio:.3f}', '-t', f'{durata:.3f}', '-i', src,
           '-lavfi', catena, '-loop', '0', dst]

    if not _esegui(cmd, t('run.gif'), int(durata * fps)):
        return False
    _pannello_esito(dst, None, t('gif.note', inizio=fmt_durata(inizio),
                                 durata=f'{durata:.1f}', fps=fps, w=larghezza))
    return True


def webp(src: str, dst: str, inizio: float | None = None,
         durata: float | None = None, fps: int = GIF_FPS,
         larghezza: int = GIF_LARGHEZZA) -> bool:
    """Come la GIF, ma in WebP animato.

    Non essendo vincolato a 256 colori non ha bisogno di palette, e sullo
    stesso spezzone pesa quasi nove volte meno di una GIF fatta bene. Lo
    leggono tutti i browser dell'ultimo decennio; se la destinazione e' un
    forum di vent'anni fa, allora serve la GIF.
    """
    info = probe(src)
    if not info:
        console.print(t('error.unreadable', path=escape(os.path.basename(src))))
        return False
    inizio, durata = _finestra(info, inizio, durata, 5.0)

    cmd = ['ffmpeg', '-hide_banner', '-v', 'error', '-y',
           '-ss', f'{inizio:.3f}', '-t', f'{durata:.3f}', '-i', src,
           '-vf', f'fps={fps},scale={larghezza}:-1:flags=lanczos',
           '-c:v', 'libwebp', '-lossless', '0', '-q:v', str(WEBP_QUALITA),
           '-loop', '0', '-an', dst]

    if not _esegui(cmd, t('run.webp'), int(durata * fps)):
        return False
    _pannello_esito(dst, None, t('gif.note', inizio=fmt_durata(inizio),
                                 durata=f'{durata:.1f}', fps=fps, w=larghezza))
    return True

def provino(src: str, dst: str, righe: int = PROVINO_RIGHE,
            colonne: int = PROVINO_COLONNE,
            larghezza: int = PROVINO_LARGHEZZA) -> bool:
    """Compone una griglia di fotogrammi presi a intervalli regolari.

    Per capire cosa contiene un file e' piu' utile di un'anteprima animata:
    sedici istanti sparsi su tutta la durata dicono in un colpo d'occhio se
    e' il video giusto, dove cambiano le scene e se ci sono parti nere.
    """
    info = probe(src)
    if not info or not info['duration']:
        console.print(t('error.unreadable', path=escape(os.path.basename(src))))
        return False

    caselle = righe * colonne
    # Un fotogramma ogni N secondi, con N scelto perche' la griglia copra
    # esattamente tutta la durata: campionare a intervallo fisso lascerebbe
    # fuori la seconda meta' dei video lunghi.
    intervallo = max(info['duration'] / (caselle + 1), 0.1)

    # La casella ha misura fissa, ricavata dalle proporzioni del video. Senza,
    # basta che il filmato cambi formato a meta' — succede spesso nei montaggi
    # con spezzoni d'archivio — perche' la griglia esca a scalini. Le
    # proporzioni originali si conservano comunque: cio' che avanza viene
    # riempito di nero invece che stirato.
    altezza = max(2, round(larghezza * (info['height'] or 9)
                           / (info['width'] or 16) / 2) * 2)

    cmd = ['ffmpeg', '-hide_banner', '-v', 'error', '-y', '-i', src,
           '-vf', (f'fps=1/{intervallo:.4f},'
                   f'scale={larghezza}:{altezza}:force_original_aspect_ratio=decrease'
                   ':flags=lanczos,'
                   f'pad={larghezza}:{altezza}:-1:-1:color=black,setsar=1,'
                   f'tile={colonne}x{righe}:padding=4:margin=4'),
           '-frames:v', '1', dst]

    if not _esegui(cmd, t('run.sheet'), 0):
        return False
    _pannello_esito(dst, None, t('sheet.note', n=caselle,
                                 ogni=fmt_durata(intervallo)))
    return True

def compat(src: str, dst: str, crf: int = CRF_DEFAULT) -> bool:
    """Riporta il video a un H.264 che leggono anche gli apparecchi datati.

    Tre vincoli, tutti necessari e tutti spesso violati dai file scaricati:
    il profilo *baseline* (niente fotogrammi B, che i decodificatori piu'
    semplici non sanno gestire), il formato pixel ``yuv420p`` (molti file
    YouTube sono yuv444 o a 10 bit, che una TV del 2012 non decodifica) e le
    dimensioni pari, richieste dalla codifica stessa.

    ``+faststart`` sposta l'indice all'inizio del file: senza, un lettore da
    chiavetta USB deve leggere fino in fondo prima di poter partire.
    """
    info = probe(src)
    if not info:
        console.print(t('error.unreadable', path=escape(os.path.basename(src))))
        return False

    cmd = ['ffmpeg', '-hide_banner', '-v', 'error', '-y', '-i', src,
           '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2',
           '-c:v', 'libx264', '-profile:v', 'baseline', '-level', '3.0',
           '-pix_fmt', 'yuv420p', '-crf', str(crf), '-preset', 'medium',
           '-c:a', 'aac', '-b:a', '192k', '-ac', '2', '-ar', '44100',
           '-movflags', '+faststart', dst]

    if not _esegui(cmd, t('run.compat'), int(info['duration'] * (info['fps'] or 25))):
        return False
    _pannello_esito(dst, info, t('compat.note'))
    return True


def nome_uscita(src: str, suffisso: str, estensione: str | None = None,
                cartella: str | None = None) -> str:
    """Nome del file prodotto: nella cartella indicata, o accanto all'originale.

    L'originale non viene mai sovrascritto: un montaggio e' una scelta, e la
    si rifa' volentieri con parametri diversi. Il suffisso fra parentesi quadre
    dice quale delle sei operazioni l'ha prodotto, che e' l'unica cosa che si
    vuole sapere guardando la cartella mesi dopo.

    Senza ``cartella`` il file resta accanto all'originale, ed e' il
    comportamento giusto da riga di comando: chi lancia ``clip taglia`` su un
    video in una cartella sua si aspetta lo spezzone li'. La finestra passa
    invece sempre la cartella dei montaggi, perche' li' non c'e' una \"cartella
    corrente\" che chi guarda abbia in mente.
    """
    radice, ext = os.path.splitext(src)
    if cartella:
        radice = os.path.join(cartella, os.path.basename(radice))
    return f'{radice} [{suffisso}]{estensione or ext}'
