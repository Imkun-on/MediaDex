# -*- coding: utf-8 -*-
"""Il marchio di MediaDex, disegnato una volta sola e messo nei tre posti.

    python assets/marchio.py

Cosa rappresenta
    Un disco che sulla destra si apre in una forma d'onda. Sono i due mestieri
    piu' riconoscibili del programma in un segno solo: il cerchio col foro dice
    «CD», le barre dicono «suono», e insieme dicono «questa roba la scarichi e
    la incidi».

    Prima c'era un cerchio con quattro barre di livello DENTRO, e assomigliava
    troppo al marchio di EchoScript, che ha le barre di livello anche lui. Due
    programmi diversi con due icone che si confondono nella barra delle
    applicazioni sono due programmi che si aprono per sbaglio l'uno al posto
    dell'altro.

Perche' uno script che disegna, invece delle immagini e basta
    Perche' lo stesso segno vive in tre posti: l'icona dell'eseguibile e della
    finestra, il marchio nella barra laterale, e quello sul velo di
    caricamento. Gli ultimi due sono SVG dentro ``client/index.html``.

    Tre copie a mano divergono: basta ritoccarne una e chi lancia il programma
    dal desktop vede un disegno, poi dentro la finestra ne trova un altro, a
    due secondi di distanza. Per questo le misure stanno QUI una volta sola, e
    questo script non si limita a generare il .ico e il .png: riscrive anche i
    due SVG dentro la pagina. Un comando, tre posti allineati per costruzione.

Perche' si disegna in grande e poi si rimpicciolisce
    Pillow non sa disegnare con l'antialiasing: un cerchio tracciato a 32 pixel
    viene fuori a scalini. Si disegna quindi otto volte piu' grande e si riduce
    con LANCZOS, che e' lo stesso filtro con cui PixDex ingrandisce i video.
"""
from __future__ import annotations

import os
import re

from PIL import Image, ImageDraw

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(QUI)
ICO = os.path.join(QUI, 'MediaDex.ico')
PNG = os.path.join(QUI, 'MediaDex.png')
PAGINA = os.path.join(RADICE, 'client', 'index.html')

# ── Le misure, su una tela di 100x100 ────────────────────────────────────────

# Il disco. DISCO_R e' il raggio della LINEA MEDIA dell'anello, come in SVG: il
# tratto ci sta a cavallo, meta' dentro e meta' fuori, quindi il bordo esterno
# arriva a DISCO_R + DISCO_SPESSORE/2 = 24.
DISCO_CX, DISCO_CY, DISCO_R = 26.0, 50.0, 20.0
DISCO_SPESSORE = 8.0
FORO_R = 6.5

# Le tre barre dell'onda: (x, larghezza, altezza), centrate sulla stessa linea
# orizzontale del disco.
#
# Due distanze, e contano tutt'e due.
#
# Fra una barra e l'altra: 5. Piu' stretto e a sedici pixel - la misura della
# barra delle applicazioni - lo stacco sparisce e l'onda diventa una macchia.
#
# Fra il bordo del disco e la prima barra: 12, cioe' piu' del doppio. Prima
# erano 6 contro 5, quindi praticamente uguali, e l'occhio leggeva disco e onda
# come un blocco solo appiccicato. Sono due cose diverse e devono vedersi come
# due cose diverse: lo stacco FRA i due gruppi dev'essere nettamente piu' largo
# di quello DENTRO ciascun gruppo.
BARRE = [
    (62.0, 8.0, 30.0),
    (75.0, 8.0, 56.0),
    (88.0, 8.0, 20.0),
]
BARRA_R = 4.0

# I colori del tema, gli stessi di :root in client/styles/style.css.
VERDE = (0x39, 0xFF, 0x88, 255)      # --magenta: l'accento primario
ACIDO = (0x86, 0xFF, 0x5E, 255)      # --ciano: la barra alta, per dare rilievo

# Le misure che Windows si aspetta dentro un .ico. La piu' piccola e' quella
# della barra delle applicazioni, la piu' grande quella delle anteprime grandi
# di Esplora risorse.
MISURE = [16, 24, 32, 48, 64, 128, 256]

SCALA = 8                             # si disegna otto volte piu' grande
LATO = 256


def _n(v: float) -> str:
    """Un numero come lo scriverebbe una persona: 8 e non 8.0."""
    return str(int(v)) if float(v).is_integer() else str(v)


# ── L'immagine ───────────────────────────────────────────────────────────────

def disegna(lato: int = LATO) -> Image.Image:
    """Il marchio su fondo trasparente, del lato richiesto."""
    grande = lato * SCALA
    k = grande / 100.0                # da coordinate su 100 a pixel veri
    img = Image.new('RGBA', (grande, grande), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Il disco: un anello, cioe' un cerchio tracciato con una penna spessa.
    #
    # Il riquadro e' quello del bordo ESTERNO, non della linea media, perche'
    # Pillow e SVG non tracciano allo stesso modo: in SVG il tratto sta a
    # cavallo della circonferenza, in Pillow cresce verso l'interno del
    # riquadro. Senza questa correzione l'icona sul desktop veniva piu' piccola
    # del marchio dentro la finestra, di meta' spessore per parte: uno scarto
    # che non si spiega guardando, e che fa sembrare sbagliata una delle due.
    esterno = (DISCO_R + DISCO_SPESSORE / 2) * k
    cx, cy = DISCO_CX * k, DISCO_CY * k
    d.ellipse([cx - esterno, cy - esterno, cx + esterno, cy + esterno],
              outline=VERDE, width=round(DISCO_SPESSORE * k))

    # Il foro: pieno, non vuoto. Su fondo trasparente un foro «vuoto» non si
    # vedrebbe affatto, perche' dentro il disco non c'e' niente da bucare.
    f = FORO_R * k
    d.ellipse([cx - f, cy - f, cx + f, cy + f], fill=VERDE)

    # L'onda: tre barre verticali arrotondate, centrate sulla stessa linea.
    for i, (x, larg, alt) in enumerate(BARRE):
        colore = ACIDO if i == 1 else VERDE
        d.rounded_rectangle(
            [x * k, (DISCO_CY - alt / 2) * k,
             (x + larg) * k, (DISCO_CY + alt / 2) * k],
            radius=BARRA_R * k, fill=colore)

    return img.resize((lato, lato), Image.LANCZOS)


# ── Lo stesso segno, in markup ───────────────────────────────────────────────

def svg(rientro: str) -> str:
    """Il corpo dell'SVG: gli stessi cerchi e le stesse barre.

    Le classi ``b1 b2 b3`` servono al velo di caricamento, dove le tre barre si
    muovono come un livello audio con tre ritardi diversi; ``alta`` tinge la
    barra centrale col verde acido. Il disco non ha classi perche' non si muove
    e non cambia colore: un CD che pulsa non vuol dire niente.
    """
    pezzi = [
        '<circle cx="{}" cy="{}" r="{}" fill="none" stroke="currentColor"'
        ' stroke-width="{}"/>'.format(
            _n(DISCO_CX), _n(DISCO_CY), _n(DISCO_R), _n(DISCO_SPESSORE)),
        '<circle cx="{}" cy="{}" r="{}" fill="currentColor"/>'.format(
            _n(DISCO_CX), _n(DISCO_CY), _n(FORO_R)),
    ]
    for i, (x, larg, alt) in enumerate(BARRE, start=1):
        classe = 'b2 alta' if i == 2 else 'b{}'.format(i)
        pezzi.append(
            '<rect class="{}" x="{}" y="{}" width="{}" height="{}" rx="{}"'
            ' fill="currentColor"/>'.format(
                classe, _n(x), _n(DISCO_CY - alt / 2),
                _n(larg), _n(alt), _n(BARRA_R)))
    return ''.join(rientro + p + '\n' for p in pezzi)


def riquadro(margine: float = 2.0) -> str:
    """Il viewBox stretto sul segno, con un filo di margine.

    Il segno e' piu' largo che alto - disco e onda stanno uno accanto all'altro
    - e su una tela quadrata lascerebbe due fasce vuote sopra e sotto, che
    dentro la barra laterale diventano un marchio minuscolo in mezzo al niente.

    Si calcola dalle misure vere invece di scriverlo a mano: sarebbe il quarto
    posto da tenere allineato, e il primo a restare indietro al primo ritocco.
    """
    alta = max(alt for _x, _larg, alt in BARRE)
    meta = max(DISCO_R + DISCO_SPESSORE / 2, alta / 2) + margine
    return '0 {} 100 {}'.format(_n(DISCO_CY - meta), _n(2 * meta))


def aggiorna_pagina() -> None:
    """Riscrive i due SVG dentro client/index.html con queste misure."""
    testo = open(PAGINA, encoding='utf-8').read()
    vista = riquadro()
    for classe, rientro in (('marchio-icona', ' ' * 10), ('avvio-marchio', ' ' * 8)):
        schema = re.compile(
            '(<svg class="' + classe + '" viewBox=")[^"]*("[^>]*>\n).*?(</svg>)', re.S)
        if not schema.search(testo):
            raise SystemExit('non trovo <svg class="{}"> in {}'.format(classe, PAGINA))
        testo = schema.sub(
            lambda m: (m.group(1) + vista + m.group(2) + svg(rientro)
                       + rientro[:-2] + m.group(3)),
            testo, count=1)
    open(PAGINA, 'w', encoding='utf-8', newline='\n').write(testo)
    print('  {}  (i due marchi, viewBox {})'.format(PAGINA, vista))


def scrivi() -> None:
    grande = disegna(LATO)
    grande.save(PNG)
    # Pillow ricampiona da solo le misure richieste, partendo dalla piu' grande:
    # quella la si e' gia' costruita bene qui sopra.
    grande.save(ICO, sizes=[(m, m) for m in MISURE])
    print('  {}  {}x{}'.format(PNG, LATO, LATO))
    print('  {}  {}'.format(ICO, ', '.join(str(m) for m in MISURE)))
    aggiorna_pagina()


if __name__ == '__main__':
    scrivi()
