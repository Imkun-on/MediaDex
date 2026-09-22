"""Cosa c'e' dentro un file video, chiesto a ffprobe.

Una lettura sola per due mestieri
    PixDex e ClipDex avevano ognuno la propria ``probe()``. Facevano la stessa
    chiamata a ffprobe, con le stesse opzioni, e differivano solo in cosa si
    portavano via dalla risposta: ClipDex voleva sapere del flusso audio -
    frequenza, canali, se c'e' - perche' deve deciderne il destino quando
    unisce due file; PixDex voleva il bitrate, i semiquadri e i bit per pixel,
    perche' su quelli fonda la diagnosi.

    Qui la lettura e' una e il dizionario e' l'unione dei due. Nessuno dei due
    chiamanti perde un campo, e chi aggiunge un campo domani lo aggiunge per
    entrambi invece che per uno solo, come era successo al ``timeout``: ce
    l'aveva ClipDex e non PixDex, quindi un file di rete irraggiungibile
    bloccava a tempo indefinito la rimasterizzazione e non il montaggio.

Cosa fa quando non capisce
    Restituisce None, sempre, e scrive la ragione nel log. Non solleva: un file
    illeggibile in mezzo a una cartella di venti non deve fermare gli altri
    diciannove, e a monte c'e' sempre qualcuno - la finestra o il terminale -
    che sa cosa dire a chi guarda.
"""
from __future__ import annotations

import json
import subprocess

from server.config import i18n
from server.utils.console import setup_logger

t = i18n.t

log = setup_logger('pixdex', 'pixdex.log')


def _fps(valore: str | None) -> float:
    """Converte una frequenza fotogrammi 'num/den' in un numero.

    ffprobe la scrive come frazione - ``30000/1001`` per i 29.97 del NTSC -
    perche' e' l'unica forma esatta. Qui serve un numero, e uno zero vale come
    «non lo so»: tutti i conti a valle sono gia' protetti contro lo zero,
    mentre un'eccezione qui fermerebbe la lettura di un file che per il resto
    si capisce benissimo.
    """
    if not valore:
        return 0.0
    try:
        if '/' in valore:
            num, den = valore.split('/', 1)
            return float(num) / float(den) if float(den) else 0.0
        return float(valore)
    except (ValueError, ZeroDivisionError):
        return 0.0


def probe(path: str) -> dict | None:
    """Le caratteristiche di un file video, o None se non ne contiene uno.

    Il ``timeout`` non e' prudenza astratta: ffprobe su un percorso di rete
    caduto non torna mai, e senza limite si porterebbe dietro l'interfaccia
    grafica, che aspetta la risposta per mostrare la diagnosi.
    """
    try:
        dati = json.loads(subprocess.run(
            ['ffprobe', '-v', 'error', '-print_format', 'json',
             '-show_format', '-show_streams', path],
            capture_output=True, text=True, encoding='utf-8',
            errors='replace', check=True, timeout=60).stdout)
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError) as exc:
        log.warning('ffprobe fallito su %s: %s', path, exc)
        return None

    video = next((s for s in dati.get('streams', [])
                  if s.get('codec_type') == 'video'), None)
    audio = next((s for s in dati.get('streams', [])
                  if s.get('codec_type') == 'audio'), None)
    if not video:
        return None

    formato = dati.get('format', {})
    durata = float(formato.get('duration') or video.get('duration') or 0.0)
    fps = _fps(video.get('avg_frame_rate')) or _fps(video.get('r_frame_rate'))
    larghezza = int(video.get('width') or 0)
    altezza = int(video.get('height') or 0)
    dimensione = int(formato.get('size') or 0)

    # Il bitrate del solo flusso video spesso manca nei file WebM: in quel
    # caso si ricava dalla dimensione totale, che lo sovrastima di quanto pesa
    # l'audio. E' un'approssimazione accettabile perche' serve solo a decidere
    # quanto e' compresso il video, non a rifare i conti dell'encoder.
    bitrate = int(video.get('bit_rate') or 0)
    if not bitrate and durata > 0 and dimensione:
        bitrate = int(dimensione * 8 / durata)

    # Fotogrammi totali: il campo dichiarato non c'e' quasi mai nei file
    # scaricati, quindi si stima da durata e frequenza. Serve solo alla barra
    # di avanzamento, dove un errore dell'uno per cento non si nota.
    frames = int(video.get('nb_frames') or 0)
    if not frames and durata and fps:
        frames = int(durata * fps)

    return {
        'path': path,
        'width': larghezza,
        'height': altezza,
        'fps': fps,
        'codec': video.get('codec_name') or '?',
        'pix_fmt': video.get('pix_fmt') or '?',
        'bitrate': bitrate,
        'duration': durata,
        'size': dimensione,
        'frames': frames,

        # Il flusso audio non serve alla diagnosi ma al contenitore d'arrivo:
        # si scrive sempre un .mp4, e non tutto cio' che entra in un .wmv o in
        # un .avi ci puo' stare. Vedi _comando_audio in remaster.py e
        # _copiabile in edit.py.
        'audio_codec': (audio or {}).get('codec_name') or '',
        'audio_rate': int((audio or {}).get('sample_rate') or 0),
        'audio_ch': int((audio or {}).get('channels') or 0),
        'has_audio': audio is not None,

        # field_order diverso da 'progressive' significa semiquadri: materiale
        # televisivo o riversato da nastro, che va deinterlacciato prima di
        # qualunque altra cosa.
        'interlaced': (video.get('field_order') or 'progressive') not in
                      ('progressive', 'unknown'),
        'bpp': (bitrate / (larghezza * altezza * fps)
                if larghezza and altezza and fps and bitrate else 0.0),
    }


# ── Cosa e' davvero un filmato ───────────────────────────────────────────────
#
# FFmpeg e' molto piu' accomodante di quanto ci si aspetti: ha un demuxer che
# legge un file di testo come un'animazione ANSI da terminale e lo dichiara un
# video 640x400 a 25 fps. Un requirements.txt passa quindi ogni controllo
# basato sul solo "ffprobe ha trovato un flusso video", e senza questo filtro
# ci si ritroverebbe a rimasterizzare per mezz'ora un elenco di dipendenze.
#
# Anche un'immagine singola e' formalmente un video: un fotogramma, durata
# zero. Non c'e' niente da rimasterizzare li' dentro.
CODEC_FINTI = frozenset({'ansi', 'png', 'bmp', 'tiff', 'ppm', 'pgm', 'targa'})


DURATA_MINIMA = 1.0


def e_un_filmato(info: dict) -> bool:
    """True se cio' che ffprobe ha letto e' davvero un filmato.

    Due criteri, e bastano entrambi presi insieme: il codec non e' fra quelli
    che descrivono immagini ferme o testo, e dura almeno un secondo. Nessun
    video vero dura meno, e nessun file di testo dura di piu'.
    """
    if info.get('codec') in CODEC_FINTI:
        return False
    return float(info.get('duration') or 0) >= DURATA_MINIMA


# Sotto questa densita' di bit per pixel il file e' compresso al punto che i
# quadretti si vedono: 0.05 bpp e' la soglia empirica sotto cui YouTube inizia
# a lasciare artefatti visibili anche a un occhio non allenato.
BPP_COMPRESSO = 0.05


BPP_MOLTO_COMPRESSO = 0.025


def diagnosi(info: dict) -> tuple[list[str], str]:
    """Elenca i difetti rilevati e restituisce il preset consigliato.

    La diagnosi guarda tre grandezze: la risoluzione (dice se ha senso
    ingrandire), i bit per pixel (dicono quanto la compressione ha
    infierito) e l'ordine dei campi (dice se il materiale e' televisivo).
    Nessuna di queste richiede di decodificare il video, quindi il consiglio
    e' istantaneo anche su file da un'ora.
    """
    problemi: list[str] = []
    preset = 'standard'

    if info['interlaced']:
        problemi.append(t('diag.interlaced'))
        preset = 'vecchio'

    if info['height'] and info['height'] <= 480:
        problemi.append(t('diag.lowres', h=info['height']))

    bpp = info['bpp']
    if bpp and bpp < BPP_MOLTO_COMPRESSO:
        problemi.append(t('diag.very_compressed', bpp=f'{bpp:.3f}'))
        if preset != 'vecchio':
            preset = 'forte'
    elif bpp and bpp < BPP_COMPRESSO:
        problemi.append(t('diag.compressed', bpp=f'{bpp:.3f}'))

    # Un formato pixel a 8 bit e' la norma, ma e' anche la causa delle bande
    # nelle sfumature: vale la pena dirlo perche' e' esattamente il difetto
    # che la lavorazione a 10 bit va a sanare.
    if info['pix_fmt'].startswith('yuv420p') and '10' not in info['pix_fmt']:
        problemi.append(t('diag.banding_risk'))

    if not problemi:
        problemi.append(t('diag.clean'))
        preset = 'pulito'

    return problemi, preset
