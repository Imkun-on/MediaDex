"""Dove stanno le cose, dentro e fuori dall'eseguibile.

Il problema che risolve
    Ogni modulo del progetto calcola la propria cartella con
    ``os.path.dirname(os.path.abspath(__file__))``, e finche' si lancia
    ``python MediaDex.py`` e' esattamente quello che serve.

    Dentro un eseguibile costruito con PyInstaller non lo e' piu'. In modalita'
    a file unico il contenuto viene estratto a ogni avvio in una cartella
    temporanea, e ``__file__`` punta li'. Un log scritto in quella cartella, o
    una preferenza salvata li', sparirebbero alla chiusura del programma
    insieme alla cartella stessa. E i brani scaricati finirebbero in un posto
    che nessuno andrebbe mai a cercare.

Le due cartelle, che non coincidono
    risorse   cio' che e' stato impacchettato insieme al programma e non
              cambia mai: la pagina web, le icone. Dentro l'eseguibile sta
              nella cartella temporanea; fuori, accanto ai sorgenti.

    dati      cio' che appartiene a chi usa il programma e deve restare:
              i brani scaricati, i log, la lingua scelta. Dentro
              l'eseguibile sta accanto al file .exe, dove la si trova
              aprendo la cartella; fuori, accanto ai sorgenti.

    Fuori dall'eseguibile le due coincidono, ed e' il motivo per cui finora
    la distinzione non serviva a nessuno.
"""
from __future__ import annotations

import os
import sys

# La radice del progetto quando si lavora sui sorgenti.
#
# I passi hanno un nome invece di stare dentro a tre dirname annidati: cosi'
# chi legge CONTA i livelli invece di dedurli dalle parentesi. Non e'
# pedanteria - e' la riga piu' fragile del progetto. Qui dentro finiscono i
# log, la lingua scelta, il database dei download e i brani scaricati:
# sbagliare di un livello non da' nessun errore, sposta soltanto tutte e
# quattro le cose in una cartella dove nessuno le cerchera'. Spostando questo
# file si aggiunge o si toglie un passo, e il nome dice subito se il conto
# torna.
_QUESTO_FILE = os.path.abspath(__file__)
_CARTELLA_CONFIG = os.path.dirname(_QUESTO_FILE)      # server/config
_CARTELLA_SERVER = os.path.dirname(_CARTELLA_CONFIG)  # server
_SORGENTI = os.path.dirname(_CARTELLA_SERVER)         # la radice


def impacchettato() -> bool:
    """True se stiamo girando dentro un eseguibile costruito con PyInstaller."""
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


def cartella_risorse() -> str:
    """Dove stanno i file impacchettati col programma (la pagina, le icone)."""
    return sys._MEIPASS if impacchettato() else _SORGENTI


def cartella_dati() -> str:
    """Dove stanno i file di chi usa il programma, e dove restano.

    Accanto all'eseguibile, non nella cartella temporanea: e' l'unico posto
    che chi lo ha lanciato sa ritrovare, ed e' l'unico che sopravvive alla
    chiusura.
    """
    if impacchettato():
        return os.path.dirname(os.path.abspath(sys.executable))
    return _SORGENTI


def dati(*parti: str) -> str:
    """Percorso dentro la cartella dei dati, creata se non c'e' ancora."""
    percorso = os.path.join(cartella_dati(), *parti)
    return percorso


def risorsa(*parti: str) -> str:
    """Percorso dentro la cartella delle risorse impacchettate."""
    return os.path.join(cartella_risorse(), *parti)


# ── Dove finisce quello che il programma produce ─────────────────────────────
#
# Una cartella sola, divisa per mestiere. Prima ognuno faceva a modo suo: i
# download in ``download_audio/``, i video rimasterizzati e i montaggi accanto
# al file di partenza, cioe' sparsi per il disco dovunque fosse l'originale. E
# la finestra, per i download, lo CHIEDEVA: un campo con un bottone «sfoglia»
# da riempire prima di poter premere Scarica.
#
# Adesso non lo chiede piu' e non serve saperlo: c'e' un posto, e la barra
# laterale ha un bottone che lo apre. Le sottocartelle si creano da sole al
# primo file che ci finisce dentro.

def risultati(*parti: str) -> str:
    """La cartella dei risultati, o qualcosa dentro di essa."""
    return dati('risultati', *parti)


def _assicura(percorso: str) -> str:
    """Crea la cartella se non c'e' e restituisce il percorso.

    Creare qui invece che nei chiamanti evita il difetto classico: il motore
    scrive il file, la cartella non esiste, e l'errore che arriva parla di un
    percorso invece che di quello che si stava facendo.
    """
    os.makedirs(percorso, exist_ok=True)
    return percorso


def cartella_musica() -> str:
    """I brani e i video scaricati, una sottocartella per playlist."""
    return _assicura(risultati('musica'))


def cartella_rimasterizzati() -> str:
    """I video rifatti da PixDex, piu' i confronti prima/dopo."""
    return _assicura(risultati('rimasterizzati'))


def cartella_montaggi() -> str:
    """Spezzoni, unioni, GIF e provini prodotti da ClipDex."""
    return _assicura(risultati('montaggi'))
