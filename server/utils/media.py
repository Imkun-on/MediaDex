"""Quali estensioni valgono come filmato e quali come audio.

Sono elenchi di ESTENSIONI, col punto davanti, per riconoscere un file che sta
gia' sul disco: ``.mp4``, ``.m4a``. Si usano per frugare in una cartella e per
filtrare un selettore di file.

Da non confondere con i FORMATI DI USCITA di AudioDex - ``m4a``, ``mp3``,
``mp4`` senza punto - che dicono in cosa convertire un download e vivono in
``server/config/settings.py``. Si assomigliavano abbastanza da chiamarsi
uguali, ``AUDIO_EXTS`` e ``VIDEO_EXTS``, in due file diversi e con due
significati diversi: mettendoli nello stesso modulo sotto lo stesso nome si
sarebbe rotto tutto in silenzio, perche' ``'.mp4' in FORMATI_VIDEO`` e'
perfettamente valido e perfettamente falso.
"""
from __future__ import annotations

# Contenitori video che ClipDex e PixDex sanno aprire. L'elenco era scritto
# due volte, uguale, nei due moduli.
VIDEO_EXTS = frozenset({'.mp4', '.mkv', '.webm', '.avi', '.mov', '.m4v',
                        '.flv', '.wmv', '.mpg', '.mpeg', '.ts', '.m2ts'})

# Cosa BurnDex accetta come traccia da incidere. C'e' dentro anche ``.mp4``
# perche' un file audio scaricato da AudioDex ha spesso quel contenitore.
AUDIO_EXTS = frozenset({'.m4a', '.mp3', '.opus', '.mp4', '.wav',
                        '.flac', '.aac', '.ogg', '.wma'})
