"""PixDex al terminale: i pannelli, le domande, gli argomenti.

Il pannello delle risoluzioni e' la cosa che questo file esiste per disegnare.
Non e' un elenco fisso: ogni riga porta il fattore di ingrandimento calcolato
su quel file e il giudizio che ne consegue, e la stessa riga che offre il 4K
dice, quando e' il caso, che da quella sorgente non aggiunge un dettaglio
vero. Il giudizio non e' scritto qui - arriva da ``server/video/presets.py`` -
proprio perche' la finestra ne mostra uno identico.
"""
from __future__ import annotations

import argparse
import os
import sys

from rich.align import Align
from rich.box import DOUBLE, HEAVY_HEAD, ROUNDED
from rich.markup import escape
from rich.panel import Panel
from rich.rule import Rule
from rich.style import Style
from rich.table import Table
from rich.text import Text

from server.config import i18n
from server.config.paths import cartella_musica as _musica
from server.utils.console import LARGHEZZA, SYM_OK, console
from server.utils.ffmpeg import check_ffmpeg
from server.utils.media import VIDEO_EXTS
from server.utils.text import fmt_durata, fmt_peso
from server.video.probe import diagnosi, e_un_filmato, probe
from server.video.presets import (
    CRF_DEFAULT, FATTORE_BUONO, PRESETS,
    altezza_obiettivo, catena_filtri, fattore_ingrandimento,
    giudizio_fattore,
    risolvi_altezza,
)
from server.video.remaster import confronto, nome_uscita, rimasterizza

t = i18n.t


def _print_banner() -> None:
    """Stampa il banner ASCII colorato 'PixDex' all'avvio del programma.

    Stesse tinte e stesso riquadro doppio di AudioDex e BurnDex: chi apre il
    terminale capisce a colpo d'occhio che e' lo stesso progetto.
    """
    banner_lines = [
        r'    ____  _      ____           ',
        r'   / __ \(_)  __/ __ \___  _  __',
        r'  / /_/ / / |/_/ / / / _ \| |/_/',
        r' / ____/ />  </ /_/ /  __/>  <  ',
        r'/_/   /_/_/|_/_____/\___/_/|_|  ',
    ]
    colors = ['bright_magenta', 'magenta', 'bright_blue', 'blue', 'bright_cyan', 'cyan']
    text = Text()
    for i, line in enumerate(banner_lines):
        text.append(line + '\n', style=Style(color=colors[i % len(colors)], bold=True))
    text.append('\n' + t('banner.subtitle.pix'), style=Style(color='white', bold=True))
    text.append('  ·  ', style='dim')
    text.append(t('banner.tagline.pix'), style='dim')

    console.print()
    console.print(Panel(
        Align.center(text),
        border_style='bright_blue',
        box=DOUBLE,
        padding=(1, 2),
        width=LARGHEZZA,
    ))


def _passo(numero: int, totale: int, titolo: str) -> None:
    """Riga di separazione che annuncia il passo corrente della procedura."""
    console.print()
    console.print(Rule(
        Text.assemble(
            (t('step.label', n=numero, tot=totale),
             Style(color='black', bgcolor='bright_blue', bold=True)),
            ('  ', ''),
            (titolo.upper(), Style(color='bright_blue', bold=True)),
            ('  ', ''),
        ),
        style='bright_blue',
        align='left',
    ), width=LARGHEZZA)


def _chiedi(prompt: str) -> str:
    """Legge una risposta dal terminale trattando Ctrl-C come rinuncia."""
    try:
        return console.input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        console.print()
        return ''


def _pannello_sorgente(info: dict) -> None:
    """Mostra la carta d'identita' del file di partenza.

    Serve a rendere evidente il tetto invalicabile del lavoro: se la sorgente
    e' 360p, nessun preset produrra' un vero 1080p, e vederlo scritto prima di
    partire evita l'aspettativa sbagliata.
    """
    tab = Table(box=ROUNDED, show_header=False, border_style='grey37',
                width=LARGHEZZA, padding=(0, 1))
    tab.add_column(style='dim_label', no_wrap=True, width=22)
    tab.add_column(style='white')

    tab.add_row(t('info.file'), escape(os.path.basename(info['path'])))
    tab.add_row(t('info.resolution'), f"{info['width']} × {info['height']}")
    tab.add_row(t('info.fps'), f"{info['fps']:.2f}")
    tab.add_row(t('info.codec'), f"{info['codec']}  ({info['pix_fmt']})")
    tab.add_row(t('info.bitrate'), f"{info['bitrate'] / 1000:.0f} kbit/s")
    tab.add_row(t('info.duration'), fmt_durata(info['duration']))
    tab.add_row(t('info.size'), fmt_peso(info['size']))
    if info['interlaced']:
        tab.add_row(t('info.scan'), t('info.interlaced'))

    console.print()
    console.print(Panel(tab, title=t('info.title'), title_align='left',
                        border_style='bright_blue', box=ROUNDED,
                        width=LARGHEZZA, padding=(0, 0)))


def _pannello_diagnosi(problemi: list[str], consigliato: str) -> None:
    """Mostra i difetti rilevati e il preset che li affronta."""
    corpo = Text()
    for p in problemi:
        corpo.append('  • ', style='bright_blue')
        corpo.append(p + '\n', style='white')
    corpo.append('\n')
    corpo.append('  ' + t('diag.suggested') + ' ', style='dim')
    corpo.append(PRESETS[consigliato]['nome'](), style='bold bright_green')

    console.print()
    console.print(Panel(corpo, title=t('diag.title'), title_align='left',
                        border_style='bright_blue', box=ROUNDED,
                        width=LARGHEZZA, padding=(0, 1)))


def _scegli_qualita(info: dict, preset: str) -> int | None:
    """Fa scegliere a che risoluzione portare il video.

    Mostra per ogni modalita' il risultato concreto su *questo* file — non
    l'etichetta commerciale — con il fattore di ingrandimento e un giudizio.
    Vedere scritto "360p → 2160p, 6.00×, nessun dettaglio in piu'" accanto
    alla voce 4K vale piu' di qualsiasi avvertenza in un manuale.

    Restituisce l'altezza scelta, oppure None se si rinuncia.
    """
    automatica = altezza_obiettivo(info, None, preset)

    voci: list[tuple[str, int]] = [
        ('quality.auto', automatica),
        ('quality.none', info['height']),
        ('quality.hd', 1080),
        ('quality.2k', 1440),
        ('quality.4k', 2160),
    ]

    # Le larghezze sono fissate a mano perche' la somma deve stare nei 68
    # caratteri comuni a tutto il progetto: lasciate libere, la colonna del
    # commento si stringe fino a spezzare le parole a meta'.
    tab = Table(box=HEAVY_HEAD, border_style='grey37', width=LARGHEZZA,
                header_style='bold bright_blue', padding=(0, 1))
    tab.add_column('#', justify='right', width=2, style='dim')
    tab.add_column(t('quality.col_mode'), width=14, no_wrap=True)
    tab.add_column(t('quality.col_result'), width=21, justify='right')
    tab.add_column(t('quality.col_note'), width=18, no_wrap=True)

    for i, (chiave, altezza) in enumerate(voci, 1):
        fattore = fattore_ingrandimento(info, altezza)
        colore, nota = giudizio_fattore(fattore)
        etichetta = t(chiave)
        if chiave == 'quality.auto':
            etichetta = '★ ' + etichetta
        risultato = (f"{info['height']}p → [bold]{altezza}p[/bold]  "
                     f'[{colore}]{fattore:.2f}×[/{colore}]'
                     if altezza != info['height']
                     else f"[bold]{altezza}p[/bold]  [{colore}]{fattore:.2f}×[/{colore}]")
        tab.add_row(str(i), f'[{colore}]{etichetta}[/{colore}]', risultato,
                    f'[{colore}]{t(nota)}[/{colore}]')

    tab.add_row(str(len(voci) + 1), t('quality.custom'), '', '')

    console.print()
    console.print(tab)
    console.print(t('quality.hint'))

    risposta = _chiedi(t('quality.prompt'))
    if not risposta:
        return automatica
    if not risposta.isdigit():
        console.print(t('quality.invalid'))
        return automatica

    scelta = int(risposta)
    if 1 <= scelta <= len(voci):
        return voci[scelta - 1][1]
    if scelta == len(voci) + 1:
        libera = _chiedi(t('quality.custom_prompt'))
        altezza = risolvi_altezza(libera)
        if altezza:
            return altezza
        console.print(t('quality.invalid'))
        return automatica

    console.print(t('quality.invalid'))
    return automatica


def _pannello_piano(info: dict, preset: str, altezza: int,
                    catena: str, gpu: bool, crf: int, dst: str) -> None:
    """Mostra cosa verra' fatto, prima di farlo.

    Una rimasterizzazione dura minuti od ore: vedere prima la catena di
    filtri e la risoluzione d'arrivo permette di correggere una scelta
    sbagliata subito, invece di scoprirla a lavoro finito.
    """
    tab = Table(box=ROUNDED, show_header=False, border_style='grey37',
                width=LARGHEZZA, padding=(0, 1))
    tab.add_column(style='dim_label', no_wrap=True, width=22)
    tab.add_column(style='white', overflow='fold')

    tab.add_row(t('plan.preset'), f"[bold bright_green]{PRESETS[preset]['nome']()}[/]")
    tab.add_row('', f"[dim]{PRESETS[preset]['desc']()}[/dim]")
    if altezza and altezza != info['height']:
        fattore = fattore_ingrandimento(info, altezza)
        colore, nota = giudizio_fattore(fattore)
        tab.add_row(t('plan.resolution'),
                    f"{info['height']}p [dim]→[/dim] [bold]{altezza}p[/bold]"
                    f"  [{colore}]{fattore:.2f}×[/{colore}]")
        # L'avviso compare solo quando serve, e dice cosa aspettarsi invece di
        # limitarsi a sconsigliare: chi ha scelto il 4K sapendo cosa fa deve
        # poter tirare dritto senza sentirsi rimproverare a ogni lancio.
        if fattore > FATTORE_BUONO:
            tab.add_row('', f'[{colore}]{t(nota)}[/{colore}]')
    else:
        tab.add_row(t('plan.resolution'), f"{info['height']}p  [dim]({t('plan.no_upscale')})[/dim]")
    tab.add_row(t('plan.encoder'),
                'h264_amf  [dim](GPU AMD)[/dim]' if gpu
                else f'libx264  [dim](CRF {crf})[/dim]')
    tab.add_row(t('plan.audio'), t('plan.audio_copy'))
    tab.add_row(t('plan.output'), escape(os.path.basename(dst)))
    tab.add_row(t('plan.filters'), f'[dim]{escape(catena)}[/dim]')

    console.print()
    console.print(Panel(tab, title=t('plan.title'), title_align='left',
                        border_style='bright_blue', box=ROUNDED,
                        width=LARGHEZZA, padding=(0, 0)))


def _pannello_risultato(info: dict, dst: str, confronto: str | None) -> None:
    """Riepilogo finale: cosa e' cambiato e dove trovare i file."""
    nuovo = probe(dst)
    tab = Table(box=ROUNDED, show_header=False, border_style='grey37',
                width=LARGHEZZA, padding=(0, 1))
    tab.add_column(style='dim_label', no_wrap=True, width=22)
    tab.add_column(style='white', overflow='fold')

    if nuovo:
        tab.add_row(t('result.resolution'),
                    f"{info['width']}×{info['height']}  [dim]→[/dim]  "
                    f"[bold]{nuovo['width']}×{nuovo['height']}[/bold]")
        delta = nuovo['size'] - info['size']
        segno = '+' if delta >= 0 else '−'
        tab.add_row(t('result.size'),
                    f"{fmt_peso(info['size'])}  [dim]→[/dim]  "
                    f"[bold]{fmt_peso(nuovo['size'])}[/bold]"
                    f"  [dim]({segno}{fmt_peso(abs(delta))})[/dim]")
    tab.add_row(t('result.file'), escape(dst))
    if confronto:
        tab.add_row(t('result.compare'), escape(confronto))
        tab.add_row('', f"[dim]{t('result.compare_hint')}[/dim]")

    console.print()
    console.print(Panel(tab, title=f"{SYM_OK} {t('result.title')}",
                        title_align='left', border_style='bright_green',
                        box=ROUNDED, width=LARGHEZZA, padding=(0, 0)))


def _trova_video(base: str) -> list[str]:
    """Elenca i video presenti nella cartella dei download, piu' recenti prima."""
    trovati: list[str] = []
    for radice, _dirs, files in os.walk(base):
        for nome in files:
            if os.path.splitext(nome)[1].lower() in VIDEO_EXTS:
                trovati.append(os.path.join(radice, nome))
    trovati.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return trovati


def _scegli_video(base: str) -> str | None:
    """Fa scegliere un video fra quelli scaricati, o accetta un percorso.

    La cartella dei download e' il punto di partenza naturale — chi
    rimasterizza ha quasi sempre appena scaricato — ma incollare un percorso
    qualsiasi resta possibile, perche' il programma funziona su qualunque
    file video, non solo sui propri.
    """
    video = _trova_video(base) if os.path.isdir(base) else []

    if not video:
        console.print(t('choose.none', path=escape(base)))
        risposta = _chiedi(t('choose.ask_path'))
        return os.path.abspath(risposta.strip('"')) if risposta else None

    tab = Table(box=HEAVY_HEAD, border_style='grey37', width=LARGHEZZA,
                header_style='bold bright_blue')
    tab.add_column('#', justify='right', width=3, style='dim')
    tab.add_column(t('choose.col_file'), overflow='ellipsis', no_wrap=True)
    tab.add_column(t('choose.col_res'), justify='right', width=10)
    tab.add_column(t('choose.col_size'), justify='right', width=10)

    mostrati = video[:15]
    for i, path in enumerate(mostrati, 1):
        info = probe(path)
        risoluzione = f"{info['height']}p" if info and info['height'] else '?'
        tab.add_row(str(i), escape(os.path.basename(path)), risoluzione,
                    fmt_peso(os.path.getsize(path)))

    console.print()
    console.print(tab)
    console.print(t('choose.hint'))

    risposta = _chiedi(t('choose.prompt'))
    if not risposta:
        return None
    if risposta.isdigit() and 1 <= int(risposta) <= len(mostrati):
        return mostrati[int(risposta) - 1]
    return os.path.abspath(risposta.strip('"'))


def main() -> None:
    """Punto di ingresso: legge gli argomenti e avvia la procedura.

    Tre modalita' d'uso:
      - nessun argomento     -> interattiva, sceglie fra i video scaricati;
      - --input <file>       -> rimasterizza quel file;
      - --info --input <f>   -> analizza e consiglia, senza scrivere nulla.

    La risoluzione d'arrivo si sceglie al terzo passo, con una tabella che per
    ogni modalita' mostra il risultato su *questo* file e quanto vale davvero:
    da riga di comando la stessa scelta si fissa con --height auto|hd|2k|4k.

    Come negli altri due strumenti la lingua va fissata prima di costruire il
    parser, perche' i testi di --help vengono composti mentre il parser si crea.
    """
    # Da riga di comando si parla solo italiano: nessuna domanda all'avvio,
    # nessuna opzione da ricordare. Il catalogo bilingue resta intatto perche'
    # la GUI continua a offrire la scelta della lingua.

    parser = argparse.ArgumentParser(
        description=t('cli.desc.pix'),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=t('cli.epilog.pix'),
    )
    parser.add_argument('--input', '-i', type=str, default=None,
                        help=t('cli.input.pix'))
    parser.add_argument('--output', '-o', type=str, default=None,
                        help=t('cli.output.pix'))
    parser.add_argument('--base', '-b', type=str,
                        default=_musica(),
                        help=t('cli.base.pix'))
    parser.add_argument('--preset', '-p', type=str, default=None,
                        choices=sorted(PRESETS), help=t('cli.preset'))
    parser.add_argument('--height', type=str, default=None,
                        metavar='auto|none|hd|2k|4k|PIXEL',
                        help=t('cli.height'))
    parser.add_argument('--crf', type=int, default=CRF_DEFAULT,
                        help=t('cli.crf.pix', default=CRF_DEFAULT))
    parser.add_argument('--gpu', action='store_true', help=t('cli.gpu'))
    parser.add_argument('--no-compare', action='store_true',
                        help=t('cli.no_compare'))
    parser.add_argument('--info', action='store_true', help=t('cli.info.pix'))
    parser.add_argument('--yes', '-y', action='store_true', help=t('cli.yes.pix'))

    args = parser.parse_args()

    _print_banner()

    if not check_ffmpeg():
        sys.exit(1)

    # ── Passo 1: sorgente ───────────────────────────────────────────────────
    _passo(1, 5, t('step.source'))
    src = (os.path.abspath(args.input) if args.input
           else _scegli_video(os.path.abspath(args.base)))
    if not src:
        console.print(t('common.goodbye.pix'))
        return
    if not os.path.isfile(src):
        console.print(t('common.file_missing', path=escape(src)))
        sys.exit(1)

    info = probe(src)
    if not info or not e_un_filmato(info):
        console.print(t('probe.error', path=escape(os.path.basename(src))))
        sys.exit(1)

    _pannello_sorgente(info)

    # ── Passo 2: diagnosi ───────────────────────────────────────────────────
    _passo(2, 5, t('step.diagnosis'))
    problemi, consigliato = diagnosi(info)
    _pannello_diagnosi(problemi, consigliato)

    if args.info:
        console.print()
        return

    preset = args.preset or consigliato

    # ── Passo 3: risoluzione d'arrivo ───────────────────────────────────────
    # La scelta si chiede solo quando ha senso chiederla: se --height e' stato
    # passato la decisione e' gia' presa, e con --yes non c'e' nessuno davanti
    # allo schermo. In entrambi i casi vale l'automatico, che si ferma al
    # doppio ed e' l'unico valore difendibile senza aver visto il file.
    _passo(3, 5, t('step.quality'))
    richiesta = risolvi_altezza(args.height)
    if args.height is None and not args.yes:
        richiesta = _scegli_qualita(info, preset)
    altezza = altezza_obiettivo(info, richiesta, preset)

    catena = catena_filtri(preset, info, altezza)
    dst = os.path.abspath(args.output) if args.output else nome_uscita(
        src, altezza or info['height'], None)

    # ── Passo 4: conferma ───────────────────────────────────────────────────
    _passo(4, 5, t('step.plan'))
    _pannello_piano(info, preset, altezza, catena, args.gpu, args.crf, dst)

    if not args.yes:
        # L'invio a vuoto vale "procedi": a questo punto il piano e' gia' sotto
        # gli occhi e chi arriva qui ha gia' deciso. Le altre risposte passano
        # dal riconoscitore condiviso, che accetta si'/no in entrambe le lingue.
        risposta = _chiedi(t('confirm.proceed'))
        if risposta and not i18n.is_yes(risposta):
            console.print(t('common.cancelled.pix'))
            return

    # ── Passo 4: lavorazione ────────────────────────────────────────────────
    _passo(5, 5, t('step.remaster'))
    console.print()
    if not rimasterizza(info, dst, catena, args.gpu, args.crf):
        sys.exit(1)

    png_confronto = None
    if not args.no_compare:
        # Il fotogramma di confronto si prende a un terzo del video: l'inizio
        # e' quasi sempre una sigla o una schermata nera, che non mostrerebbe
        # nessuna differenza.
        istante = max(info['duration'] / 3, 0.0)
        png_confronto = confronto(
            src, dst, os.path.splitext(dst)[0] + ' [confronto].png', istante)

    _pannello_risultato(info, dst, png_confronto)
    console.print()


if __name__ == '__main__':
    main()
