"""Quanto suona forte una traccia, e come dirlo al lettore.

Due brani scaricati da due video diversi possono differire di dieci decibel:
in una playlist si sente, e si passa il tempo sul volume. La misura si fa con
il filtro ``ebur128`` di FFmpeg, che restituisce il volume PERCEPITO secondo
lo standard EBU R128 - non il picco, che non dice quasi niente su quanto una
cosa suoni forte.

Il valore non viene applicato al suono: si scrive nei tag ReplayGain, e chi
legge decide. Ricodificare per alzare il volume vorrebbe dire perdere
qualita' per un'operazione che il lettore sa fare da solo, a costo zero e in
modo reversibile.
"""
from __future__ import annotations

import re
import subprocess

from server.utils.console import setup_logger

log = setup_logger('audiodex', 'audiodex.log')

# Livello di riferimento dello standard ReplayGain 2.0. Nota: BurnDex usa -16
# per il CD, un filo piu' alto perche' in auto il rumore di fondo mangia i
# passaggi deboli. Sono due destinazioni diverse, non un'incoerenza.
REPLAYGAIN_RIFERIMENTO = -18.0


def _misura_volume(path: str) -> dict | None:
    """Misura loudness integrata e picco reale secondo lo standard EBU R128.

    Restituisce ``{'i': LUFS, 'tp': dBTP}`` oppure None: come per la
    copertina, non poter misurare non deve mai compromettere un download.
    """
    try:
        out = subprocess.run(
            ['ffmpeg', '-hide_banner', '-v', 'info', '-i', path,
             '-af', 'ebur128=framelog=quiet:peak=true', '-f', 'null', '-'],
            capture_output=True, text=True, encoding='utf-8',
            errors='replace', timeout=300,
        ).stderr
    except (subprocess.SubprocessError, OSError) as exc:
        log.debug('Misura del volume non riuscita su %s: %s', path, exc)
        return None

    # Il riepilogo finale di ebur128 e' testo indentato, non JSON: si prendono
    # l'ultima "I:" e l'ultima "Peak:", che sono quelle del riepilogo e non
    # quelle dei blocchi intermedi.
    letture = re.findall(r'^\s*I:\s*(-?[\d.]+)\s*LUFS', out, re.M)
    picchi = re.findall(r'^\s*Peak:\s*(-?[\d.]+)\s*dBFS', out, re.M)
    if not letture or not picchi:
        return None
    try:
        return {'i': float(letture[-1]), 'tp': float(picchi[-1])}
    except ValueError:
        return None


def _tag_volume(misura: dict) -> dict[str, bytes]:
    """Traduce la misura nei tag ReplayGain, pronti da scrivere.

    Il guadagno e' quanto il lettore deve alzare o abbassare per portare il
    brano al livello di riferimento; il picco e' lineare fra 0 e 1, come vuole
    lo standard, e serve al lettore per non tosare quando applica il guadagno.
    """
    guadagno = REPLAYGAIN_RIFERIMENTO - misura['i']
    picco_lineare = 10 ** (misura['tp'] / 20)
    return {
        'replaygain_track_gain': f'{guadagno:+.2f} dB'.encode(),
        'replaygain_track_peak': f'{picco_lineare:.6f}'.encode(),
    }
