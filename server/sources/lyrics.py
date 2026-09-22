"""Il testo sincronizzato, cercato su LRCLIB.

E' la cosa che distingue un file scaricato da uno comprato: il testo in
formato LRC, con il tempo su ogni riga, scritto DENTRO il file. Sul telefono
scorre da solo mentre il brano suona, e nessuno deve piu' cercarlo a parte.

LRCLIB non chiede chiavi ne' registrazioni, e la ricerca si fa con artista e
titolo. Per questo meta' del modulo serve a ricavare artista e titolo da un
titolo di YouTube, che e' un problema piu' difficile di quanto sembri: fra
``(Official Video)``, ``[HD]`` e i trattini decorativi, la stessa canzone
arriva scritta in dieci modi.
"""
from __future__ import annotations

import re

import requests

from server.config.settings import REQUEST_TIMEOUT
from server.utils.console import setup_logger

log = setup_logger('audiodex', 'audiodex.log')

# API pubblica e gratuita di testi sincronizzati (formato LRC), senza chiave.
LRCLIB_API = 'https://lrclib.net/api'


def _clean_track_title(title: str) -> str:
    """Ripulisce il titolo YouTube dalle decorazioni non musicali.

    Rimuove le parentesi tipo '(Official Video)', '[HD]', '(Lyrics)' ecc.,
    che farebbero fallire la ricerca del testo nei database di lyrics.
    """
    cleaned = re.sub(
        r'[\(\[][^)\]]*(official|video|lyric|audio|visualizer|hd|4k|remaster|m/?v)[^)\]]*[\)\]]',
        '', title, flags=re.IGNORECASE,
    )
    cleaned = re.sub(r'\s{2,}', ' ', cleaned).strip(' -_|')
    return cleaned or title


def _split_artist_title(title: str, uploader: str | None = None) -> tuple[str, str]:
    """Separa artista e brano dal titolo di un video YouTube.

    I titoli musicali sono quasi sempre nel formato 'Artista - Brano
    (decorazioni)': dopo la pulizia delle decorazioni, la parte prima del
    trattino è l'artista. Se il formato manca, come artista si usa il nome
    del canale (senza il suffisso ' - Topic' dei canali auto-generati).
    Restituisce (artista, brano); artista può essere stringa vuota.
    """
    cleaned = _clean_track_title(title)
    if ' - ' in cleaned:
        artist, track = cleaned.split(' - ', 1)
        return artist.strip(), track.strip()
    artist = (uploader or '').removesuffix(' - Topic').strip()
    return artist, cleaned


def cerca_testo(title: str, artist: str, duration: int | float | None) -> tuple[str | None, str | None]:
    """Cerca su LRCLIB il testo sincronizzato (karaoke) di una traccia.

    Restituisce (testo_sincronizzato_lrc, testo_semplice); entrambi None se
    non trovato. Prima tenta la corrispondenza esatta artista+titolo+durata,
    poi una ricerca libera scartando i risultati con durata troppo diversa
    (>10s: probabilmente versione live o remix). Qualsiasi errore di rete
    viene solo loggato: i testi sono un extra, mai un motivo di fallimento.
    """
    artist, track = _split_artist_title(title, artist)

    headers = {'User-Agent': 'AudioDex/1.0 (https://github.com/Imkun-on/AudioDex)'}
    try:
        if artist and duration:
            resp = requests.get(
                f'{LRCLIB_API}/get',
                params={'artist_name': artist, 'track_name': track, 'duration': int(duration)},
                headers=headers, timeout=REQUEST_TIMEOUT,
            )
            if resp.status_code == 200:
                data = resp.json()
                if not data.get('instrumental'):
                    return data.get('syncedLyrics'), data.get('plainLyrics')

        params = {'track_name': track, 'artist_name': artist} if artist else {'q': track}
        resp = requests.get(f'{LRCLIB_API}/search', params=params, headers=headers, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            for item in resp.json():
                if item.get('instrumental'):
                    continue
                if duration and item.get('duration') and abs(item['duration'] - duration) > 10:
                    continue
                if item.get('syncedLyrics') or item.get('plainLyrics'):
                    return item.get('syncedLyrics'), item.get('plainLyrics')
    except Exception as e:
        log.debug("LRCLIB errore per '%s': %s", title, e)
    return None, None
