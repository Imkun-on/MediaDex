"""I cinque trattamenti, e la matematica di quanto si puo' ingrandire.

Un preset non e' un pulsante: e' una catena di filtri FFmpeg costruita su
misura per QUESTO file, perche' i filtri che servono dipendono da cosa c'e'
dentro - se e' interlacciato, quanto e' compresso, se e' un cartone animato o
ripreso dal vero.

La parte che conta davvero e' pero' l'altra: fin dove ha senso ingrandire.
L'interpolazione non inventa dettaglio, lo spalma, e oltre una certa soglia
produce un file piu' pesante e non piu' bello. ``giudizio_fattore`` e'
l'unico posto del programma che lo dice in faccia, ed e' bene che sia
separato da chi disegna la tabella: cosi' la stessa risposta arriva identica
al terminale e alla finestra.
"""
from __future__ import annotations

from server.config import i18n

t = i18n.t

# ── Scala delle risoluzioni ──────────────────────────────────────────────────
# L'ingrandimento non va oltre il doppio: sopra quella soglia l'interpolazione
# non ha piu' pixel veri da cui partire e restituisce un'immagine molle, che
# poi la nitidezza puo' solo peggiorare. Meglio un 720p onesto di un 4K finto.
SCALA_ALTEZZE = (480, 720, 1080, 1440, 2160)


MAX_FATTORE_UPSCALE = 2.0

# Modalita' di ingrandimento offerte per nome, sia a schermo che con --height.
# ``None`` significa "decidi tu": e' l'automatico, che si ferma al doppio.
# Le altre sono richieste esplicite, e vengono rispettate anche quando la
# sorgente non le giustifica — ma non in silenzio: la tabella di scelta dice
# apertamente quando un 4K sarebbe solo un 360p gonfiato.
MODI_QUALITA: dict[str, int | None] = {
    'auto': None,
    'none': 0,      # nessun ingrandimento: solo pulizia, alla risoluzione nativa
    'hd': 1080,
    '2k': 1440,
    '4k': 2160,
}

# Soglie del giudizio sul fattore di ingrandimento. Fino al doppio
# l'interpolazione ha abbastanza pixel veri da cui partire; fino al triplo il
# risultato regge ma si ammorbidisce; oltre, si sta solo scrivendo un numero
# piu' grande nei metadati del file.
FATTORE_BUONO = 2.0


FATTORE_MOLLE = 3.0

# Qualita' di default per libx264: 18 e' il punto in cui la differenza dal
# sorgente smette di essere visibile a occhio, senza gonfiare il file come
# farebbe un valore piu' basso.
CRF_DEFAULT = 18


def _f_pulito(_info: dict) -> list[str]:
    """Sorgente gia' discreta: si toglie solo la sporcizia della compressione."""
    return [
        'deblock=filter=weak:block=4',
        'deband=1thr=0.008:2thr=0.008:3thr=0.008:4thr=0.008:range=16:blur=1',
    ]


def _f_standard(_info: dict) -> list[str]:
    """Il caso normale di un video YouTube: quadretti, aloni, bande."""
    return [
        'deblock=filter=weak:block=4',
        'hqdn3d=1.5:1.2:4:3',
        'deband=1thr=0.010:2thr=0.010:3thr=0.010:4thr=0.010:range=16:blur=1',
    ]


def _f_forte(_info: dict) -> list[str]:
    """Sorgente molto rovinata: si accetta di perdere un po' di micro-dettaglio.

    ``atadenoise`` media i fotogrammi vicini solo dove non c'e' movimento:
    e' il filtro giusto contro il disturbo da compressione, che salta da un
    fotogramma all'altro mentre l'immagine vera resta ferma.
    """
    return [
        'deblock=filter=strong:block=4',
        'atadenoise=0a=0.02:1a=0.02:2a=0.02:s=9',
        'hqdn3d=3:2.5:6:4.5',
        'deband=1thr=0.010:2thr=0.010:3thr=0.010:4thr=0.010:range=16:blur=1',
    ]


def _f_animazione(_info: dict) -> list[str]:
    """Cartoni e anime: linee nette e campiture piatte, regole opposte.

    Qui il disturbo va tolto con la mano leggerissima — la riduzione del
    rumore mangia le linee sottili, che nell'animazione *sono* il disegno —
    mentre la sbandatura va spinta, perche' le grandi campiture di colore
    uniforme sono proprio dove le bande si vedono di piu'.
    """
    return [
        'deblock=filter=weak:block=4',
        'hqdn3d=1:0.8:2:2',
        'deband=1thr=0.020:2thr=0.020:3thr=0.020:4thr=0.020:range=24:blur=1',
    ]


def _f_vecchio(_info: dict) -> list[str]:
    """Materiale televisivo o da nastro: prima si separano i semiquadri.

    ``bwdif`` in modalita' send_frame produce un fotogramma progressivo per
    ogni coppia di semiquadri, mantenendo la frequenza originale: raddoppiarla
    con send_field darebbe un movimento piu' fluido ma un file doppio, che su
    materiale d'archivio non ripaga.
    """
    return [
        'bwdif=mode=send_frame:parity=auto:deint=all',
        'deblock=filter=strong:block=4',
        'hqdn3d=4:3:6:4.5',
        'deband=1thr=0.012:2thr=0.012:3thr=0.012:4thr=0.012:range=16:blur=1',
    ]


PRESETS: dict[str, dict] = {
    'pulito': {
        'nome': lambda: t('preset.pulito.name'),
        'desc': lambda: t('preset.pulito.desc'),
        'filtri': _f_pulito,
        'sharpen': 0.20,
        'upscale': False,
    },
    'standard': {
        'nome': lambda: t('preset.standard.name'),
        'desc': lambda: t('preset.standard.desc'),
        'filtri': _f_standard,
        'sharpen': 0.30,
        'upscale': True,
    },
    'forte': {
        'nome': lambda: t('preset.forte.name'),
        'desc': lambda: t('preset.forte.desc'),
        'filtri': _f_forte,
        'sharpen': 0.35,
        'upscale': True,
    },
    'animazione': {
        'nome': lambda: t('preset.animazione.name'),
        'desc': lambda: t('preset.animazione.desc'),
        'filtri': _f_animazione,
        'sharpen': 0.45,
        'upscale': True,
    },
    'vecchio': {
        'nome': lambda: t('preset.vecchio.name'),
        'desc': lambda: t('preset.vecchio.desc'),
        'filtri': _f_vecchio,
        'sharpen': 0.30,
        'upscale': True,
    },
}


def altezza_obiettivo(info: dict, richiesta: int | None, preset: str) -> int:
    """Decide a che altezza portare il video.

    Senza indicazione esplicita sale al gradino successivo della scala
    standard, ma mai oltre il doppio dell'originale: il limite e' quello che
    separa un ingrandimento credibile da un'immagine gonfia e molle.
    """
    h = info['height']
    if not h:
        return 0
    if richiesta is not None:
        # Zero e' la richiesta esplicita di non ingrandire ("solo pulizia"):
        # va distinta da "nessuna richiesta", che invece lascia decidere qui.
        # Trattarle allo stesso modo — come farebbe un banale ``if richiesta``
        # — riporterebbe l'automatico proprio a chi ha chiesto di non toccare
        # la risoluzione.
        return richiesta if richiesta > 0 else h
    if not PRESETS[preset]['upscale']:
        return h

    tetto = int(h * MAX_FATTORE_UPSCALE)
    candidati = [a for a in SCALA_ALTEZZE if h < a <= tetto]
    return candidati[-1] if candidati else h


def risolvi_altezza(valore: str | None) -> int | None:
    """Traduce il valore di ``--height`` in un'altezza in pixel.

    Accetta sia i nomi (``auto``, ``hd``, ``2k``, ``4k``, ``none``) sia un
    numero. I nomi esistono perche' nessuno ragiona in "millequaranta pixel di
    altezza": si ragiona in "HD" e "4K", ed e' giusto che il programma parli
    la stessa lingua di chi lo usa. ``None`` significa automatico.
    """
    if valore is None:
        return None
    chiave = valore.strip().lower()
    if chiave in MODI_QUALITA:
        return MODI_QUALITA[chiave]
    try:
        altezza = int(chiave.rstrip('p'))
    except ValueError:
        return None
    return altezza if altezza > 0 else None


def fattore_ingrandimento(info: dict, altezza: int) -> float:
    """Di quante volte l'immagine viene ingrandita in altezza."""
    h = info['height']
    return (altezza / h) if h and altezza else 1.0


def giudizio_fattore(fattore: float) -> tuple[str, str]:
    """Restituisce (colore, chiave del commento) per un fattore di ingrandimento.

    E' il cuore dell'onesta' di questa schermata: la stessa tabella che offre
    il 4K dice anche, sulla stessa riga, che da un 360p il 4K non aggiunge
    un solo dettaglio vero.
    """
    if fattore <= 1.0:
        return 'bright_green', 'quality.note_native'
    if fattore <= FATTORE_BUONO:
        return 'bright_green', 'quality.note_ok'
    if fattore <= FATTORE_MOLLE:
        return 'yellow', 'quality.note_soft'
    return 'red', 'quality.note_fake'


def catena_filtri(preset: str, info: dict, altezza: int) -> str:
    """Compone la catena di filtri completa, nell'ordine corretto.

    Il passaggio a 10 bit in testa e il ritorno a 8 bit in coda non sono un
    vezzo: la sbandatura funziona sostituendo i gradini con una rampa, e una
    rampa ha bisogno di valori intermedi che a 8 bit semplicemente non
    esistono. Lavorare a 10 bit e scendere solo alla fine e' quello che
    distingue una sfumatura pulita da una che ha solo bande diverse.
    """
    catena: list[str] = ['format=yuv420p10le']
    catena += PRESETS[preset]['filtri'](info)

    if altezza and altezza != info['height']:
        catena.append(f'scale=-2:{altezza}:flags=lanczos')

    # La nitidezza adattiva viene per ultima e va dosata: ``cas`` alza il
    # contrasto locale solo dove trova gia' un contorno, quindi non rimarca
    # il disturbo nelle zone piatte come farebbe una maschera di contrasto
    # tradizionale.
    forza = PRESETS[preset]['sharpen']
    if forza > 0:
        catena.append(f'cas={forza}')

    catena.append('format=yuv420p')
    return ','.join(catena)
