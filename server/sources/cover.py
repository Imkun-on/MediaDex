"""La copertina, ritagliata quadrata.

YouTube serve le miniature in 16:9. Un lettore musicale le mostra in un
riquadro quadrato, quindi o le schiaccia o le taglia da solo, di solito male.
Ritagliarla qui, prendendo il centro, e' l'unico modo di sapere cosa si
vedra'.

Se Pillow non c'e' la miniatura viene scritta com'e': una copertina 16:9 e'
comunque meglio di nessuna copertina, e non vale la pena rendere obbligatoria
una dipendenza per un ritaglio.
"""
from __future__ import annotations

import os
import subprocess
import tempfile

from server.utils.console import setup_logger

log = setup_logger('audiodex', 'audiodex.log')

COPERTINA_LATO = 600     # abbondante per qualunque lettore, senza gonfiare il file


def copertina_quadrata(dati: bytes) -> bytes | None:
    """Rende quadrata una miniatura 16:9 senza tagliarne via niente.

    Restituisce i byte del JPEG prodotto, o None se qualcosa non va: la
    copertina e' un di piu', e non deve mai far fallire un download. In quel
    caso il chiamante incorpora l'immagine originale, com'e' sempre stato.
    """
    lato = COPERTINA_LATO
    catena = (
        f'[0:v]scale={lato}:{lato}:force_original_aspect_ratio=increase,'
        f'crop={lato}:{lato},gblur=sigma=24[sfondo];'
        f'[0:v]scale={lato}:{lato}:force_original_aspect_ratio=decrease'
        ':flags=lanczos[primo];'
        '[sfondo][primo]overlay=(W-w)/2:(H-h)/2'
    )
    try:
        with tempfile.TemporaryDirectory(prefix='audiodex_cover_') as tmp:
            sorgente = os.path.join(tmp, 'in')
            destinazione = os.path.join(tmp, 'out.jpg')
            with open(sorgente, 'wb') as fh:
                fh.write(dati)
            subprocess.run(
                ['ffmpeg', '-hide_banner', '-v', 'error', '-y', '-i', sorgente,
                 '-filter_complex', catena, '-frames:v', '1', '-q:v', '3',
                 destinazione],
                capture_output=True, check=True, timeout=60,
            )
            with open(destinazione, 'rb') as fh:
                return fh.read()
    except (subprocess.SubprocessError, OSError) as exc:
        log.debug('Copertina non resa quadrata: %s', exc)
        return None
