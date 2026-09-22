"""Gli album caricati come video unico, e come capire se dividerli.

Il punto non e' tagliare: e' capire SE tagliare. Un video di un'ora con
dodici capitoli puo' essere un album da dividere in dodici tracce, oppure una
conferenza con dodici sezioni che va lasciata intera. Sbagliare nel primo
senso lascia un file da un'ora che nessun telefono sa mettere in una playlist;
sbagliare nel secondo produce dodici frammenti senza senso.

Le cinque soglie qui sotto sono i criteri con cui si decide, e sono tarate
per sbagliare dalla parte del non dividere: un album non diviso resta
ascoltabile, una conferenza fatta a pezzi no.
"""
from __future__ import annotations

import os
import subprocess

from server.audio.tagging import tag_m4a
from server.utils.console import setup_logger
from server.utils.text import nome_file_pulito, prefisso_traccia

log = setup_logger('audiodex', 'audiodex.log')

CAPITOLI_MINIMI = 3          # con due capitoli e' quasi sempre "intro + resto"


DURATA_MINIMA_ALBUM = 600    # dieci minuti: sotto, per lungo che sia, non e' un disco


DURATA_MINIMA_TRACCIA = 30   # sotto e' un segnaposto, non un brano


QUOTA_TRACCE_VALIDE = 0.8    # tolleranza per l'intro o lo stacco di coda


COPERTURA_MINIMA = 0.8       # i capitoli devono coprire quasi tutto il video


def capitoli_album(info: dict) -> list[dict] | None:
    """Decide se i capitoli di un video sono le tracce di un disco.

    Restituisce l'elenco normalizzato ``[{'n', 'inizio', 'fine', 'titolo'}]``
    se la divisione ha senso, altrimenti None. Non chiede niente e non tocca
    niente: serve solo a rispondere alla domanda "questo si puo' dividere?".
    """
    capitoli = info.get('chapters') or []
    if len(capitoli) < CAPITOLI_MINIMI:
        return None

    durata_totale = float(info.get('duration') or 0)
    if durata_totale < DURATA_MINIMA_ALBUM:
        return None

    normalizzati: list[dict] = []
    precedente = -1.0
    for i, cap in enumerate(capitoli, 1):
        try:
            inizio = float(cap.get('start_time'))
            fine = float(cap.get('end_time'))
        except (TypeError, ValueError):
            return None
        # Capitoli disordinati o sovrapposti: i dati non sono affidabili e
        # tagliare alla cieca produrrebbe tracce che si accavallano.
        if fine <= inizio or inizio < precedente:
            return None
        precedente = inizio
        normalizzati.append({
            'n': i,
            'inizio': inizio,
            'fine': min(fine, durata_totale) if durata_totale else fine,
            'titolo': (cap.get('title') or '').strip() or f'Traccia {i}',
        })

    lunghe = sum(1 for c in normalizzati
                 if c['fine'] - c['inizio'] >= DURATA_MINIMA_TRACCIA)
    if lunghe < len(normalizzati) * QUOTA_TRACCE_VALIDE:
        return None

    coperto = sum(c['fine'] - c['inizio'] for c in normalizzati)
    if durata_totale and coperto < durata_totale * COPERTURA_MINIMA:
        return None

    return normalizzati


def dividi_per_capitoli(src: str, capitoli: list[dict], cartella: str,
                         *, artista: str | None = None,
                         album: str | None = None,
                         copertina: str | None = None) -> list[str]:
    """Taglia il file nei suoi capitoli dentro ``cartella``, senza ricodificare.

    Il taglio e' in copia: costa secondi invece di minuti e non perde nulla.
    Il prezzo e' che sui *video* l'inizio si aggancia al fotogramma chiave
    piu' vicino, quindi puo' scostarsi di qualche secondo; sull'audio la
    granularita' e' di pochi millisecondi e non si nota. Del resto nemmeno i
    capitoli scritti a mano su YouTube sono precisi al fotogramma.

    I capitoli del file di partenza non vengono ereditati dagli spezzoni
    (``-map_chapters -1``): una traccia che dichiara al suo interno l'indice
    dell'intero disco confonde i lettori.

    Restituisce l'elenco dei file prodotti.
    """
    os.makedirs(cartella, exist_ok=True)
    _ext = os.path.splitext(src)[1]
    totale = len(capitoli)
    prodotti: list[str] = []

    for cap in capitoli:
        durata = cap['fine'] - cap['inizio']
        nome = prefisso_traccia(cap['n'], totale) + nome_file_pulito(cap['titolo'])
        dst = os.path.join(cartella, nome + _ext)
        try:
            subprocess.run(
                ['ffmpeg', '-v', 'error', '-y',
                 '-ss', f"{cap['inizio']:.3f}", '-t', f'{durata:.3f}',
                 '-i', src, '-c', 'copy', '-map_chapters', '-1',
                 '-avoid_negative_ts', 'make_zero', dst],
                capture_output=True, check=True, timeout=300,
            )
        except (subprocess.SubprocessError, OSError) as exc:
            log.error('Taglio del capitolo %s fallito: %s', cap['n'], exc)
            continue

        # Il tag ©lyr e i tag iTunes vivono nel container MP4: valgono per
        # .m4a e .mp4, non per il Matroska o l'Ogg.
        if _ext.lower() in ('.m4a', '.mp4'):
            tag_m4a(dst, title=cap['titolo'], artist=artista, album=album,
                     track_num=cap['n'], thumbnail_url=copertina)
        prodotti.append(dst)

    return prodotti
