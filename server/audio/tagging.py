"""I tag dentro al file: titolo, artista, album, copertina, testo, volume.

Un file senza tag e' un file che sul telefono compare come «Traccia
sconosciuta» in mezzo ad altre venti uguali. Scriverli e' la differenza fra
aver scaricato della musica e aver scaricato dei file.

Si usa mutagen, che e' facoltativo: senza, il file resta valido e suona, e
manca solo l'anagrafica. Per questo ogni scrittura e' protetta e nessun
errore qui dentro fa fallire un download gia' riuscito - sarebbe buttare via
quattro minuti di rete per un titolo.
"""
from __future__ import annotations

import os

import requests

from server.audio.loudness import _misura_volume, _tag_volume
from server.sources.cover import copertina_quadrata
from server.utils.console import setup_logger

log = setup_logger('audiodex', 'audiodex.log')

try:
    from mutagen.mp4 import MP4, MP4Cover, MP4FreeForm
    _HAS_MUTAGEN = True
except ImportError:
    _HAS_MUTAGEN = False


def tag_m4a(filepath: str, title: str | None = None, artist: str | None = None,
             album: str | None = None, track_num: int | None = None,
             thumbnail_url: str | None = None, lyrics: str | None = None,
             volume: bool = True) -> None:
    """Scrive i metadati (titolo, artista, album, n. traccia, copertina, testo) nel file.

    I file .m4a usano il container MP4, quindi i tag seguono lo standard
    iTunes (©nam, ©ART, ...). La copertina viene scaricata dalla thumbnail
    di YouTube e incorporata nel file. Se mutagen non è installato non fa
    nulla: il download resta comunque valido, solo senza tag.
    """
    if not _HAS_MUTAGEN:
        log.debug('mutagen non installato - skip tagging')
        return

    try:
        audio = MP4(filepath)
        tags = audio.tags
        if tags is None:
            audio.add_tags()
            tags = audio.tags

        if title:
            tags['©nam'] = [title]
        if artist:
            tags['©ART'] = [artist]
        if album:
            tags['©alb'] = [album]
        if track_num:
            tags['trkn'] = [(track_num, 0)]
        if lyrics:
            tags['©lyr'] = [lyrics]

        if thumbnail_url:
            try:
                resp = requests.get(thumbnail_url, timeout=15)
                resp.raise_for_status()
                content_type = resp.headers.get('Content-Type', '')
                if 'png' in content_type:
                    img_format = MP4Cover.FORMAT_PNG
                else:
                    img_format = MP4Cover.FORMAT_JPEG
                # Le miniature YouTube sono 16:9 e i lettori le mostrano in un
                # quadrato: senza questo passaggio escono schiacciate o tagliate.
                quadrata = copertina_quadrata(resp.content)
                if quadrata:
                    dati, img_format = quadrata, MP4Cover.FORMAT_JPEG
                else:
                    dati = resp.content
                tags['covr'] = [MP4Cover(dati, imageformat=img_format)]
                log.debug('Copertina aggiunta: %s', title)
            except Exception as e:
                log.debug('Impossibile scaricare copertina: %s', e)

        # Volume: si misura il file appena scritto e si annota di quanto il
        # lettore deve alzarlo o abbassarlo. L'audio non viene toccato, quindi
        # non si perde niente e si disfa cancellando due tag. I nomi seguono
        # lo standard ReplayGain; nel contenitore MP4 vivono come campi liberi
        # sotto lo spazio iTunes, che e' dove VLC e foobar2000 li cercano.
        if volume:
            misura = _misura_volume(filepath)
            if misura:
                for nome, valore in _tag_volume(misura).items():
                    tags[f'----:com.apple.iTunes:{nome}'] = [
                        MP4FreeForm(valore)]
                log.debug('Volume misurato: %.2f LUFS, picco %.2f dBTP',
                          misura['i'], misura['tp'])

        audio.save()
        log.debug('Tag salvati: %s', filepath)
    except Exception as e:
        log.warning('Errore tagging %s: %s', os.path.basename(filepath), e)
