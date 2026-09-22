"""ClipDex al terminale: le domande, i menu, gli argomenti.

Due modi di usarlo, e nessuno dei due e' un ripiego dell'altro. Senza
argomenti fa domande: quali file, quale operazione, con che parametri - ed e'
il modo in cui si usa quando non si sa ancora cosa si vuole. Con un
sottocomando (``taglia``, ``unisci``, ``gif``, ``webp``, ``provino``,
``compat``) non chiede niente ed e' scriptabile.

Qui dentro non c'e' un solo pezzo di lavoro vero: tutto quello che fa qualcosa
sta in ``server/video/``, e questo file si limita a capire cosa e' stato
chiesto e a chiamarlo.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

from rich.align import Align
from rich.box import DOUBLE, HEAVY_HEAD
from rich.markup import escape
from rich.panel import Panel
from rich.rule import Rule
from rich.style import Style
from rich.table import Table
from rich.text import Text

from server.config import i18n
from server.config.paths import cartella_musica as _musica
from server.utils.console import LARGHEZZA, console
from server.utils.ffmpeg import check_ffmpeg
from server.utils.media import VIDEO_EXTS
from server.utils.text import fmt_durata, fmt_peso, leggi_tempo
from server.video.probe import probe
from server.video.edit import (
    CRF_DEFAULT, GIF_FPS, GIF_LARGHEZZA, PROVINO_COLONNE, PROVINO_RIGHE,
    compat, gif, nome_uscita, provino, taglia, unisci, webp,
)

t = i18n.t


def _print_banner() -> None:
    """Stampa il banner ASCII colorato 'ClipDex' all'avvio."""
    banner_lines = [
        r'   _________       ____           ',
        r'  / ____/ (_)___  / __ \___  _  __',
        r' / /   / / / __ \/ / / / _ \| |/_/',
        r'/ /___/ / / /_/ / /_/ /  __/>  <  ',
        r'\____/_/_/ .___/_____/\___/_/|_|  ',
        r'        /_/                       ',
    ]
    colors = ['bright_magenta', 'magenta', 'bright_blue', 'blue', 'bright_cyan', 'cyan']
    text = Text()
    for i, line in enumerate(banner_lines):
        text.append(line + '\n', style=Style(color=colors[i % len(colors)], bold=True))
    text.append('\n' + t('banner.subtitle.clip'), style=Style(color='white', bold=True))
    text.append('  ·  ', style='dim')
    text.append(t('banner.tagline.clip'), style='dim')

    console.print()
    console.print(Panel(Align.center(text), border_style='bright_blue',
                        box=DOUBLE, padding=(1, 2), width=LARGHEZZA))


def _passo(numero: int, totale: int, titolo: str) -> None:
    """Riga di separazione che annuncia il passo corrente."""
    console.print()
    console.print(Rule(
        Text.assemble(
            (t('step.label', n=numero, tot=totale),
             Style(color='black', bgcolor='bright_blue', bold=True)),
            ('  ', ''), (titolo.upper(), Style(color='bright_blue', bold=True)), ('  ', ''),
        ),
        style='bright_blue', align='left',
    ), width=LARGHEZZA)


def _chiedi(prompt: str) -> str:
    """Legge una risposta trattando Ctrl-C come rinuncia."""
    try:
        return console.input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        console.print()
        return ''

def _trova_video(base: str) -> list[str]:
    """Elenca i video presenti, i piu' recenti per primi."""
    trovati = []
    for radice, _dirs, files in os.walk(base):
        for nome in files:
            if os.path.splitext(nome)[1].lower() in VIDEO_EXTS:
                trovati.append(os.path.join(radice, nome))
    trovati.sort(key=os.path.getmtime, reverse=True)
    return trovati


def _scegli_video(base: str) -> str | None:
    """Fa scegliere un video fra quelli scaricati, o accetta un percorso."""
    video = _trova_video(base) if os.path.isdir(base) else []
    if not video:
        console.print(t('choose.none', path=escape(base)))
        risposta = _chiedi(t('choose.ask_path'))
        return os.path.abspath(risposta.strip('"')) if risposta else None

    tab = Table(box=HEAVY_HEAD, border_style='grey37', width=LARGHEZZA,
                header_style='bold bright_blue')
    tab.add_column('#', justify='right', width=3, style='dim')
    tab.add_column(t('choose.col_file'), overflow='ellipsis', no_wrap=True)
    tab.add_column(t('choose.col_dur'), justify='right', width=9)
    tab.add_column(t('choose.col_size'), justify='right', width=10)

    mostrati = video[:15]
    for i, path in enumerate(mostrati, 1):
        info = probe(path)
        tab.add_row(str(i), escape(os.path.basename(path)),
                    fmt_durata(info['duration']) if info else '?',
                    fmt_peso(os.path.getsize(path)))
    console.print()
    console.print(tab)

    risposta = _chiedi(t('choose.prompt'))
    if not risposta:
        return None
    if risposta.isdigit() and 1 <= int(risposta) <= len(mostrati):
        return mostrati[int(risposta) - 1]
    return os.path.abspath(risposta.strip('"'))


AZIONI = ('taglia', 'unisci', 'gif', 'webp', 'provino', 'compat')


def _scegli_azione() -> str | None:
    """Menu delle sei operazioni, per chi lancia il programma senza argomenti."""
    tab = Table(box=HEAVY_HEAD, border_style='grey37', width=LARGHEZZA,
                header_style='bold bright_blue')
    tab.add_column('#', justify='right', width=3, style='dim')
    tab.add_column(t('menu.col_action'), width=12, no_wrap=True)
    tab.add_column(t('menu.col_desc'), overflow='fold')

    for i, azione in enumerate(AZIONI, 1):
        tab.add_row(str(i), f'[bold]{azione}[/bold]', t(f'menu.{azione}'))

    console.print()
    console.print(tab)
    risposta = _chiedi(t('menu.prompt'))
    if risposta.isdigit() and 1 <= int(risposta) <= len(AZIONI):
        return AZIONI[int(risposta) - 1]
    if risposta in AZIONI:
        return risposta
    return None


def main() -> None:
    """Punto di ingresso: sottocomandi, oppure procedura guidata senza argomenti."""

    parser = argparse.ArgumentParser(
        description=t('cli.desc.clip'),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=t('cli.epilog.clip'),
    )
    parser.add_argument('--base', '-b', type=str,
                        default=_musica(),
                        help=t('cli.base.clip'))
    parser.add_argument('--crf', type=int, default=CRF_DEFAULT,
                        help=t('cli.crf.clip', default=CRF_DEFAULT))
    sub = parser.add_subparsers(dest='azione', metavar='|'.join(AZIONI))

    p = sub.add_parser('taglia', help=t('menu.taglia'))
    p.add_argument('--input', '-i', type=str, default=None, help=t('cli.input.clip'))
    p.add_argument('--output', '-o', type=str, default=None, help=t('cli.output.clip'))
    p.add_argument('--da', type=str, default=None, help=t('cli.da'))
    p.add_argument('--a', type=str, default=None, help=t('cli.a'))
    p.add_argument('--preciso', action='store_true', help=t('cli.preciso'))

    p = sub.add_parser('unisci', help=t('menu.unisci'))
    p.add_argument('--input', '-i', type=str, nargs='+', default=None,
                   help=t('cli.input_multi'))
    p.add_argument('--dir', '-d', type=str, default=None, help=t('cli.dir.clip'))
    p.add_argument('--output', '-o', type=str, default=None, help=t('cli.output.clip'))
    p.add_argument('--no-capitoli', action='store_true', help=t('cli.no_chapters'))

    for nome in ('gif', 'webp'):
        p = sub.add_parser(nome, help=t(f'menu.{nome}'))
        p.add_argument('--input', '-i', type=str, default=None, help=t('cli.input.clip'))
        p.add_argument('--output', '-o', type=str, default=None, help=t('cli.output.clip'))
        p.add_argument('--da', type=str, default=None, help=t('cli.da'))
        p.add_argument('--durata', type=str, default=None, help=t('cli.durata'))
        p.add_argument('--fps', type=int, default=GIF_FPS, help=t('cli.fps', default=GIF_FPS))
        p.add_argument('--larghezza', type=int, default=GIF_LARGHEZZA,
                       help=t('cli.larghezza', default=GIF_LARGHEZZA))

    p = sub.add_parser('provino', help=t('menu.provino'))
    p.add_argument('--input', '-i', type=str, default=None, help=t('cli.input.clip'))
    p.add_argument('--output', '-o', type=str, default=None, help=t('cli.output.clip'))
    p.add_argument('--griglia', type=str, default=f'{PROVINO_COLONNE}x{PROVINO_RIGHE}',
                   help=t('cli.griglia'))

    p = sub.add_parser('compat', help=t('menu.compat'))
    p.add_argument('--input', '-i', type=str, default=None, help=t('cli.input.clip'))
    p.add_argument('--output', '-o', type=str, default=None, help=t('cli.output.clip'))

    args = parser.parse_args()

    _print_banner()
    if not check_ffmpeg():
        sys.exit(1)

    azione = args.azione or _scegli_azione()
    if not azione:
        console.print(t('common.goodbye.clip'))
        return

    base = os.path.abspath(args.base)

    # ── unisci: piu' sorgenti, quindi un percorso a sé ──────────────────────
    if azione == 'unisci':
        sorgenti = getattr(args, 'input', None)
        cartella = getattr(args, 'dir', None)
        if cartella:
            sorgenti = _trova_video(os.path.abspath(cartella))
            sorgenti.sort()      # in una cartella conta l'ordine dei nomi
        if not sorgenti:
            console.print(t('merge.need_inputs'))
            return
        sorgenti = [os.path.abspath(s) for s in sorgenti]
        mancanti = [s for s in sorgenti if not os.path.isfile(s)]
        if mancanti:
            console.print(t('error.missing', path=escape(mancanti[0])))
            sys.exit(1)
        if len(sorgenti) < 2:
            console.print(t('merge.need_two'))
            return

        _passo(1, 2, t('step.inputs'))
        for i, s in enumerate(sorgenti, 1):
            info = probe(s)
            console.print(t('merge.item', n=i, file=escape(os.path.basename(s)),
                            durata=fmt_durata(info['duration']) if info else '?'))

        dst = (os.path.abspath(getattr(args, 'output', None))
               if getattr(args, 'output', None)
               else nome_uscita(sorgenti[0], 'ClipDex unito', '.mp4'))
        _passo(2, 2, t('step.working'))
        ok = unisci(sorgenti, dst,
                    capitoli=not getattr(args, 'no_capitoli', False), crf=args.crf)
        sys.exit(0 if ok else 1)

    # ── tutte le altre: una sola sorgente ───────────────────────────────────
    src = getattr(args, 'input', None)
    src = os.path.abspath(src) if src else _scegli_video(base)
    if not src:
        console.print(t('common.goodbye.clip'))
        return
    if not os.path.isfile(src):
        console.print(t('error.missing', path=escape(src)))
        sys.exit(1)

    esplicito = getattr(args, 'output', None)
    _passo(1, 1, t('step.working'))

    if azione == 'taglia':
        inizio = leggi_tempo(getattr(args, 'da', None))
        fine = leggi_tempo(getattr(args, 'a', None))
        if inizio is None:
            inizio = leggi_tempo(_chiedi(t('cut.ask_from')))
        if inizio is None:
            console.print(t('error.bad_time'))
            sys.exit(1)
        if fine is None and not getattr(args, 'a', None):
            fine = leggi_tempo(_chiedi(t('cut.ask_to')))
        if fine is not None and fine <= inizio:
            console.print(t('error.empty_range'))
            sys.exit(1)
        dst = os.path.abspath(esplicito) if esplicito else nome_uscita(src, 'ClipDex taglio')
        ok = taglia(src, dst, inizio, fine,
                    preciso=getattr(args, 'preciso', False), crf=args.crf)

    elif azione in ('gif', 'webp'):
        estensione = '.gif' if azione == 'gif' else '.webp'
        dst = (os.path.abspath(esplicito) if esplicito
               else nome_uscita(src, f'ClipDex {azione}', estensione))
        funzione = gif if azione == 'gif' else webp
        ok = funzione(src, dst,
                      leggi_tempo(getattr(args, 'da', None)),
                      leggi_tempo(getattr(args, 'durata', None)),
                      getattr(args, 'fps', GIF_FPS),
                      getattr(args, 'larghezza', GIF_LARGHEZZA))

    elif azione == 'provino':
        griglia = getattr(args, 'griglia', f'{PROVINO_COLONNE}x{PROVINO_RIGHE}')
        m = re.fullmatch(r'(\d+)\s*[x×]\s*(\d+)', griglia.strip())
        if not m:
            console.print(t('error.bad_grid', valore=escape(griglia)))
            sys.exit(1)
        colonne, righe = int(m.group(1)), int(m.group(2))
        dst = (os.path.abspath(esplicito) if esplicito
               else nome_uscita(src, 'ClipDex provino', '.png'))
        ok = provino(src, dst, righe, colonne)

    else:   # compat
        dst = (os.path.abspath(esplicito) if esplicito
               else nome_uscita(src, 'ClipDex compat', '.mp4'))
        ok = compat(src, dst, crf=args.crf)

    console.print()
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
