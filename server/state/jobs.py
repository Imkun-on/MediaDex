"""Il lavoro in corso: uno solo per volta, e come lo si ferma.

Due cose che si assomigliano poco ma stanno nello stesso posto, perche'
rispondono alla stessa domanda: c'e' un lavoro in corso, e cosa succede se
qualcuno lo interrompe.

``INTERROTTO`` e' l'evento che i thread di download guardano fra un brano e
l'altro. Serve al terminale, dove il Ctrl+C arriva davvero; nella finestra non
si presenta mai, ma il codice che scarica e' lo stesso e non deve sapere
quale dei due lo sta usando.

``Posto`` e' invece il posto di lavoro della finestra: uno solo, e va preso
prima di cominciare. Non e' pignoleria - i quattro mestieri si contendono
FFmpeg, il disco e la barra di avanzamento, e due che partono insieme non
producono il doppio del lavoro ma due meta' di niente.
"""
from __future__ import annotations

import os
import threading

from server.utils.console import setup_logger

log = setup_logger('audiodex', 'audiodex.log')


# Evento condiviso tra i thread: quando viene impostato (primo Ctrl+C) i
# download non ancora partiti vengono annullati e il programma si chiude
# in modo pulito appena terminano quelli in corso.
INTERROTTO = threading.Event()


def chiudi_con_garbo(signum, frame):
    """Gestisce Ctrl+C: il primo chiede l'arresto pulito, il secondo forza l'uscita.

    Interrompere di colpo dei download paralleli lascerebbe sul disco file
    troncati che il controllo anti-duplicati potrebbe scambiare per tracce
    complete. Il primo Ctrl+C imposta quindi un evento condiviso: i download
    già avviati arrivano in fondo, quelli in coda vengono annullati.

    Il secondo Ctrl+C serve come via di fuga se qualcosa resta bloccato — per
    esempio una richiesta di rete appesa — e usa ``os._exit`` per terminare
    davvero senza attendere i thread.
    """
    if INTERROTTO.is_set():
        log.warning('Secondo Ctrl+C - terminazione forzata')
        os._exit(1)
    log.warning('Ctrl+C ricevuto - completamento download in corso, poi arresto...')
    INTERROTTO.set()


class Posto:
    """Il posto di lavoro della finestra: uno, e chi lo prende lo dichiara.

    Controllare se e' libero e poi prenderlo sono due gesti, e fra i due c'e'
    una fessura: due clic ravvicinati - o Ctrl+Invio tenuto premuto - la
    trovano tutt'e due aperta e partono in due. Non e' solo un lavoro doppio:
    chi lavora dirotta ``sys.stdout`` sul log e lo rimette a posto alla fine, e
    con due lavori intrecciati il secondo a finire rimette quello del primo,
    lasciando l'uscita standard dirottata su un oggetto morto per il resto
    della sessione. Da li' in poi nessun modulo riesce piu' a scrivere una
    riga.

    La serratura chiude la fessura: il controllo e la presa diventano un gesto
    solo.
    """

    def __init__(self) -> None:
        self._occupato = False
        self._serratura = threading.Lock()

    def occupa(self) -> bool:
        """Prende il posto se e' libero, e dice se c'e' riuscito."""
        with self._serratura:
            if self._occupato:
                return False
            self._occupato = True
            return True

    def libera(self) -> None:
        """Rende il posto. Chiamarla piu' di una volta non fa danni."""
        with self._serratura:
            self._occupato = False
