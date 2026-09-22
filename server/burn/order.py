"""In che ordine finiscono le tracce sul disco, e quanto durano.

Il problema e' che l'ordine alfabetico quasi mai e' quello giusto: «10 - …»
viene prima di «2 - …», e una raccolta scaricata da una playlist ha i file
numerati proprio cosi'. Qui si riconosce la numerazione dentro al nome e la si
rispetta; quando non ce n'e', si ripiega sulla data di creazione, che per una
cartella appena scaricata e' l'ordine in cui i brani sono arrivati.

Su un CD questo conta piu' che altrove: l'ordine sbagliato non si corregge
dopo.
"""
from __future__ import annotations

import json
import os
import re
import subprocess

from server.config import i18n
from server.utils.console import console, setup_logger
from server.utils.media import AUDIO_EXTS

t = i18n.t

log = setup_logger('burndex', 'burndex.log')

# Prefisso numerico dei file prodotti da AudioDex: "01 - Titolo.m4a".
_NUM_PREFIX = re.compile(r'^\s*(\d{1,3})\s*[-._)\s]')

def _data_creazione(path: str) -> float:
    """Data di creazione del file, in secondi.

    Su Windows st_ctime e' storicamente la creazione, ma e' in via di
    deprecazione e passera' a indicare l'ultima modifica dei metadati:
    st_birthtime (Python 3.12+) e' il campo corretto, con ripiego per le
    versioni e i filesystem che non lo espongono.
    """
    info = os.stat(path)
    return getattr(info, 'st_birthtime', info.st_mtime)


def ordina_tracce(cartella: str) -> tuple[list[str], str]:
    """Restituisce i file audio della cartella nell'ordine di masterizzazione.

    Tre criteri, in ordine di precedenza:
      1. ``ordine.txt`` nella cartella (un nome file per riga) - comando manuale;
      2. prefisso numerico nel nome ("01 - Titolo.m4a") - e' come AudioDex
         salva le playlist, quindi di norma scatta questo;
      3. data di creazione del file - ripiego per cartelle messe insieme a mano.

    Ritorna anche una descrizione del criterio usato, da mostrare all'utente:
    sul CD-R non si torna indietro, quindi deve essere chiaro *perche'*
    l'ordine e' quello.
    """
    lista = os.path.join(cartella, 'ordine.txt')
    if os.path.exists(lista):
        percorsi = []
        with open(lista, encoding='utf-8') as fh:
            for riga in fh:
                nome = riga.strip()
                if not nome or nome.startswith('#'):
                    continue
                p = os.path.join(cartella, nome)
                if not os.path.exists(p):
                    console.print(t('order.missing_file', name=nome))
                    return [], ''
                percorsi.append(p)
        return percorsi, t('order.file')

    file_audio = [os.path.join(cartella, n) for n in os.listdir(cartella)
                  if os.path.splitext(n)[1].lower() in AUDIO_EXTS]
    if not file_audio:
        return [], ''

    # Il prefisso numerico vale solo se ce l'hanno *tutti*: con un file senza
    # numero l'ordinamento diventerebbe arbitrario proprio dove conta.
    numeri = [_NUM_PREFIX.match(os.path.basename(p)) for p in file_audio]
    if all(numeri):
        coppie = sorted(zip(file_audio, numeri), key=lambda c: int(c[1].group(1)))
        return [p for p, _ in coppie], t('order.number')

    return sorted(file_audio, key=_data_creazione), t('order.created')

def durata_traccia(path: str) -> float | None:
    """Durata in secondi di un file audio, letta con ffprobe.

    Serve a calcolare la capienza prima di impegnare il masterizzatore:
    ffprobe legge l'intestazione del file senza decodificarlo, quindi risponde
    in millisecondi anche su un album intero. Decodificare per sapere quanto
    dura costerebbe minuti e centinaia di megabyte.

    Ritorna None invece di sollevare un'eccezione quando il file e' corrotto o
    non riconosciuto: il chiamante raccoglie tutti i file illeggibili e li
    elenca insieme, cosi' si sistemano in una volta sola.
    """
    try:
        out = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'json', path],
            capture_output=True, text=True, check=True, encoding='utf-8',
        )
        return float(json.loads(out.stdout)['format']['duration'])
    except (subprocess.CalledProcessError, KeyError, ValueError, json.JSONDecodeError) as exc:
        log.error('ffprobe fallito su %s: %s', path, exc)
        return None
