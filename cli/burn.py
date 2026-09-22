"""BurnDex al terminale: il banner, la scelta della cartella, gli argomenti.

Il modo interattivo e' quello per cui BurnDex e' nato: si lancia senza
argomenti, si sceglie una raccolta fra quelle scaricate, e da li' in poi e' una
procedura a quattro passi con una scheda di conferma prima del punto di non
ritorno.

C'e' anche ``--info``, che non incide niente: dice quali unita' ci sono, cosa
c'e' dentro, e se questo computer e' adatto. Si usa prima di sprecare un disco.
"""
from __future__ import annotations

import argparse
import os
import sys

from rich.align import Align
from rich.box import DOUBLE, HEAVY_HEAD
from rich.markup import escape
from rich.panel import Panel
from rich.style import Style
from rich.table import Table
from rich.text import Text

from server.config import i18n
from server.config.paths import cartella_musica as _musica
from server.utils.console import LARGHEZZA, chiedi, console, passo
from server.utils.ffmpeg import check_ffmpeg
from server.utils.media import AUDIO_EXTS
from server.burn.redbook import (
    SAFE_MINUTES, sectors_to_minutes, settori_totali, velocita_x)
from server.burn.order import durata_traccia, ordina_tracce
from server.burn.drives import (
    _HAS_PYWIN32, _info_sistema, _leggi_supporto, _lettera_unita,
    _pannello_sistema, elenca_unita, nome_unita)
from server.burn.writer import DEFAULT_SPEED_X, pythoncom
from server.services.burn import SYM_DISC, masterizza_cartella

t = i18n.t


def _print_banner() -> None:
    """Stampa il banner ASCII colorato 'BurnDex' all'avvio del programma.

    Ricalca quello di AudioDex — stesse tinte, stesso riquadro doppio — per
    dichiarare a colpo d'occhio che i due strumenti appartengono allo stesso
    progetto. Sotto il disegno, una riga dice a cosa serve il programma e in
    quale standard scrive: chi lo lancia dopo mesi ritrova subito il contesto.
    """
    banner_lines = [
        r'    ____                   ____           ',
        r'   / __ )__  ___________  / __ \___  _  __',
        r'  / __  / / / / ___/ __ \/ / / / _ \| |/_/',
        r' / /_/ / /_/ / /  / / / / /_/ /  __/>  <  ',
        r'/_____/\__,_/_/  /_/ /_/_____/\___/_/|_|',
    ]
    colors = ['bright_magenta', 'magenta', 'bright_blue', 'blue', 'bright_cyan', 'cyan']
    text = Text()
    for i, line in enumerate(banner_lines):
        text.append(line + '\n', style=Style(color=colors[i % len(colors)], bold=True))
    text.append('\n' + t('banner.subtitle.burn'), style=Style(color='white', bold=True))
    text.append('  ·  ', style='dim')
    text.append(t('banner.standard'), style='dim')

    console.print()
    console.print(Panel(
        Align.center(text),
        border_style='bright_blue',
        box=DOUBLE,
        padding=(1, 2),
        width=LARGHEZZA,
    ))


def _scegli_cartella(base: str) -> str | None:
    """Mostra le raccolte presenti in risultati/musica e ne fa scegliere una.

    E' il passo 1 della procedura guidata, quello che rende BurnDex usabile
    senza ricordare percorsi: elenca le sottocartelle create da AudioDex con
    numero di tracce e durata complessiva, quest'ultima in giallo quando
    supera la capienza di un disco.

    La cartella base compare anch'essa in elenco, come "brani singoli", se
    contiene direttamente dei file audio: e' li' che AudioDex lascia i brani
    scaricati fuori da una playlist, e ignorarli li renderebbe invisibili.

    Ritorna None se l'utente esce o sbaglia la scelta; il chiamante lo
    interpreta come rinuncia e chiude senza toccare nulla.
    """
    passo(1, 4, t('step.collection'))
    if not os.path.isdir(base):
        console.print(t('common.folder_missing', path=base))
        return None

    cartelle = sorted(
        os.path.join(base, n) for n in os.listdir(base)
        if os.path.isdir(os.path.join(base, n))
    )
    # La cartella base stessa e' una candidata: AudioDex ci lascia dentro i
    # brani singoli, quelli scaricati fuori da una playlist.
    if any(os.path.splitext(n)[1].lower() in AUDIO_EXTS for n in os.listdir(base)):
        cartelle.insert(0, base)

    if not cartelle:
        console.print(t('collection.none_found', base=base))
        return None

    tabella = Table(box=HEAVY_HEAD, border_style='bright_blue', width=LARGHEZZA,
                    header_style='bold bright_blue', padding=(0, 1))
    tabella.add_column('#', style='dim_label', justify='right', width=2)
    tabella.add_column(t('collection.column'), style='bold white', overflow='ellipsis',
                       no_wrap=True, ratio=1)
    tabella.add_column(t('collection.tracks'), justify='right', style='info', width=6)
    tabella.add_column(t('collection.duration'), justify='right', style='info', width=9)

    # La durata complessiva e' il dato che decide se una raccolta ci sta su un
    # disco, ma costa un ffprobe per file: con molte raccolte l'attesa si
    # sente, quindi la si dichiara invece di lasciare il terminale muto.
    righe = []
    with console.status(t('collection.scanning'), spinner='dots'):
        for i, c in enumerate(cartelle, 1):
            tracce, _ = ordina_tracce(c)
            nome = t('collection.singles') if c == base else escape(os.path.basename(c))
            # Stesso conteggio della scaletta (stacchi inclusi), altrimenti qui
            # si leggerebbe un totale e due schermate dopo un altro.
            minuti = sectors_to_minutes(settori_totali([durata_traccia(p) for p in tracce]))
            durata = f"{minuti:.1f} {t('common.min')}"
            righe.append((str(i), nome, str(len(tracce)),
                          f'[warning]{durata}[/warning]' if minuti > SAFE_MINUTES
                          else durata))

    for riga in righe:
        tabella.add_row(*riga)

    console.print()
    console.print(tabella)

    scelta = chiedi(t('collection.prompt', disc=SYM_DISC))
    if not scelta:
        return None
    try:
        idx = int(scelta)
        if not 1 <= idx <= len(cartelle):
            raise ValueError
    except ValueError:
        console.print(t('common.invalid_choice.burn'))
        return None
    return cartelle[idx - 1]

def _modalita_info() -> None:
    """Mostra sistema, masterizzatori e disco inserito, senza scrivere nulla.

    E' la modalita' ``--info``, pensata come primo comando da lanciare: dice
    se il computer ha un lettore, se e' interno o esterno, che disco c'e'
    dentro e a quali velocita' l'unita' sa scrivere. Tutte informazioni che
    altrimenti si scoprirebbero a meta' procedura.

    E' anche lo strumento diagnostico da usare quando una masterizzazione
    fallisce: se qui l'unita' non compare piu', il problema e' il
    collegamento e non il programma.

    Non apre alcuna sessione di scrittura e non modifica nulla.
    """
    _pannello_sistema(_info_sistema())

    unita = elenca_unita()
    if not unita:
        console.print(t('info.no_imapi_drive'))
        console.print(t('info.check_external'))
        return

    tabella = Table(box=HEAVY_HEAD, border_style='bright_blue', width=LARGHEZZA,
                    header_style='bold bright_blue', padding=(0, 1))
    tabella.add_column('#', style='dim_label', justify='right', width=2)
    tabella.add_column(t('info.drive_column'), style='bold white', overflow='ellipsis',
                       no_wrap=True, ratio=1)
    tabella.add_column(t('info.disc_column'), width=18)
    tabella.add_column(t('info.speed_column'), style='dim', width=8)

    for i, rec in enumerate(unita):
        info = _leggi_supporto(rec)
        if info is None:
            stato, velocita = t('info.no_disc'), '[dim]-[/dim]'
        else:
            capienza = f'{sectors_to_minutes(info["settori"]):.0f} {t("common.min")}'
            stato = (t('info.blank', type=info['tipo'], capacity=capienza)
                     if info['vuoto']
                     else t('info.written', type=info['tipo']))
            velocita = ', '.join(velocita_x(v) for v in info['velocita']) or '-'
        tabella.add_row(str(i),
                        f'{escape(nome_unita(rec))} [dim]{escape(_lettera_unita(rec))}[/dim]',
                        stato, velocita)

    console.print()
    console.print(tabella)
    console.print()


def main() -> None:
    """Punto di ingresso: legge gli argomenti e avvia il flusso.

    Tre modalita' d'uso:
      - nessun argomento -> interattiva (sceglie la raccolta da risultati/musica);
      - --dir <cartella> -> masterizza quella cartella;
      - --info           -> elenca masterizzatori e disco inserito, senza scrivere.

    La lingua va fissata *prima* di costruire il parser, perche' i testi di
    --help vengono composti mentre il parser si crea.
    """
    # Da riga di comando si parla solo italiano: nessuna domanda all'avvio,
    # nessuna opzione da ricordare. Il catalogo bilingue resta intatto perche'
    # la GUI continua a offrire la scelta della lingua.

    parser = argparse.ArgumentParser(
        description=t('cli.desc.burn'),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=t('cli.epilog.burn'),
    )
    parser.add_argument('--dir', '-d', type=str, default=None,
                        help=t('cli.dir.burn'))
    parser.add_argument('--base', '-b', type=str,
                        default=_musica(),
                        help=t('cli.base.burn'))
    parser.add_argument('--speed', '-s', type=int, default=None,
                        help=t('cli.speed', default=DEFAULT_SPEED_X))
    parser.add_argument('--drive', type=int, default=None,
                        help=t('cli.drive'))
    parser.add_argument('--dry-run', '-n', action='store_true',
                        help=t('cli.dry_run'))
    parser.add_argument('--info', '-i', action='store_true',
                        help=t('cli.info.burn'))
    parser.add_argument('--yes', '-y', action='store_true',
                        help=t('cli.yes.burn'))
    parser.add_argument('--no-eject', action='store_true',
                        help=t('cli.no_eject'))
    parser.add_argument('--no-level', action='store_true', help=t('cli.no_level'))
    parser.add_argument('--trim', action='store_true', help=t('cli.trim'))
    args = parser.parse_args()

    _print_banner()

    if not check_ffmpeg('tools.missing'):
        sys.exit(1)

    if args.info:
        if not _HAS_PYWIN32:
            console.print(t('tools.no_pywin32'))
            console.print(t('tools.install_pywin32'))
            sys.exit(1)
        pythoncom.CoInitialize()
        _modalita_info()
        return

    cartella = os.path.abspath(args.dir) if args.dir else _scegli_cartella(os.path.abspath(args.base))
    if not cartella:
        console.print(t('common.goodbye.burn'))
        return
    if not os.path.isdir(cartella):
        console.print(t('common.folder_missing', path=cartella))
        sys.exit(1)

    try:
        codice = masterizza_cartella(
            cartella,
            speed_x=args.speed,
            dry_run=args.dry_run,
            auto_si=args.yes,
            espelli=not args.no_eject,
            indice_unita=args.drive,
            livella=not args.no_level,
            rifila=args.trim,
        )
    except KeyboardInterrupt:
        # Durante la scrittura il Ctrl+C non ferma il laser: il disco e' perso
        # comunque, ma almeno l'unita' viene rilasciata da ReleaseMedia().
        console.print(t('common.interrupted'))
        codice = 1

    sys.exit(codice)


if __name__ == '__main__':
    main()
