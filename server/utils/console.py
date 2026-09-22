"""Configurazione del logging e tema/simboli Rich condivisi da tutti gli scraper.

Centralizza ciò che ogni scraper deve avere identico: la console Rich con i
nomi di stile usati nei markup (es. [error], [accent]), i simboli Unicode di
esito e la creazione del logger su file.
"""
from __future__ import annotations

import logging
import os
import sys

from rich.console import Console
from rich.theme import Theme

# ── Uscita a video in UTF-8 ───────────────────────────────────────────────────
# I tre programmi stampano frecce, riquadri e simboli di esito che nella
# vecchia tabella caratteri di Windows (cp1252) semplicemente non esistono. Su
# Windows Terminal non si nota, ma dentro il cmd.exe classico ogni carattere
# fuori tabella fa cadere il programma con UnicodeEncodeError — a meta' di un
# download o, peggio, di una masterizzazione.
#
# Riconfigurare i due flussi in UTF-8 elimina la caduta alla radice. Il
# ripiego ``errors='replace'`` copre il caso in cui perfino questo non
# riesca: si vedra' un punto interrogativo al posto di un'emoji, che e'
# infinitamente meglio di una traccia di errore.
for _flusso in (sys.stdout, sys.stderr):
    try:
        _flusso.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, ValueError, OSError):
        # Flusso rediretto su qualcosa che non e' un file di testo
        # riconfigurabile (una pipe gia' aperta in binario, per esempio):
        # non c'e' niente da sistemare e non c'e' niente da rompere.
        pass

# ── Tema Rich condiviso ───────────────────────────────────────
# Associa un nome semantico a ogni colore: nel codice si scrive
# [warning]...[/warning] invece del colore concreto, così la palette
# si cambia in un punto solo per tutti gli scraper.
THEME = Theme({
    "info":      "cyan",
    "success":   "bold green",
    "warning":   "bold yellow",
    "error":     "bold red",
    "title":     "bold bright_magenta",
    "dim_label": "dim white",
    "accent":    "bright_blue",
    "ok":        "green",
    "fail":      "red",
})

console = Console(theme=THEME)

# ── Simboli Unicode di esito (già colorati col markup del tema) ───────────────────────────────────────────
SYM_OK    = "[ok]\u2713[/ok]"
SYM_FAIL  = "[fail]\u2717[/fail]"
SYM_ARROW = "[accent]\u25b6[/accent]"
SYM_DOT   = "[accent]\u2022[/accent]"

# La larghezza dei pannelli, uguale per tutti e quattro gli strumenti.
#
# Stava scritta quattro volte, una per motore, tutte e quattro uguali a 68.
# Non e' un numero a caso: e' la larghezza sotto la quale un terminale
# predefinito di Windows non manda a capo le tabelle, e sopra la quale le righe
# di testo cominciano a essere faticose da seguire. Averla in un posto solo e'
# anche l'unico modo perche' i quattro restino allineati, che e' il punto:
# passando da uno all'altro si deve avere l'impressione di stare nello stesso
# programma.
LARGHEZZA = 68


def passo(numero: int, totale: int, titolo: str) -> None:
    """Riga di separazione che annuncia il passo corrente di una procedura.

    Dare un numero a ogni fase trasforma una sequenza di riquadri in una
    procedura guidata: si capisce a colpo d'occhio a che punto si e' e quanto
    manca prima del punto di non ritorno - che su BurnDex e' l'unico punto che
    conta davvero, perche' dopo c'e' un disco consumato.

    Era scritta tre volte, identica, in BurnDex, PixDex e ClipDex.
    """
    from rich.rule import Rule
    from rich.style import Style
    from rich.text import Text
    from server.config import i18n

    console.print()
    console.print(Rule(
        Text.assemble(
            (i18n.t('step.label', n=numero, tot=totale),
             Style(color='black', bgcolor='bright_blue', bold=True)),
            ('  ', ''),
            (titolo.upper(), Style(color='bright_blue', bold=True)),
            ('  ', ''),
        ),
        style='bright_blue',
        align='left',
    ), width=LARGHEZZA)


def chiedi(prompt: str) -> str:
    """Legge una risposta dal terminale, tollerando EOF e BOM iniziale.

    Il BOM compare quando l'input arriva da una pipe di PowerShell
    (``"" | python ...``), tipico delle prove da script: non essendo uno
    spazio non verrebbe tolto da ``strip()``, e una riga vuota risulterebbe
    compilata.

    Un EOF o un Ctrl+C valgono come risposta vuota invece che come eccezione:
    chi sta a meta' di una procedura a passi deve poter cambiare idea senza
    vedersi stampare un traceback.
    """
    try:
        return console.input(prompt).strip().lstrip('﻿').strip()
    except (EOFError, KeyboardInterrupt):
        return ''


def setup_logger(
    name: str,
    filename: str,
    *,
    level: int = logging.DEBUG,
    ytdlp: bool = False,
) -> logging.Logger:
    """Crea un logger che scrive solo su file, nella cartella logs/ del progetto.

    Niente handler verso il terminale: l'output a video è gestito da Rich
    (tabelle, pannelli, barre live) e righe di log in mezzo lo rovinerebbero.
    Il controllo ``if not log.handlers`` evita di aggiungere handler doppi
    se la funzione viene chiamata più volte con lo stesso nome.

    Parametri
    ---------
    name : str
        Nome del logger.
    filename : str
        Nome del file di log (verrà creato in ``logs/``).
    level : int
        Livello minimo di logging (default DEBUG).
    ytdlp : bool
        Se True crea anche il sub-logger ``<name>.ytdlp``, limitato ai
        WARNING per non riempire il file con l'output verboso di yt-dlp.
    """
    # Dentro un eseguibile la cartella di questo file e' temporanea e sparisce
    # alla chiusura: i log vanno accanto all'.exe, dove si sanno ritrovare.
    from server.config.paths import dati
    log_dir = dati('logs')
    os.makedirs(log_dir, exist_ok=True)

    log = logging.getLogger(name)
    log.setLevel(level)

    if not log.handlers:
        fh = logging.FileHandler(
            os.path.join(log_dir, filename),
            encoding='utf-8',
        )
        fh.setLevel(level)
        fmt = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
        )
        fh.setFormatter(fmt)
        log.addHandler(fh)

    if ytdlp:
        ytdlp_log = logging.getLogger(f'{name}.ytdlp')
        ytdlp_log.setLevel(logging.WARNING)

    return log
