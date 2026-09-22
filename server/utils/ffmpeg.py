"""FFmpeg c'e' o non c'e', e se non c'e' lo si dice subito.

Tre motori su quattro non sanno fare niente senza FFmpeg, e tutti e tre
avevano la stessa funzione scritta a modo loro: ``_check_ffmpeg`` in ClipDex,
``_check_ffmpeg`` in PixDex, ``_check_tools`` in BurnDex. Le prime due erano
identiche riga per riga; la terza cambiava solo la chiave del messaggio.

Il controllo si fa una volta all'avvio, prima di qualunque altra cosa.
L'alternativa e' scoprire l'assenza di FFmpeg a meta' decodifica, dopo che chi
sta al terminale ha gia' scelto la raccolta, le tracce e la velocita' - e su
BurnDex, dopo che il disco e' gia' in movimento.

Servono ENTRAMBI gli eseguibili, e per compiti distinti: ``ffprobe`` legge le
durate senza decodificare, ``ffmpeg`` fa il lavoro. Vengono elencati insieme
quelli mancanti, cosi' chi ha installato male il pacchetto risolve tutto in un
colpo invece di scoprire il secondo problema dopo aver corretto il primo.
"""
from __future__ import annotations

import shutil

from server.config import i18n
from server.utils.console import console


def check_ffmpeg(chiave: str = 'tools.no_ffmpeg') -> bool:
    """True se ffmpeg e ffprobe sono nel PATH; altrimenti lo stampa e dice no.

    ``chiave`` esiste solo perche' BurnDex ha sempre detto la stessa cosa con
    parole sue (``tools.missing``). Unificare la logica non e' una buona
    ragione per cambiare, senza dirlo a nessuno, una frase che qualcuno legge
    da mesi.
    """
    mancanti = [nome for nome in ('ffmpeg', 'ffprobe') if not shutil.which(nome)]
    if mancanti:
        console.print(i18n.t(chiave, tools=', '.join(mancanti)))
        console.print(i18n.t('tools.install_ffmpeg'))
        return False
    return True
