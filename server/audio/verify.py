"""Quello che e' arrivato e' davvero quello che ci si aspettava?

Un download puo' finire senza errori e lasciare un file troncato: la rete
cade a tre quarti, yt-dlp chiude il file, e quello che resta si apre e suona -
per due minuti invece di quattro. Nessuno se ne accorge finche' non lo
ascolta, e a quel punto e' in una playlist su un telefono.

Il controllo e' semplice e costa niente: si chiede a ffprobe quanto dura il
file e lo si confronta con quanto avrebbe dovuto durare.
"""
from __future__ import annotations

import os
import shutil
import subprocess

from server.config import i18n
from server.config.settings import MIN_DISK_SPACE_MB
from server.utils.console import console, setup_logger
from server.utils.text import durata_o_ignota

t = i18n.t

log = setup_logger('audiodex', 'audiodex.log')

# Scarto tollerato fra durata dichiarata e durata reale. Il 2% copre gli
# arrotondamenti dei contenitori e l'ultimo pacchetto incompleto, senza
# lasciar passare un troncamento vero, che toglie ben altro.
TOLLERANZA_DURATA = 0.02


def _durata_reale(path: str) -> float | None:
    """Durata del file letta dal contenitore, o None se non si apre."""
    try:
        out = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=nw=1:nk=1', path],
            capture_output=True, text=True, encoding='utf-8',
            errors='replace', check=True, timeout=30,
        ).stdout.strip()
        return float(out) if out else None
    except (subprocess.SubprocessError, ValueError, OSError):
        return None


def verifica_file(path: str, durata_attesa: float | None = None) -> str:
    """Controlla che il file sia integro. Restituisce '' se lo e', altrimenti
    una descrizione del problema, pronta da mostrare e da registrare nel log.

    Un limite noto: senza ``durata_attesa`` un Ogg o un WebM troncato di netto
    passa il controllo, perche' i pacchetti rimasti sono validi e il
    contenitore dichiara onestamente la durata piu' corta. Nella pratica
    yt-dlp la durata la riporta quasi sempre, e nei contenitori MP4 il
    troncamento si vede comunque perche' l'indice sta in fondo al file e
    sparisce col taglio.
    """
    durata = _durata_reale(path)
    if durata is None:
        return t('verify.unreadable')

    if durata_attesa and durata_attesa > 0:
        mancante = durata_attesa - durata
        if mancante > max(durata_attesa * TOLLERANZA_DURATA, 1.0):
            return t('verify.truncated',
                     reale=durata_o_ignota(durata),
                     attesa=durata_o_ignota(durata_attesa))

    try:
        esito = subprocess.run(
            ['ffmpeg', '-v', 'error', '-xerror', '-i', path,
             '-map', '0:a?', '-f', 'null', '-'],
            capture_output=True, text=True, encoding='utf-8',
            errors='replace', timeout=300,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        log.warning('Verifica non eseguibile su %s: %s', path, exc)
        return ''          # non poter verificare non equivale a un file rotto

    if esito.returncode != 0 or esito.stderr.strip():
        prima_riga = (esito.stderr.strip().splitlines() or ['?'])[0]
        return t('verify.corrupt', reason=prima_riga[:80])

    return ''


def spazio_disco_sufficiente(path: str) -> bool:
    """Controlla lo spazio libero sul disco di destinazione.

    Sotto la soglia MIN_DISK_SPACE_MB avvisa e chiede conferma; restituisce
    False solo se l'utente rinuncia. Un errore di lettura non blocca: meglio
    tentare il download che fermarsi per un controllo accessorio.
    """
    try:
        os.makedirs(path, exist_ok=True)
        free_mb = shutil.disk_usage(path).free / 1048576
        if free_mb < MIN_DISK_SPACE_MB:
            log.warning('Spazio disco basso: %.0f MB liberi', free_mb)
            console.print(t('disk.low', mb=f'{free_mb:.0f}'))
            if not i18n.is_yes(console.input(t('disk.continue'))):
                return False
        else:
            log.info('Spazio disco: %.0f MB liberi', free_mb)
        return True
    except OSError:
        return True
