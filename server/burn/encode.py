"""Da file compresso a PCM, che e' l'unica cosa che un CD audio sa contenere.

Il Red Book non ammette codec: 44100 Hz, 16 bit, stereo, e basta. Ogni traccia
va quindi decodificata per intero prima di poter essere incisa, il che vuol
dire circa 850 MB di file temporanei per un disco pieno.

Le due lavorazioni facoltative stanno qui perche' e' l'unico momento in cui si
possono fare: il livellamento del volume, che misura ogni traccia e le porta
tutte alla stessa intensita' percepita, e la rifilatura dei silenzi in testa e
in coda. Dopo la decodifica non si torna indietro, e dopo l'incisione nemmeno.
"""
from __future__ import annotations

import os
import re
import subprocess

from server.config import i18n
from server.utils.console import setup_logger
from server.burn.redbook import MIN_TRACK_SECTORS, SECTOR_BYTES

t = i18n.t

log = setup_logger('burndex', 'burndex.log')

# Obiettivo di livellamento. -16 LUFS e' il valore su cui si sono allineate le
# piattaforme di ascolto: alto abbastanza da non costringere ad alzare il
# volume in auto, basso abbastanza da lasciare respiro ai picchi. Il tetto a
# -1 dBTP tiene un margine sotto lo zero, dove i convertitori dei lettori
# datati iniziano a distorcere anche senza tosatura vera.
LOUDNESS_OBIETTIVO = -16.0


PICCO_MASSIMO = -1.0


# ── Trattamento dell'audio prima di incidere ─────────────────────────────────
#
# Il CD audio e' 44.1 kHz, 16 bit, stereo, e basta: qualunque cosa si scarichi
# — un opus a 48 kHz, un m4a a 44.1, un file mono di un vecchio caricamento —
# va portata li'. Il come non e' indifferente.
#
# Scendere a 16 bit troncando i valori genera una distorsione *correlata* al
# segnale: sui passaggi deboli, code di riverbero e dissolvenze, l'orecchio la
# riconosce come suono sporco. Il dither sostituisce quella distorsione con
# rumore casuale, che invece si ignora. Misurato su un tono a -70 dBFS,
# l'energia sulle armoniche passa da +46.9 dB a +31.1 dB rispetto alla
# fondamentale: quasi 16 dB di sporcizia in meno.
#
# Il ricampionatore invece resta quello predefinito. La scelta e' voluta:
# ``soxr`` e' considerato migliore, ma non sono riuscito a misurare un
# vantaggio reale nel passaggio 48 -> 44.1, e chiederlo su una build compilata
# senza ``libsoxr`` farebbe fallire la masterizzazione a meta'. Non vale il
# rischio per un guadagno che non so dimostrare.
DITHER = 'dither_method=triangular_hp'

# Rifilatura dei silenzi: i caricamenti YouTube hanno spesso uno o due secondi
# di nulla in testa e in coda, che si sommano ai 2 secondi di stacco che IMAPI2
# inserisce comunque fra una traccia e l'altra. La coda si toglie girando il
# flusso, tagliando l'inizio e rigirandolo: ``silenceremove`` sa lavorare solo
# in testa.
_SILENZIO = ('silenceremove=start_periods=1:start_threshold=-50dB:'
             'start_silence=0.05:detection=peak')


TAGLIO_SILENZI = f'{_SILENZIO},areverse,{_SILENZIO},areverse'


def _misura_loudness(path: str) -> dict | None:
    """Misura la loudness integrata del brano secondo lo standard EBU R128.

    Serve a sapere di quanto alzare o abbassare ogni traccia perche' il disco
    esca uniforme: su una playlist YouTube i salti fra un brano e l'altro
    arrivano a 9-10 LU, cioe' la mano che corre alla manopola del volume a
    ogni cambio di traccia.

    Si usa ``ebur128`` e non la prima passata di ``loudnorm``. Danno gli
    stessi identici numeri — verificato su uno stesso file: -35.8 LUFS e
    -31.6 dBFS contro -35.78 e -31.56 — ma su un brano di quattro minuti il
    primo impiega 2.3 secondi contro 11.6. Su un CD da venti tracce sono
    ottanta secondi invece di sette minuti, ed e' la differenza fra una
    misura che si puo' fare sempre e una che si doveva chiedere.

    Restituisce None se la misura non riesce: il livellamento e' un di piu',
    non deve mai impedire una masterizzazione.
    """
    try:
        out = subprocess.run(
            ['ffmpeg', '-hide_banner', '-v', 'info', '-i', path,
             '-af', 'ebur128=framelog=quiet:peak=true', '-f', 'null', '-'],
            capture_output=True, text=True, encoding='utf-8',
            errors='replace', timeout=300,
        ).stderr
    except (subprocess.SubprocessError, OSError) as exc:
        log.warning('Misura loudness fallita su %s: %s', path, exc)
        return None

    # Il riepilogo di ebur128 e' testo indentato, non JSON: si prendono
    # l'ultima "I:" e l'ultima "Peak:", che sono quelle del riepilogo finale
    # e non quelle dei blocchi intermedi.
    letture = re.findall(r'^\s*I:\s*(-?[\d.]+)\s*LUFS', out, re.M)
    picchi = re.findall(r'^\s*Peak:\s*(-?[\d.]+)\s*dBFS', out, re.M)
    if not letture or not picchi:
        return None
    try:
        return {'i': float(letture[-1]), 'tp': float(picchi[-1])}
    except ValueError:
        return None


def _guadagno_livellamento(misura: dict | None) -> float:
    """Di quanti dB alzare o abbassare una traccia per allinearla alle altre.

    Il guadagno non supera mai il margine che resta prima del picco reale:
    spingere oltre toserebbe la forma d'onda, e una tosatura su CD non si
    torna indietro a rimediarla.
    """
    if not misura:
        return 0.0
    voluto = LOUDNESS_OBIETTIVO - misura['i']
    consentito = PICCO_MASSIMO - misura['tp']
    return round(min(voluto, consentito), 2)


def _decodifica(src: str, dst: str, guadagno_db: float = 0.0,
                rifila: bool = False) -> int:
    """Decodifica src in PCM grezzo 44.1 kHz / 16 bit / stereo dentro dst.

    IMAPI2 vuole l'audio nudo, senza header WAV, allineato al settore da
    2352 byte e lungo almeno 4 secondi: se sgarra di un byte la chiamata
    AddAudioTrack fallisce. Il riempimento con silenzio sistema entrambi i
    vincoli. Ritorna i settori occupati.

    La catena di filtri mette il guadagno *prima* della riduzione a 16 bit:
    alzare il volume dopo aver gia' quantizzato amplificherebbe anche l'errore
    di quantizzazione, buttando via il lavoro del dither.
    """
    catena = []
    if rifila:
        catena.append(TAGLIO_SILENZI)
    if guadagno_db:
        catena.append(f'volume={guadagno_db}dB')
    catena.append(f'aresample=osr=44100:out_sample_fmt=s16:{DITHER}')
    # Esplicitare il layout copre il caso dei caricamenti mono: -ac 2 lo
    # gestirebbe comunque, ma dentro la catena la conversione deve avvenire
    # prima della riduzione a 16 bit, non dopo.
    catena.append('aformat=sample_fmts=s16:sample_rates=44100:channel_layouts=stereo')

    with open(dst, 'wb') as fh:
        subprocess.run(
            ['ffmpeg', '-v', 'error', '-i', src, '-vn',
             '-af', ','.join(catena),
             '-f', 's16le', '-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '2', '-'],
            stdout=fh, stderr=subprocess.PIPE, check=True,
        )

    n = os.path.getsize(dst)
    padding = max(MIN_TRACK_SECTORS * SECTOR_BYTES - n, 0)
    padding += -(n + padding) % SECTOR_BYTES
    if padding:
        with open(dst, 'ab') as fh:
            fh.write(b'\x00' * padding)
    return (n + padding) // SECTOR_BYTES
