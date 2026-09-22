"""Scaricare UN brano, dall'inizio alla fine.

Tutto quello che succede fra «questo video» e «questo file, taggato, col
testo dentro, controllato». Le fasi sono cinque e si susseguono sempre nello
stesso ordine - scarico, converto, cerco il testo, scrivo i tag, verifico - e
chi guarda le vede passare una per una, perche' un download di quattro minuti
che non dice a che punto e' sembra bloccato.

Le due funzioni che raccontano
    ``_YtDlpProgressHook`` traduce i byte che yt-dlp riferisce in una
    frazione, ed e' l'unica cosa che fa muovere la barra durante la parte
    lunga. Il resto delle fasi non ha un avanzamento misurabile: si limitano
    ad annunciarsi.

Scaricare PIU' brani non e' affare di questo modulo: quello e' un'orchestra,
e sta in ``server/services/audio.py``.
"""
from __future__ import annotations

import os
import time

import yt_dlp
from rich.markup import escape
from rich.progress import Progress

from server.config import i18n
from server.config.settings import (
    AUDIO_SOURCE_FORMATS, FORMATI_AUDIO, FORMATI_VIDEO, MAX_RETRIES,
    RETRY_BASE_DELAY)
from server.audio.chapters import capitoli_album, dividi_per_capitoli
from server.audio.tagging import tag_m4a
from server.audio.verify import verifica_file
from server.sources.lyrics import cerca_testo
from server.sources.youtube import _apply_cookies
from server.state import db as scraper_db
from server.state.jobs import INTERROTTO
from server.utils.console import SYM_FAIL, SYM_OK, console, setup_logger
from server.utils.http import retry_delay
from server.utils.text import nome_file_pulito, prefisso_traccia

t = i18n.t

log = setup_logger('audiodex', 'audiodex.log', ytdlp=True)


def _retry_delay(attempt: int) -> float:
    """Calcola l'attesa tra un tentativo fallito e il successivo.

    Backoff esponenziale (cresce a ogni tentativo) con jitter casuale, per
    non riprovare a raffica e non sincronizzare i retry dei vari thread.
    """
    return retry_delay(attempt, base=RETRY_BASE_DELAY, jitter=(1.0, 3.0))

def _wanted_name(prefix: str, title: str, existing_path: str) -> str:
    """Nome file atteso per una traccia: prefisso + titolo + estensione attuale.

    Serve alla rinumerazione dei file scaricati con una versione precedente,
    quando ancora non esisteva il numero di traccia nel nome: calcola come
    *dovrebbe* chiamarsi oggi quel file, per poterlo rinominare invece di
    riscaricarlo.

    L'estensione viene presa dal file esistente e non dal formato richiesto:
    un `.mp3` già in cartella va rinominato restando `.mp3`, altrimenti si
    otterrebbe un nome che promette un contenuto diverso da quello reale.

    La sanificazione è applicata due volte di proposito — prima al titolo, poi
    all'intero nome — perché il prefisso numerico è generato dal programma ed
    è già sicuro, mentre il secondo passaggio normalizza la stringa completa.
    """
    ext = os.path.splitext(existing_path)[1]
    return nome_file_pulito(prefix + nome_file_pulito(title)) + ext


def _is_already_downloaded(title: str, output_dir: str, prefix: str = '',
                           exts: frozenset[str] = FORMATI_AUDIO) -> str | None:
    """Controlla se la traccia è già stata scaricata nella cartella di destinazione.

    Confronta il titolo sanificato con i nomi dei file esistenti, tra quelli
    con un'estensione in `exts` (i formati equivalenti: audio con audio,
    video con video — così un brano gia' scaricato in .m4a non fa saltare
    lo stesso titolo richiesto in video). I file sotto i 10 KB vengono
    considerati download incompleti e quindi da rifare. Restituisce il
    percorso del file trovato oppure None: evita di riscaricare le stesse
    tracce nei run successivi.

    Con un prefisso di traccia riconosce anche i file scaricati da versioni
    precedenti — cioè *senza* numero — e li rinomina invece di riscaricarli.
    I file che hanno già un numero diverso NON vengono toccati: in una
    playlist con due tracce omonime (succede: stesso brano in versione
    singolo e in versione album) si contenderebbero lo stesso file,
    rinominandolo a vicenda e lasciandone scaricare una sola.
    """
    if not os.path.isdir(output_dir):
        return None

    safe_title = nome_file_pulito(title)
    wanted = (prefix + safe_title).lower()

    fallback = None
    for f in os.listdir(output_dir):
        name_no_ext, ext = os.path.splitext(f)
        if ext.lstrip('.').lower() not in exts:
            continue
        name_no_ext = name_no_ext.lower()
        full = os.path.join(output_dir, f)
        if name_no_ext == wanted:
            if os.path.getsize(full) > 10240:
                return full
            continue
        if prefix and name_no_ext == safe_title.lower():
            if os.path.getsize(full) > 10240:
                fallback = full

    if fallback:
        # Stesso brano senza numerazione: basta rinominarlo.
        target = os.path.join(output_dir, _wanted_name(prefix, title, fallback))
        if not os.path.exists(target):
            try:
                os.replace(fallback, target)
                log.info('Rinumerato: %s', os.path.basename(target))
                return target
            except OSError as exc:
                log.warning('Rinumerazione non riuscita: %s', exc)
        return fallback
    return None


class _YtDlpProgressHook:
    """Ponte tra yt-dlp e la barra di avanzamento Rich del singolo file.

    yt-dlp invoca quest'oggetto a ogni blocco scaricato; noi aggiorniamo la
    barra con i byte ricevuti. La dimensione totale non è nota subito (a
    volte è solo una stima che arriva dopo le prime chiamate), perciò viene
    impostata al primo valore disponibile.
    """

    def __init__(self, progress: Progress | None, task_id, title: str,
                 on_downloaded=None, on_progress=None):
        """Lega questo hook alla barra di una singola traccia.

        Parametri
        ---------
        progress, task_id
            La barra Rich e l'identificativo dell'attività da aggiornare.
            Possono essere None: chi non disegna a terminale — l'interfaccia
            grafica — passa solo ``on_progress``.
        title : str
            Titolo della traccia, tenuto per i messaggi diagnostici.
        on_downloaded : callable | None
            Richiamata quando l'ultimo byte è arrivato. Serve a segnalare al
            tracker delle fasi che il download è finito e che da lì in poi
            sta lavorando FFmpeg: senza, la barra "Download" resterebbe
            indietro per tutta la conversione.
        on_progress : callable | None
            Richiamata con ``(scaricati, totale)`` in byte a ogni blocco.
            E' l'unico modo che ha un chiamante senza terminale di sapere a
            che punto è un download: il numero c'è già, e prima non usciva
            di qui.

        ``_started`` e ``_total`` esistono perché la dimensione del file non
        è nota alla prima chiamata: si registra il primo totale utile e lo si
        riusa alla fine per portare la barra esattamente al fondo scala.
        """
        self.progress = progress
        self.task_id = task_id
        self.title = title
        self.on_downloaded = on_downloaded
        self.on_progress = on_progress
        self._started = False
        self._total = 0

    def __call__(self, d: dict) -> None:
        """Callback invocata da yt-dlp a ogni blocco scaricato.

        Traduce il dizionario di stato di yt-dlp in aggiornamenti della barra
        Rich. Gestisce due soli stati: ``downloading``, che porta avanti i
        byte, e ``finished``, che chiude la barra al 100% e avvisa il
        chiamante.

        La chiusura esplicita al totale serve perché l'ultimo evento
        ``downloading`` può arrivare qualche kilobyte prima della fine,
        lasciando la barra al 99% per sempre.

        L'intero corpo è avvolto in un ``except`` silenzioso di proposito:
        questa funzione gira dentro il ciclo di download di yt-dlp, e
        un'eccezione sollevata qui — anche solo per una chiave mancante in un
        formato di stato inatteso — abortirebbe un download altrimenti sano.
        Un difetto grafico è sempre preferibile a una traccia persa.
        """
        try:
            if d['status'] == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                downloaded = d.get('downloaded_bytes', 0)
                if total > 0:
                    self._total = total
                    if self.progress is not None:
                        if not self._started:
                            self.progress.update(self.task_id, total=total)
                            self._started = True
                        self.progress.update(self.task_id, completed=downloaded)
                    else:
                        self._started = True
                    if self.on_progress:
                        self.on_progress(downloaded, total)
            elif d['status'] == 'finished':
                if self._started and self._total > 0:
                    if self.progress is not None:
                        self.progress.update(self.task_id, completed=self._total)
                    if self.on_progress:
                        self.on_progress(self._total, self._total)
                # I byte sono arrivati: da qui in poi lavora FFmpeg.
                if self.on_downloaded:
                    self.on_downloaded()
        except Exception:
            pass


def download_single(entry: dict, output_dir: str, audio_format: str = 'm4a',
                    track_num: int | None = None, album: str | None = None,
                    progress: Progress | None = None, task_id=None,
                    fetch_lyrics: bool = True, total_tracks: int | None = None,
                    numbered: bool = False, on_phase=None, on_progress=None,
                    media: str = 'audio', dividi: bool = False) -> dict:
    """Scarica una singola traccia e ne registra i metadati.

    Con media='audio' (default) scarica il solo flusso audio; con
    media='video' scarica anche la traccia video e unisce i due flussi.

    Flusso completo:
      1. salta subito se il file esiste già su disco (status 'skip');
      2. scarica il flusso richiesto e lo converte/unisce nel formato
         scelto tramite ffmpeg;
      3. *(solo audio)* cerca il testo sincronizzato su LRCLIB e, se
         trovato, lo incorpora nei tag (un file unico, nessun .lrc);
      4. scrive titolo, artista, album e copertina nei tag — nei video
         solo per l'mp4, che condivide il container MP4 con l'm4a;
      5. registra il download nel database globale.
    In caso di errore riprova fino a MAX_RETRIES volte con attesa crescente.

    Restituisce {'title', 'status' ('ok'/'skip'/'fail'), 'file', 'error',
    'lyrics' (True se è stato trovato e incorporato il testo)}.
    """
    title = entry.get('title', t('common.unknown'))
    url = entry.get('url', '')
    uploader = entry.get('uploader', '')

    result = {'title': title, 'status': 'fail', 'file': '', 'error': '',
              'lyrics': False, 'tracce': 0}

    if INTERROTTO.is_set():
        result['error'] = 'shutdown'
        return result

    prefix = prefisso_traccia(track_num, total_tracks) if numbered else ''
    is_video = media == 'video'

    existing = _is_already_downloaded(
        title, output_dir, prefix,
        exts=FORMATI_VIDEO if is_video else FORMATI_AUDIO,
    )
    if existing:
        log.info("Gia' scaricato: %s", title)
        result['status'] = 'skip'
        result['file'] = os.path.basename(existing)
        if progress and task_id is not None:
            # Barra piena: la traccia c'è già, non serve leggere il totale
            # precedente (Progress.tasks è una lista posizionale, e con i
            # task rimossi a mano a mano l'indice non è più il TaskID).
            progress.update(task_id, total=1, completed=1)
        return result

    os.makedirs(output_dir, exist_ok=True)

    # Il prefisso numerico entra nel nome del file: sul disco (e sul telefono,
    # che ordina per nome) le tracce restano nell'ordine della playlist.
    outtmpl = os.path.join(output_dir, f'{prefix}%(title)s.%(ext)s')

    ydl_opts = _apply_cookies({
        'outtmpl': outtmpl,
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': False,
        'retries': MAX_RETRIES,
        'fragment_retries': MAX_RETRIES,
        'writethumbnail': False,
        'noplaylist': True,
    })

    if is_video:
        # Video completo: YouTube serve video e audio come flussi separati
        # (le risoluzioni alte non hanno audio incorporato), quindi si
        # scarica il meglio di entrambi e ffmpeg li unisce nel container
        # scelto. Il fallback 'best' copre i video a flusso unico.
        ydl_opts['format'] = (
            f'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best'
            if audio_format == 'mp4' else 'bestvideo+bestaudio/best'
        )
        ydl_opts['merge_output_format'] = audio_format

        # Metadati scritti da ffmpeg durante il merge: titolo, autore, data
        # e i capitoli del video. Funziona su qualsiasi container, ed è
        # l'unica via per il Matroska, che mutagen non sa taggare.
        ydl_opts['postprocessors'] = [
            {'key': 'FFmpegMetadata', 'add_metadata': True, 'add_chapters': True},
        ]

        # Album e numero di traccia non stanno nell'info di yt-dlp: li
        # ricaviamo noi dalla playlist, quindi vanno passati a mano come
        # argomenti extra di ffmpeg. Senza, un video di playlist perderebbe
        # proprio i due campi che tengono insieme una raccolta.
        extra_meta = []
        if album:
            extra_meta += ['-metadata', f'album={album}']
        if track_num:
            extra_meta += ['-metadata', f'track={track_num}']
        if extra_meta:
            ydl_opts['postprocessor_args'] = {'metadata': extra_meta}
        if audio_format == 'mkv':
            # Nel Matroska la copertina è un allegato: la incorpora yt-dlp,
            # perché mutagen non scrive i metadati mkv. Nell'mp4 invece
            # ci pensa tag_m4a più sotto, insieme a tutto il resto.
            ydl_opts['writethumbnail'] = True
            ydl_opts['postprocessors'].append(
                {'key': 'EmbedThumbnail', 'already_have_thumbnail': False}
            )
    else:
        # Solo audio: niente traccia video, il file occupa una frazione
        # dello spazio. Il flusso richiesto dipende dal formato di uscita
        # (vedi AUDIO_SOURCE_FORMATS): così 'FFmpegExtractAudio' trova già
        # il codec giusto e rimuxa senza ricodificare, invece di scaricare
        # sempre l'AAC e ricomprimerlo una seconda volta.
        ydl_opts['format'] = AUDIO_SOURCE_FORMATS.get(audio_format, 'bestaudio/best')
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': audio_format,
            'preferredquality': '0',
        }]

    def phase(name: str) -> None:
        """Segnala il superamento di una fase, se c'è un tracker collegato."""
        if on_phase:
            on_phase(name)

    if (progress and task_id is not None) or on_progress:
        hook = _YtDlpProgressHook(
            progress if task_id is not None else None, task_id, title,
            on_downloaded=lambda: phase('download'),
            on_progress=on_progress,
        )
        ydl_opts['progress_hooks'] = [hook]

    for attempt in range(1, MAX_RETRIES + 1):
        if INTERROTTO.is_set():
            result['error'] = 'shutdown'
            return result
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if not info:
                    raise Exception('Nessuna info estratta')

                final_ext = audio_format
                expected_file = ydl.prepare_filename(info)
                base, _ = os.path.splitext(expected_file)
                final_file = f'{base}.{final_ext}'

                if not os.path.isfile(final_file):
                    # Fallback: cerca il file per nome ed estensione
                    safe = nome_file_pulito(prefix + nome_file_pulito(info.get('title', title))).lower()
                    for f in os.listdir(output_dir):
                        if not f.lower().endswith(f'.{final_ext}'):
                            continue
                        name_no_ext = os.path.splitext(f)[0].lower()
                        if name_no_ext != safe:
                            continue
                        final_file = os.path.join(output_dir, f)
                        break

                if os.path.isfile(final_file):
                    # Ripulisce il nome dai "sosia" Unicode e dalle emoji che
                    # yt-dlp lascia nel nome del file: così il brano si copia
                    # senza intoppi sul telefono via cavo USB.
                    folder, current = os.path.split(final_file)
                    stem, ext = os.path.splitext(current)
                    clean = nome_file_pulito(stem)
                    if clean and clean != stem:
                        target = os.path.join(folder, clean + ext)
                        if not os.path.exists(target):
                            try:
                                os.replace(final_file, target)
                                final_file = target
                            except OSError as exc:
                                log.warning('Rinomina del file non riuscita: %s', exc)

                    # FFmpeg ha finito: il file nel formato richiesto esiste.
                    phase('convert')

                    # Prima di taggarlo e di registrarlo, accertarsi che sia
                    # intero. Un file troncato che entra nel database e' peggio
                    # di un download fallito: al giro dopo viene riconosciuto
                    # come gia' scaricato e non lo si ripesca piu'.
                    guasto = verifica_file(
                        final_file,
                        info.get('duration') or entry.get('duration'),
                    )
                    if guasto:
                        log.error('%s File non integro: %s (%s)',
                                  SYM_FAIL, title, guasto)
                        result['error'] = guasto
                        try:
                            os.remove(final_file)
                        except OSError:
                            pass
                        return result

                    # Divisione in tracce, se richiesta e se i capitoli
                    # sembrano davvero quelli di un disco. Va fatta qui:
                    # dopo la verifica, perché tagliare un file troncato
                    # moltiplicherebbe il danno, e prima dei tag, perché è
                    # ogni singola traccia a doverli avere, non l'album.
                    if dividi:
                        capitoli = capitoli_album(info)
                        if capitoli:
                            cartella = os.path.join(
                                os.path.dirname(final_file),
                                nome_file_pulito(info.get('title', title)))
                            pezzi = dividi_per_capitoli(
                                final_file, capitoli, cartella,
                                artista=(info.get('artist')
                                         or info.get('uploader') or uploader),
                                album=info.get('title', title),
                                copertina=info.get('thumbnail'),
                            )
                            result['tracce'] = len(pezzi)
                            log.info('Diviso in %d tracce: %s',
                                     len(pezzi), cartella)
                            # Detto a schermo, non solo nel log: chi ha appena
                            # risposto "sì" vuole sapere dove sono finite.
                            console.print(t('split.done', sym=SYM_OK,
                                            n=len(pezzi),
                                            cartella=escape(cartella)))

                    # Testo: incorporato direttamente nei tag del file audio
                    # (formato LRC con i timestamp), così il brano resta un
                    # file unico che porta con sé anche il testo.
                    # Il testo si scrive nel tag ©lyr, che esiste solo nel
                    # container MP4: vale per m4a e mp4, non per il mkv.
                    synced, plain = (None, None)
                    if fetch_lyrics and final_ext != 'mkv':
                        synced, plain = cerca_testo(
                            info.get('title', title),
                            info.get('artist') or info.get('uploader') or uploader,
                            info.get('duration') or entry.get('duration'),
                        )
                        if synced or plain:
                            result['lyrics'] = True
                            log.info('Testo trovato: %s', title)
                    phase('lyrics')

                    # I tag iTunes vivono nel container MP4: valgono per
                    # .m4a e .mp4, non per il Matroska (.mkv).
                    if final_ext != 'mkv':
                        tag_m4a(
                            final_file,
                            title=info.get('title', title),
                            artist=info.get('artist') or info.get('uploader') or uploader,
                            album=album or info.get('album'),
                            track_num=track_num,
                            thumbnail_url=info.get('thumbnail'),
                            lyrics=synced or plain,
                        )
                    phase('tag')

                    result['status'] = 'ok'
                    result['file'] = os.path.basename(final_file)
                    log.info('%s Scaricato: %s', SYM_OK, title)

                    scraper_db.record_audio_download(
                        source_id=entry.get('id', ''),
                        title=info.get('title', title),
                        source_url=url,
                        file_path=final_file,
                        file_size_bytes=os.path.getsize(final_file),
                        collection_name=album or info.get('album', ''),
                        artist=info.get('artist') or info.get('uploader') or uploader,
                        duration_secs=info.get('duration') or entry.get('duration') or 0,
                        audio_format=audio_format,
                        track_number=track_num or 0,
                        media_kind=media,
                    )

                    return result

                raise FileNotFoundError(f'File non trovato dopo download: {final_file}')
        except Exception as e:
            log.warning("Tentativo %d/%d fallito per '%s': %s", attempt, MAX_RETRIES, title, e)
            result['error'] = str(e)[:100]
            if attempt < MAX_RETRIES:
                delay = _retry_delay(attempt)
                log.debug('Retry tra %.1fs...', delay)
                time.sleep(delay)

    log.error('%s Fallito: %s - %s', SYM_FAIL, title, result['error'])
    return result
