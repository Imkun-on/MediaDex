"""Numeri che diventano parole, e parole che diventano numeri.

Tre funzioncine, ed erano scritte due volte a testa: ``_fmt_tempo`` in ClipDex
e ``_fmt_durata`` in PixDex erano identiche riga per riga, e cosi' ``_fmt_peso``
e ``_fmt_dimensione``. Averne una copia sola non e' solo meno codice: e'
l'unico modo perche' due sezioni della stessa finestra scrivano «1:04» nello
stesso modo.

Nota su chi NON e' finito qui. ``_format_duration`` di BurnDex assomiglia a
``fmt_durata`` ma non lo e': non ha il ramo delle ore, perche' su un CD audio
nessuna traccia puo' superare gli 80 minuti. Resta in ``server/burn/``, dove
quella premessa e' vera. Unificarlo avrebbe scambiato una somiglianza per
un'uguaglianza, che e' il modo classico di rompere le cose accorpandole.
"""
from __future__ import annotations

import re

from server.config import i18n

t = i18n.t


def leggi_tempo(valore: str | None) -> float | None:
    """Converte un istante scritto a mano in secondi.

    Accetta le forme che vengono spontanee a chi guarda un lettore video:
    ``90``, ``1:30``, ``01:02:03.5``. Restituisce None se non si capisce,
    invece di indovinare: un taglio nel punto sbagliato si scopre solo
    riguardando il risultato.
    """
    if valore is None:
        return None
    testo = valore.strip()
    if not testo:
        return None
    try:
        parti = [float(p) for p in testo.split(':')]
    except ValueError:
        return None
    if not 1 <= len(parti) <= 3 or any(p < 0 for p in parti):
        return None
    secondi = 0.0
    for p in parti:
        secondi = secondi * 60 + p
    return secondi


def fmt_durata(secondi: float) -> str:
    """Formatta una durata in h:mm:ss, oppure m:ss se sta sotto l'ora."""
    s = int(secondi)
    ore, resto = divmod(s, 3600)
    minuti, sec = divmod(resto, 60)
    return f'{ore}:{minuti:02d}:{sec:02d}' if ore else f'{minuti}:{sec:02d}'


def fmt_peso(byte: int) -> str:
    """Formatta una dimensione in MB o GB, con una cifra decimale."""
    mb = byte / (1024 * 1024)
    return f'{mb / 1024:.2f} GB' if mb >= 1024 else f'{mb:.1f} MB'


# ── Come si scrive un dato che potrebbe non esserci ─────────────────────────
#
# Le tre funzioni qui sotto vengono da AudioDex e hanno tutte la stessa
# particolarita': un valore assente non diventa zero, diventa un punto
# interrogativo. Sono due cose diverse, e confonderle e' il classico modo di
# far sembrare sbagliato un programma che funziona: «0:00» dice che il brano
# dura zero, «??:??» dice che YouTube non l'ha detto.
#
# E' anche il motivo per cui non sono la stessa funzione di fmt_durata e
# fmt_peso qui sopra, che descrivono file gia' sul disco - dove una durata c'e'
# sempre, perche' si e' appena finito di leggerla.

# yt-dlp sostituisce i caratteri vietati da Windows (/ : | ? * " < >) con dei
# "sosia" Unicode a tutta larghezza (es. / -> ⧸, : -> ：, | -> ｜). Alcuni
# telefoni rifiutano questi nomi durante la copia via cavo USB, quindi li
# riconvertiamo in '_': lo stesso simbolo usato per i caratteri vietati, così
# il nome resta coerente con il controllo dei file "gia' scaricati".
_LOOKALIKE_MAP = str.maketrans({
    '⧸': '_', '⧹': '_',  # ⧸ ⧹  (al posto di / \)
    '／': '_', '＼': '_',  # ／ ＼  (al posto di / \)
    '：': '_',                 # ：     (al posto di :)
    '｜': '_',                 # ｜     (al posto di |)
    '？': '_', '＊': '_',  # ？ ＊  (al posto di ? *)
    '＂': '_',                 # ＂     (al posto di ")
    '＜': '_', '＞': '_',  # ＜ ＞  (al posto di < >)
})

# Blocchi Unicode di emoji e simboli pittografici: anche questi mandano in
# errore la copia verso il telefono, quindi li togliamo del tutto.
_EMOJI_RE = re.compile(
    '[\U0001F000-\U0001FAFF'  # emoji, emoticon e simboli pittografici
    '\U00002600-\U000027BF'   # simboli vari e dingbat
    '\U00002300-\U000023FF'   # simboli tecnici (orologi, ecc.)
    '\U00002B00-\U00002BFF'   # stelle e frecce decorative
    '︀-️'           # selettori di variazione (emoji a colori)
    '‍]+'                # giunzione a larghezza zero (emoji composte)
)


def nome_file_pulito(name: str) -> str:
    """Rende il nome del file compatibile con Windows e con i telefoni.

    Oltre a sostituire con '_' i caratteri vietati da Windows, riconverte i
    "sosia" Unicode che yt-dlp usa al loro posto (⧸ ： ｜ ...) e rimuove le
    emoji: in entrambi i casi alcuni telefoni rifiuterebbero il file durante
    la copia via cavo USB.
    """
    name = name.translate(_LOOKALIKE_MAP)
    name = _EMOJI_RE.sub('', name)
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = re.sub(r'\s{2,}', ' ', name).strip()
    return name.rstrip(' .')


def durata_o_ignota(seconds: int | float | None) -> str:
    """Converte una durata in secondi nel formato leggibile M:SS o H:MM:SS.

    Le ore compaiono solo quando servono davvero: scrivere `0:03:54` per un
    brano di quattro minuti allungherebbe la colonna di tutte le righe della
    tabella per un dato quasi sempre nullo.

    Un valore assente diventa `??:??` invece di `0:00`, perché sono due cose
    diverse: la prima è un dato che YouTube non ha fornito, la seconda una
    traccia di durata zero.
    """
    if not seconds:
        return '??:??'
    seconds = int(seconds)
    h, m, s = seconds // 3600, (seconds % 3600) // 60, seconds % 60
    if h > 0:
        return f'{h}:{m:02d}:{s:02d}'
    return f'{m}:{s:02d}'


def peso_o_ignoto(bytes_val: int | float | None) -> str:
    """Converte una dimensione in byte in una stringa leggibile (MB o GB).

    Si passa ai gigabyte oltre i 1024 MB: è la soglia che serve da quando
    esiste il download video, dove un singolo file supera tranquillamente il
    gigabyte e leggere `3891.4 MB` costringerebbe a contare le cifre.

    Come per le durate, un valore assente resta esplicito (`?? MB`).
    """
    if not bytes_val:
        return '?? MB'
    mb = bytes_val / 1048576
    if mb >= 1024:
        return f'{mb / 1024:.1f} GB'
    return f'{mb:.1f} MB'


def viste_abbreviate(views: int | float | None) -> str:
    """Converte un conteggio di visualizzazioni in forma compatta (es. 2.1 Mrd).

    Le visualizzazioni servono a distinguere a colpo d'occhio la versione
    ufficiale di un brano dai ricaricamenti: per quello basta l'ordine di
    grandezza, mentre `1.247.883.201` occuperebbe mezza tabella. Le migliaia
    si arrotondano all'unità (`350 K`), sopra il milione si tiene un decimale
    perché lì la differenza tra `1.2 Mrd` e `1.9 Mrd` è informativa.

    La stessa funzione formatta anche i mi piace e gli iscritti al canale.
    Restituisce un trattino lungo quando il dato manca, così la scheda del
    video può omettere la riga invece di mostrarla vuota.
    """
    if not views:
        return '—'
    views = int(views)
    if views >= 1_000_000_000:
        return f"{views / 1_000_000_000:.1f} {t('unit.billions')}"
    if views >= 1_000_000:
        return f"{views / 1_000_000:.1f} {t('unit.millions')}"
    if views >= 1_000:
        return f"{views / 1_000:.0f} {t('unit.thousands')}"
    return str(views)


def prefisso_traccia(track_num: int | None, total: int | None) -> str:
    """Costruisce il prefisso numerico del nome file (es. '01 - ').

    Serve a far comparire i brani sul disco (e quindi sul telefono, che
    ordina per nome file) nello stesso ordine della playlist di origine.
    Le cifre sono zero-padded sul totale delle tracce, minimo due, così
    l'ordinamento alfabetico coincide con quello numerico.
    """
    if not track_num:
        return ''
    width = max(2, len(str(total or track_num)))
    return f'{track_num:0{width}d} - '
