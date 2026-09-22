"""Far uscire dai motori l'avanzamento che gia' calcolano.

Il problema che risolve
    BurnDex, ClipDex e PixDex sanno benissimo a che punto sono: contano le
    tracce decodificate, i fotogrammi codificati, i brani scritti sul disco, e
    lo mostrano a terminale con una barra di Rich. L'interfaccia grafica, che
    li chiama come librerie, quel numero non lo vedeva: mostrava una barra che
    andava avanti e indietro, cioe' l'ammissione di non sapere niente.

    Sapere e non dirlo era il difetto: il numero c'era gia'.

Come funziona
    ``Spiato`` e' un ``Progress`` di Rich in tutto e per tutto - a terminale si
    comporta esattamente come prima - che a ogni aggiornamento riferisce anche
    a chi si e' messo in ascolto. I motori cambiano di una riga sola: la
    fabbrica ``_progress()`` costruisce ``Spiato`` invece di ``Progress``.

    Chi ascolta e' uno solo alla volta, e va bene cosi': il programma esegue
    un lavoro per volta, e il ``Posto`` in ``server/state/jobs.py`` lo
    garantisce.

Uso
    with ascolta(lambda desc, fatti, totale: ...):
        bd.masterizza_cartella(...)

    Fuori dal blocco nessuno ascolta piu', anche se il lavoro e' finito male.
"""
from __future__ import annotations

import threading
import time
from contextlib import contextmanager

from rich.progress import Progress

# Chi vuole sapere. None quando il motore gira da terminale, che e' il caso in
# cui la barra di Rich basta a se stessa.
_ascoltatore = None

# Rich aggiorna anche dieci volte al secondo, e ogni notifica all'interfaccia
# attraversa il ponte con JavaScript: oltre una certa frequenza non si vede
# nessuna differenza e si spreca soltanto. Un quinto di secondo e' fluido.
_INTERVALLO = 0.15
_ultimo = [0.0]
_serratura = threading.Lock()


@contextmanager
def ascolta(funzione):
    """Mette in ascolto ``funzione`` per la durata del blocco.

    La firma attesa e' ``funzione(descrizione, fatti, totale)``, con
    ``totale`` che puo' essere None quando il motore stesso non lo sa.
    """
    global _ascoltatore
    with _serratura:
        precedente, _ascoltatore = _ascoltatore, funzione
        _ultimo[0] = 0.0
    try:
        yield
    finally:
        with _serratura:
            _ascoltatore = precedente


def _riferisci(descrizione: str, fatti: float, totale: float | None,
               forza: bool = False) -> None:
    funzione = _ascoltatore
    if funzione is None:
        return
    adesso = time.monotonic()
    # L'ultimo aggiornamento passa sempre: e' quello che porta la barra al
    # fondo, e perderlo la lascerebbe al 98% per sempre.
    if not forza and totale and fatti >= totale:
        forza = True
    if not forza and adesso - _ultimo[0] < _INTERVALLO:
        return
    _ultimo[0] = adesso
    try:
        funzione(descrizione, fatti, totale)
    except Exception:
        # Vale la stessa regola dei ganci di yt-dlp: un difetto nella barra non
        # puo' far fallire il lavoro vero.
        pass


class Spiato(Progress):
    """Un ``Progress`` che, oltre a disegnare, riferisce."""

    def _dillo(self, task_id, forza: bool = False) -> None:
        try:
            compito = self._tasks[task_id]
        except (KeyError, AttributeError):
            return
        _riferisci(str(compito.description or ''), float(compito.completed or 0),
                   float(compito.total) if compito.total else None, forza)

    def add_task(self, *a, **k):
        task_id = super().add_task(*a, **k)
        # Un compito appena nato e' l'inizio di una fase: si annuncia sempre,
        # altrimenti la barra resta ferma sul totale della fase precedente.
        self._dillo(task_id, forza=True)
        return task_id

    def update(self, task_id, *a, **k):
        super().update(task_id, *a, **k)
        self._dillo(task_id)

    def advance(self, task_id, advance=1):
        super().advance(task_id, advance)
        self._dillo(task_id)
