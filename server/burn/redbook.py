"""L'aritmetica del Red Book: settori, minuti, stacchi, velocita'.

Un CD audio non si misura in megabyte. L'unita' e' il SETTORE, e un secondo
di audio ne occupa esattamente 75 per definizione dello standard: la
conversione e' esatta, non approssimata. Capienza del disco, spazio libero e
lunghezza delle tracce arrivano in settori sia dallo standard sia da IMAPI2; i
minuti servono solo a mostrarli a chi guarda.

Qui dentro non si parla con niente e con nessuno: sono numeri che entrano e
numeri che escono. E' il modulo piu' in basso di tutto ``server/burn/``, ed e'
anche l'unico che si puo' leggere per intero senza sapere cosa sia IMAPI2.
"""
from __future__ import annotations


# ── Parametri del formato CD audio (standard Red Book) ───────────────────────
SECTOR_BYTES = 2352       # Dimensione di un settore audio: IMAPI2 pretende


                          # tracce esattamente multiple di questo valore
SECTORS_PER_SECOND = 75   # 75 settori/s = velocita' 1x


MIN_TRACK_SECTORS = 300   # 4 secondi: traccia piu' corta ammessa dallo standard


PREGAP_SECTORS = 150      # 2 secondi di stacco inseriti prima di ogni traccia


SAFE_MINUTES = 79         # Margine di sicurezza sugli 80 nominali: il bordo


                          # esterno e' la zona che i lettori usurati sbagliano
CD_NOMINALE = 80 * 60 * 75  # Settori di un CD-R da 80 minuti: serve come metro

def format_duration(seconds: float | None) -> str:
    """Converte una durata in secondi nel formato leggibile M:SS.

    Qui, a differenza di AudioDex, non esiste il ramo con le ore: su un CD
    audio nessuna traccia puo' superare gli 80 minuti, quindi i minuti
    bastano sempre e il codice resta piu' corto di quello equivalente.
    """
    if not seconds:
        return '??:??'
    seconds = int(seconds)
    return f'{seconds // 60}:{seconds % 60:02d}'


def sectors_to_minutes(sectors: int) -> float:
    """Converte un numero di settori nei minuti di audio corrispondenti.

    Il settore e' l'unita' di misura con cui ragionano sia lo standard Red
    Book sia IMAPI2: capienza del disco, spazio libero e lunghezza delle
    tracce arrivano tutti in settori. I minuti servono solo a mostrarli.

    La conversione e' esatta e non approssimata, perche' un secondo di audio
    occupa esattamente 75 settori per definizione dello standard.
    """
    return sectors / SECTORS_PER_SECOND / 60


def settori_totali(durate: list[float | None]) -> int:
    """Settori occupati da un elenco di brani, stacchi inclusi.

    Una traccia va arrotondata al settore pieno e non puo' durare meno di
    4 secondi; a ciascuna si aggiungono i 2 secondi di stacco che il
    masterizzatore inserisce prima. Sommare le sole durate darebbe un totale
    ottimistico di qualche decimo di minuto, abbastanza per far sforare un
    disco che sembrava pieno al limite.
    """
    totale = 0
    for dur in durate:
        settori = max(int(dur * SECTORS_PER_SECOND) + 1, MIN_TRACK_SECTORS) if dur else 0
        totale += settori + PREGAP_SECTORS
    return totale


def velocita_x(sectors_per_second: int) -> str:
    """Formatta una velocita' di scrittura in multipli di 1x, arrotondata.

    Le unita' dichiarano valori grezzi leggermente sfasati (599 invece di 600
    per gli 8x): si arrotonda per mostrarli, ma il valore grezzo va conservato
    perche' e' l'unico che SetWriteSpeed accetta senza discutere.
    """
    return f'{round(sectors_per_second / SECTORS_PER_SECOND)}x'
