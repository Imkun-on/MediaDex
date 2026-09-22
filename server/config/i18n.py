"""Il catalogo delle frasi che finiscono sotto gli occhi di chi usa il programma.

A cosa serve
    Tenerle in un posto solo invece che sparse nel codice. Chi deve mostrarne
    una chiama ``t('chiave')``; dove sia scritta la frase, e in che lingua, non
    e' affar suo.

Una lingua sola, l'italiano
    C'e' stato un menu a tendina per scegliere fra italiano e inglese, e non
    c'e' piu'. Era l'unica impostazione dell'intero programma, occupava un
    angolo fisso della barra laterale, e per tenerla in piedi servivano un
    metodo nell'API, un file di preferenze accanto all'eseguibile e la
    riscrittura di tutta la pagina a ogni cambio.

    I cataloghi sono quindi piatti: ``'chiave': 'frase'``, e basta. Prima ogni
    voce era ``{'it': ..., 'en': ...}``, il che voleva dire un livello in piu'
    da attraversare per leggere una stringa e due frasi da tenere allineate
    ogni volta che se ne cambiava una. Le traduzioni inglesi non sono andate
    perse: stanno nella storia di git, dove si ritrovano se un domani
    servissero.

Cosa NON viene tradotto
    I commenti, i docstring e le righe di log su file. Servono a chi legge o
    mantiene il codice, non a chi lo usa, e tradurli raddoppierebbe il lavoro
    di manutenzione senza aiutare nessuno.
"""
from __future__ import annotations

_catalogo: dict[str, str] = {}


# ── Catalogo e traduzione ────────────────────────────────────────────────────

def register(catalogo: dict[str, str]) -> None:
    """Aggiunge al catalogo comune le frasi di un programma.

    Ogni mestiere tiene le proprie in un modulo a parte di
    ``server/config/strings/``. Cosi' i cataloghi restano separati da leggere
    ma finiscono in uno solo, e le voci comuni - «Annullato», «Scelta non
    valida» - si scrivono una volta sola.

    Attenzione a una conseguenza: finiscono tutti nello stesso dizionario
    piatto, quindi due mestieri non possono chiamare allo stesso modo due
    frasi diverse. Chi ci prova vince o perde a seconda dell'ordine di
    registrazione, che e' il modo peggiore di decidere. Le chiavi che dicono
    cose diverse portano per questo il cognome del mestiere: ``cli.desc.pix``,
    ``cli.desc.clip``.
    """
    _catalogo.update(catalogo)


_catalogo_caricato = False


def _assicura_catalogo() -> None:
    """Carica i quattro cataloghi dei mestieri, al primo che serve.

    Perche' pigro invece che in cima al file: ``server.config.strings``
    importa QUESTO modulo per chiamare ``register``, quindi importarlo da qui
    in cima chiuderebbe il cerchio e Python si fermerebbe all'avvio. Fatto
    dentro la prima ``t()`` il cerchio non si chiude, perche' quando quella
    riga viene eseguita questo modulo e' gia' finito di caricare.

    Perche' qui e non nei chiamanti: finche' un motore era un file solo, era
    lui a registrare il proprio catalogo in cima. Spezzato in cinque moduli,
    ognuno avrebbe dovuto ricordarsene - e il primo che se ne fosse
    dimenticato avrebbe mostrato ``diag.lowres`` al posto di «la risoluzione
    e' bassa», senza un errore e senza una riga di log. E' successo davvero,
    ed e' il motivo per cui adesso non lo deve ricordare piu' nessuno.
    """
    global _catalogo_caricato
    if _catalogo_caricato:
        return
    _catalogo_caricato = True
    import server.config.strings      # noqa: F401  (registra importando)


def t(chiave: str, **kwargs) -> str:
    """La frase dietro una chiave, con i segnaposto riempiti.

    I segnaposto sono quelli di ``str.format`` (``{nome}``): passandoli come
    argomenti nominati la frase resta leggibile nel catalogo, e chi la scrive
    puo' metterli dove gli servono senza che chi la chiama debba sapere in che
    ordine.

    Una chiave assente non fa cadere il programma: viene restituita cosi'
    com'e', in modo che un errore di battitura si veda a schermo come stringa
    strana invece di interrompere un download a meta'.
    """
    _assicura_catalogo()
    testo = _catalogo.get(chiave)
    if testo is None:
        return chiave
    return testo.format(**kwargs) if kwargs else testo


# ── Risposte dell'utente ─────────────────────────────────────────────────────
#
# Si accettano anche le risposte in inglese, benche' le domande siano in
# italiano: chi passa la giornata a digitare 'y' lo digita anche qui, e
# vedersi annullare un'operazione per questo sarebbe irritante. Costa nulla ed
# elimina una categoria intera di errori.

_SI = frozenset({'s', 'si', 'sì', 'y', 'yes'})
_NO = frozenset({'n', 'no'})
_USCITA = frozenset({'q', 'quit', 'esci', 'exit'})
_TUTTI = frozenset({'all', 'a', 'tutti', 'tutte'})


def is_yes(risposta: str) -> bool:
    """True se la risposta e' un si', in italiano o in inglese."""
    return risposta.strip().lower() in _SI


def is_no(risposta: str) -> bool:
    """True se la risposta e' un no esplicito."""
    return risposta.strip().lower() in _NO


def is_quit(risposta: str) -> bool:
    """True se la risposta chiede di uscire."""
    return risposta.strip().lower() in _USCITA


def is_all(risposta: str) -> bool:
    """True se la risposta significa "tutti gli elementi"."""
    return risposta.strip().lower() in _TUTTI
