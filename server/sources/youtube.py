"""Chiedere a YouTube: cercare, leggere una playlist, guardare un video.

Qui si chiede e si riceve, e basta. Nessun file viene scritto, niente viene
convertito: questo strato produce i dizionari che descrivono cosa c'e'
dall'altra parte, e chi li usa decide cosa farne.

Tutto passa per yt-dlp, e tutto passa per ``_apply_cookies``: senza,
parecchie richieste tornano vuote o con un 403, perche' YouTube distingue
sempre piu' spesso fra un browser e tutto il resto.
"""
from __future__ import annotations

import re

import yt_dlp

from server.config import i18n
from server.config.settings import MAX_SEARCH_RESULTS
from server.utils.console import setup_logger

t = i18n.t

log = setup_logger('audiodex', 'audiodex.log', ytdlp=True)

# Impostato da --cookies-from-browser: yt-dlp legge i cookie del browser
# indicato e si presenta a YouTube autenticato. Serve per playlist e video
# privati, che altrimenti risultano "inesistenti".
_cookies_browser: str | None = None


def _apply_cookies(ydl_opts: dict) -> dict:
    """Aggiunge le opzioni cookie a un dict di opzioni yt-dlp, se richieste.

    Le opzioni yt-dlp vengono costruite in cinque punti diversi del file
    (ricerca, playlist, scheda video, download audio, download video) e tutti
    devono presentarsi a YouTube con la stessa identità. Centralizzare qui
    l'innesto dei cookie evita che aggiungendo una nuova chiamata ci si
    dimentichi di autenticarla, con l'effetto di vedere sparire proprio le
    playlist private per cui l'opzione era stata attivata.

    Modifica e restituisce lo stesso dict, per potersi incastrare
    direttamente nell'espressione che lo crea.
    """
    if _cookies_browser:
        ydl_opts['cookiesfrombrowser'] = (_cookies_browser,)
    return ydl_opts


def search_youtube(query: str, max_results: int = MAX_SEARCH_RESULTS) -> list[dict]:
    """Cerca brani su YouTube e restituisce i metadati dei risultati.

    Usa la ricerca interna di yt-dlp con 'extract_flat': ottiene solo i
    metadati (titolo, canale, durata, views, URL) senza scaricare nulla.
    La lista serve a mostrare i risultati all'utente e fargli scegliere
    cosa scaricare.
    """
    log.info("Ricerca YouTube: '%s'", query)
    results = []

    ydl_opts = _apply_cookies({
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
    })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 'default_search' restituisce 0 risultati con yt-dlp recenti:
            # serve il prefisso esplicito ytsearchN:
            info = ydl.extract_info(f'ytsearch{max_results}:{query}', download=False)
            if not info:
                return []
            entries = info.get('entries', [])
            if not entries:
                # Risultato singolo (URL diretto)
                if info.get('id'):
                    results.append({
                        'id': info['id'],
                        'title': info.get('title', t('common.unknown')),
                        'uploader': info.get('uploader') or info.get('channel') or '??',
                        'duration': info.get('duration'),
                        'views': info.get('view_count'),
                        'url': info.get('webpage_url', f"https://www.youtube.com/watch?v={info['id']}"),
                    })
                return results
            for entry in entries:
                if not entry:
                    continue
                vid_id = entry.get('id', '')
                results.append({
                    'id': vid_id,
                    'title': entry.get('title', t('common.unknown')),
                    'uploader': entry.get('uploader') or entry.get('channel') or '??',
                    'duration': entry.get('duration'),
                    'views': entry.get('view_count'),
                    'url': entry.get('url', entry.get('webpage_url', f'https://www.youtube.com/watch?v={vid_id}')),
                })
    except Exception as e:
        log.error('Errore ricerca: %s', e)

    return results


def _normalize_playlist_url(url: str) -> str:
    """Converte un URL 'watch?v=...&list=...' nell'URL canonico della playlist.

    Se si passa a yt-dlp l'URL di un video appartenente a una playlist, viene
    estratto solo quel video: per avere l'elenco completo serve l'URL
    'playlist?list=<ID>'.
    """
    match = re.search(r'[?&]list=([\w-]+)', url)
    if match and 'playlist?list=' not in url:
        return f'https://www.youtube.com/playlist?list={match.group(1)}'
    return url


def get_playlist_entries(url: str) -> tuple[str, list[dict], dict]:
    """Recupera titolo, tracce e dati d'insieme di una playlist/album.

    Come per la ricerca, 'extract_flat' scarica solo i metadati — ma per
    le voci di una playlist YouTube fornisce SOLO titolo e durata (niente
    canale né views): l'artista mostrato in tabella viene quindi ricavato
    dal titolo. A livello di **playlist**, invece, la stessa chiamata
    riporta canale, visualizzazioni complessive, data di modifica e
    visibilità: li restituiamo nel terzo valore, così il pannello di
    riepilogo non costa una richiesta in più.

    Con 'ignoreerrors' i video privati o rimossi vengono saltati invece
    di far fallire l'intera playlist; le playlist private richiedono
    --cookies-from-browser. Restituisce (titolo, tracce, dati playlist).
    """
    log.info('Recupero playlist: %s', url)
    entries = []
    playlist_title = 'Playlist'
    meta: dict = {}

    if e_playlist(url):
        url = _normalize_playlist_url(url)
        log.debug('URL normalizzato: %s', url)

    ydl_opts = _apply_cookies({
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'ignoreerrors': True,
        'noplaylist': False,
    })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return playlist_title, [], meta
            playlist_title = info.get('title', 'Playlist')
            meta = {
                'channel': info.get('channel') or info.get('uploader'),
                'views': info.get('view_count'),
                'modified': info.get('modified_date'),
                'availability': info.get('availability'),
                'count': info.get('playlist_count'),
            }
            raw_entries = info.get('entries', [])
            if not raw_entries:
                # Forse è un video singolo invece di una playlist
                if info.get('id'):
                    entries.append({
                        'id': info['id'],
                        'title': info.get('title', t('common.unknown')),
                        'uploader': info.get('uploader') or info.get('channel') or '??',
                        'duration': info.get('duration'),
                        'views': info.get('view_count'),
                        'url': info.get('webpage_url', url),
                        'index': 1,
                    })
                return playlist_title, entries, meta
            # 'index' è la posizione nella playlist di origine, non nella lista
            # che restituiamo: le voci saltate (video privati o rimossi) non
            # fanno scalare le successive, e una selezione parziale conserva
            # comunque la numerazione originale.
            for pos, entry in enumerate(raw_entries, 1):
                if not entry:
                    continue
                vid_id = entry.get('id', '')
                entries.append({
                    'id': vid_id,
                    'title': entry.get('title', t('common.unknown')),
                    'uploader': entry.get('uploader') or entry.get('channel') or '??',
                    'duration': entry.get('duration'),
                    'views': entry.get('view_count'),
                    'url': entry.get('url', entry.get('webpage_url', f'https://www.youtube.com/watch?v={vid_id}')),
                    'index': entry.get('playlist_index') or pos,
                })

            # Dimensione della playlist intera: fissa la larghezza dello
            # zero-padding anche quando se ne scarica solo un pezzo, così i
            # numeri restano allineati con quelli già presenti in cartella.
            playlist_size = max((e['index'] for e in entries), default=0)
            for e in entries:
                e['playlist_size'] = playlist_size
    except Exception as e:
        log.error('Errore recupero playlist: %s', e)

    return playlist_title, entries, meta


def get_video_details(url: str) -> dict | None:
    """Recupera i metadati completi di un singolo video, senza scaricarlo.

    A differenza di get_playlist_entries qui NON si usa 'extract_flat':
    serve l'estrazione piena, l'unica che riporta visualizzazioni, mi
    piace, iscritti al canale, categoria e lingua. Costa un paio di
    secondi, accettabili per un video solo (su una playlist intera
    sarebbero secondi per traccia, ed è il motivo per cui lì restiamo
    sull'estrazione veloce). Restituisce None se il video non esiste o
    non è accessibile.
    """
    ydl_opts = _apply_cookies({
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
    })
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info and info.get('entries'):
                # URL di playlist passato per errore: si prende il primo
                info = info['entries'][0]
            return info or None
    except Exception as e:
        log.error('Errore info video: %s', e)
        return None


def entry_da_info(info: dict, url: str) -> dict:
    """Costruisce la entry di download dai metadati completi di un video.

    Il resto del programma lavora su "entry", dizionari con sempre le stesse
    sei chiavi, prodotti dalla ricerca e dall'estrazione delle playlist.
    L'estrazione piena di un singolo video restituisce invece decine di campi
    con nomi diversi: questa funzione li riduce alla forma comune, così
    ``download_batch`` non deve sapere da dove arriva ciò che riceve.

    Ogni campo ha un ripiego, perché la scheda di un video può essere
    incompleta e un ``None`` che arrivasse fino alle tabelle vi comparirebbe
    stampato come testo. Per l'URL si preferisce ``webpage_url``, la forma
    canonica ripulita da YouTube, e si ricade su quello incollato dall'utente
    solo se manca: è ciò che elimina i parametri di Mix e tracciamento.
    """
    return {
        'id': info.get('id', ''),
        'title': info.get('title', t('common.unknown')),
        'uploader': info.get('uploader') or info.get('channel') or '??',
        'duration': info.get('duration'),
        'views': info.get('view_count'),
        'url': info.get('webpage_url', url),
    }


# Prefissi degli id di lista che YouTube assegna alle "Mix", cioè le radio
# generate al volo: My Mix, mix di un artista, mix di un video musicale.
_MIX_PREFISSI = ('RDMM', 'RDEM', 'RDAMVM', 'RDGMEM', 'RDAO')


def _is_mix_url(url: str) -> bool:
    """Riconosce le Mix di YouTube, che sembrano playlist ma non lo sono.

    Copiando il link dal player di un video, YouTube ci attacca spesso un
    '&list=RD<idVideo>&start_radio=1': è la radio automatica costruita a
    partire da quel brano. Non è una playlist apribile — l'URL canonico
    'playlist?list=RD…' fa rispondere a YouTube *"This playlist type is
    unviewable"* — quindi va ignorata e si scarica il solo video.

    Restano escluse le liste 'RDCLAK5uy_…', che YouTube Music genera per gli
    album e che invece sono normalmente consultabili.
    """
    if 'start_radio=1' in url:
        return True

    lista = re.search(r'[?&]list=([\w-]+)', url)
    if not lista:
        return False
    lista = lista.group(1)

    if lista.startswith(_MIX_PREFISSI):
        return True

    # 'RD' + id del video: la radio del brano che si sta guardando
    video = re.search(r'[?&]v=([\w-]+)', url)
    return bool(video and lista == f'RD{video.group(1)}')


def _url_ha_video(url: str) -> bool:
    """True se l'URL contiene comunque l'id di un video singolo.

    È la condizione del ripiego applicato quando l'estrazione di una playlist
    non produce nulla: se il link porta con sé un `v=`, quel video resta
    scaricabile anche se la raccolta a cui appartiene è privata, rimossa o di
    un tipo che YouTube non espone. Meglio consegnare il brano che l'utente
    stava guardando piuttosto che rifiutare l'intera operazione.
    """
    return bool(re.search(r'[?&]v=[\w-]+', url))


def e_playlist(url: str) -> bool:
    """Riconosce dall'URL se si tratta di una playlist o di un album.

    Copre i pattern di YouTube ('playlist?list=', '&list='), Spotify
    ('/playlist/', '/album/') e SoundCloud ('/sets/'). Serve a decidere se
    creare una sottocartella con il nome dell'album e proporre la
    selezione delle tracce.

    Le Mix sono escluse: hanno un '&list=' ma non sono playlist, e seguirle
    farebbe fallire il download di un video del tutto normale.
    """
    if _is_mix_url(url):
        return False
    return any(x in url for x in ('playlist?list=', '/playlist/', '/album/', '/sets/', '&list='))
