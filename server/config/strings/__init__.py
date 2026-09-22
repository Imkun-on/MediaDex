"""Le frasi che finiscono sotto gli occhi di chi usa il programma.

Una per mestiere, piu' quelle della finestra e quelle degli errori. Stanno
separate perche' cosi' si trovano, ma finiscono tutte nello stesso dizionario
piatto: ``i18n.register()`` le unisce, e le voci comuni - «Annullato»,
«Scelta non valida» - si scrivono una volta sola.

Tutte in italiano, ``'chiave': 'frase'``. C'e' stato un tempo in cui ogni voce
era ``{'it': ..., 'en': ...}`` e un menu nella barra laterale permetteva di
cambiare: quel menu non c'e' piu', e con lui il livello in piu' da
attraversare e le due frasi da tenere allineate a ogni modifica.

Chi registra, e perche' qui
    Prima lo faceva ogni motore in cima al proprio file, con un
    ``i18n.register(TESTI)`` subito dopo gli import. Funzionava finche' un
    motore era un file solo. Spezzandoli in strati e' smesso di funzionare, e
    senza fare rumore: ``server/video/probe.py`` chiamava ``t('diag.lowres')``
    e si ritrovava in mano la stringa ``'diag.lowres'``, perche' nessuno dei
    moduli nuovi si era preso la briga di registrare il catalogo di PixDex.
    Nessun errore, nessun log: solo chiavi a schermo al posto delle frasi.

    Adesso la registrazione sta qui, in un posto solo, e la fa ``i18n.t`` al
    primo uso (vedi ``_assicura_catalogo``). Nessun modulo deve piu'
    ricordarsene, che e' l'unico modo perche' non se ne dimentichi il
    prossimo.
"""
from server.config import i18n

from server.config.strings import app, audio, burn, clip, errori, pix

for _modulo in (app, audio, burn, clip, errori, pix):
    i18n.register(_modulo.TESTI)
