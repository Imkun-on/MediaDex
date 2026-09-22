"""Il filo teso fra Python e la pagina, e chi lo tiene in mano.

Perche' esiste un modulo apposta
    La finestra la crea ``MediaDex.py``, il punto d'ingresso. A raggiungerla
    devono pero' essere ``api.py`` e tutti i thread di lavoro, che di
    ``MediaDex.py`` non sanno niente e non devono saperne: un modulo del motore
    che importa il proprio punto d'ingresso chiude un cerchio e rende
    impossibile leggerne uno senza l'altro.

    La finestra sta quindi parcheggiata qui, in un modulo che non importa ne'
    l'uno ne' gli altri, e tutti la guardano dal basso.

Le due direzioni, che non si somigliano
    Dalla pagina a Python ci pensa pywebview da solo: ogni metodo pubblico di
    ``Api`` diventa ``window.pywebview.api.<nome>()``, e la risposta torna come
    promessa. Non c'e' niente da scrivere.

    Da Python alla pagina no: non esiste un canale, esiste solo «esegui questa
    riga di JavaScript». ``verso_pagina`` e' quella riga, ed e' l'unico posto
    del programma in cui si chiama ``evaluate_js``.

L'indirizzo, che viaggia per primo
    Ogni sezione della pagina ha la sua barra di avanzamento, la sua spia e la
    sua parola di stato: un messaggio che non dica a chi e' diretto non sa piu'
    dove andare. L'indirizzo pero' non si passa di mano in mano - vorrebbe dire
    aggiungere un argomento a trenta chiamate, e ricordarselo ogni volta che se
    ne aggiunge una.

    Sta invece nel thread, perche' il thread E' la risposta: un lavoro alla
    volta, e ogni lavoro appartiene alla sezione che lo ha chiesto. Lo scrive
    ``entra()``, prima riga di ogni metodo che la pagina puo' chiamare, e da li'
    in poi ogni ``verso_pagina()`` partito da quel thread sa da solo dove va.
"""
from __future__ import annotations

import json
import threading

# La finestra. Nasce vuota e la riempie il punto d'ingresso appena l'ha creata.
_finestra = None


def imposta(finestra) -> None:
    """Registra la finestra appena creata."""
    global _finestra
    _finestra = finestra


def attuale():
    """La finestra, oppure None se non esiste ancora.

    Si chiede ogni volta invece di copiarsela in una variabile: una copia presa
    troppo presto sarebbe None per sempre.
    """
    return _finestra


# ── A quale delle quattro stanze sta parlando questo thread ──────────────────

_DOVE = threading.local()


def entra(dove: str) -> None:
    """Dichiara a quale sezione appartiene il lavoro di questo thread."""
    _DOVE.sezione = dove


def qui() -> str:
    """La sezione di questo thread, o Audio se nessuno l'ha detto.

    Il ripiego non e' pigrizia: un messaggio senza indirizzo e' un difetto, e
    mandarlo in Audio lo rende visibile subito invece di farlo sparire. Un
    indirizzo sconosciuto, lato pagina, verrebbe lasciato cadere in silenzio.
    """
    return getattr(_DOVE, 'sezione', 'audio')


def json_per_js(valore) -> str:
    """JSON valido anche come pezzo di codice JavaScript.

    JSON e JavaScript non coincidono del tutto: U+2028 e U+2029 sono caratteri
    legittimi dentro una stringa JSON ma terminano una riga in JavaScript,
    quindi finirebbero dentro ``window.funzione(...)`` spezzando l'istruzione a
    meta'. Un titolo di video che li contiene farebbe fallire la chiamata in
    silenzio - l'errore lo vedrebbe solo la console della pagina, che qui non si
    apre, e i risultati non comparirebbero senza che niente lo spieghi. Si
    riscrivono nella loro forma con la barra rovesciata, che JSON accetta e
    JavaScript legge come lo stesso carattere.

    ``default=str`` copre l'altro modo di fallire in silenzio: un valore che
    json non sa serializzare - una durata come Decimal, un percorso come Path -
    farebbe alzare un'eccezione a meta' della riga, e la pagina non riceverebbe
    niente. Meglio la sua forma testuale che il nulla.
    """
    return (json.dumps(valore, ensure_ascii=False, default=str)
            .replace('\u2028', '\\u2028').replace('\u2029', '\\u2029'))


def verso_pagina(funzione: str, *argomenti) -> None:
    """Fa arrivare un messaggio alla sezione che sta lavorando, da ogni thread.

    Gli argomenti passano per JSON: e' l'unico modo di trasportare un
    dizionario Python dentro la pagina senza inventarsi una codifica, e
    protegge da apici e accenti che altrimenti spezzerebbero la chiamata.

    La pagina espone una porta sola, ``__instrada``, e l'indirizzo viaggia come
    primo argomento: prima c'erano undici nomi globali su ``window``, e nessuno
    di loro sapeva di quale sezione stesse parlando.
    """
    if _finestra is None:
        return
    try:
        args = ', '.join(json_per_js(a) for a in (qui(), funzione, list(argomenti)))
        _finestra.evaluate_js(f'window.__instrada({args})')
    except Exception:
        # Una finestra chiusa mentre un thread stava ancora riferendo non e' un
        # errore: e' il normale ordine di spegnimento.
        pass
