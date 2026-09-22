"""AudioDex al terminale: le tabelle, le domande, gli argomenti.

E' l'interfaccia piu' ricca dei quattro, perche' e' l'unica che deve far
scegliere fra molte cose: venti risultati di ricerca, cinquanta brani di una
playlist, quali di quelli scaricare. Le tabelle e le schede che stanno qui
servono tutte a quella scelta.

Il lavoro vero non e' qui. Tutto quello che questo file fa e' mostrare cosa
ha risposto ``server/sources/youtube.py``, raccogliere cosa e' stato scelto,
e passarlo a ``server/services/audio.py``.
"""
from __future__ import annotations

import argparse
import os
import signal

from rich.align import Align
from rich.box import DOUBLE, ROUNDED
from rich.markup import escape
from rich.panel import Panel
from rich.style import Style
from rich.table import Table
from rich.text import Text

from server.config import i18n
from server.config.paths import cartella_musica as _musica
from server.config.settings import (
    FORMATI_AUDIO, FORMATI_VIDEO, MAX_DOWNLOAD_WORKERS, MAX_SEARCH_RESULTS)
from server.audio.chapters import capitoli_album
from server.audio.verify import spazio_disco_sufficiente
from server.services.audio import _export_failed, download_batch
from server.sources.youtube import (
    e_playlist, entry_da_info, get_playlist_entries, get_video_details,
    search_youtube, _url_ha_video)
from server.audio.tagging import _HAS_MUTAGEN
from server.state import db as scraper_db
from server.state.jobs import INTERROTTO, chiudi_con_garbo
from server.utils.console import SYM_DOT, SYM_FAIL, SYM_OK, console
from server.utils.text import durata_o_ignota, nome_file_pulito, viste_abbreviate
from server.sources.lyrics import _split_artist_title

t = i18n.t

# Il simbolo che AudioDex usa al posto del pallino per le righe dei brani.
SYM_NOTE = '[accent]\u266b[/accent]'


def _print_banner() -> None:
    """Stampa il banner ASCII colorato 'AudioDex' all'avvio del programma.

    Non ha alcuna funzione tecnica: serve a dare al programma un'identità
    riconoscibile e a segnare con chiarezza l'inizio di una sessione quando
    il terminale contiene già l'output di comandi precedenti. Le righe sono
    colorate a sfumatura, una tinta per riga.
    """
    # Stringhe grezze (r'...'): il disegno è fitto di backslash e con le
    # sequenze di escape normali diventerebbe illeggibile da correggere.
    banner_lines = [
        r'    ___             ___       ____           ',
        r'   /   | __  ______/ (_)___  / __ \___  _  __',
        r'  / /| |/ / / / __  / / __ \/ / / / _ \| |/_/',
        r' / ___ / /_/ / /_/ / / /_/ / /_/ /  __/>  <  ',
        r'/_/  |_\__,_/\__,_/_/\____/_____/\___/_/|_|  ',
    ]
    colors = ['bright_magenta', 'magenta', 'bright_blue', 'blue', 'bright_cyan', 'cyan']
    text = Text()
    for i, line in enumerate(banner_lines):
        # A capo solo *tra* le righe: sull'ultima lascerebbe una riga
        # vuota in fondo al pannello.
        suffisso = '\n' if i < len(banner_lines) - 1 else ''
        text.append(line + suffisso, style=Style(color=colors[i % len(colors)], bold=True))
    console.print()
    console.print(Panel(
        Align.center(text),
        border_style='bright_blue',
        box=DOUBLE,
        padding=(1, 2),
        expand=False,
    ))


# Codici lingua più frequenti su YouTube. Gli altri vengono mostrati com'è
# (il codice ISO resta comunque comprensibile). I nomi estesi stanno nel
# catalogo, alle voci 'lang.<codice>': anche loro seguono la lingua scelta,
# così nella scheda di un video in inglese si legge "Italian", non "Italiano".
_LINGUE = frozenset({
    'it', 'en', 'es', 'fr', 'de', 'pt', 'ru', 'ja', 'ko', 'zh',
    'ar', 'nl', 'pl', 'tr', 'hi', 'sv', 'ro', 'el', 'uk', 'cs',
})


def _format_language(code: str | None) -> str | None:
    """Converte un codice lingua ('en', 'it-IT') nel nome esteso.

    La variante regionale viene scartata (`it-IT` → `it`): nella scheda di un
    video interessa la lingua, non il paese, e distinguere `en-US` da `en-GB`
    aggiungerebbe rumore senza aggiungere informazione.

    I codici fuori tabella vengono restituiti tali e quali invece di essere
    nascosti: una sigla ISO resta comunque interpretabile, e la tabella delle
    lingue copre solo le più frequenti su YouTube.
    """
    if not code:
        return None
    base = code.split('-')[0].lower()
    return t(f'lang.{base}') if base in _LINGUE else code


def _format_upload_date(raw: str | None) -> str:
    """Converte la data di pubblicazione da 'AAAAMMGG' a forma leggibile.

    yt-dlp restituisce le date come stringa compatta senza separatori
    (`20171005`), illeggibile a colpo d'occhio. L'ordine dei campi segue la
    lingua scelta (voce 'date.format' del catalogo): giorno/mese/anno in
    italiano, forma ISO in inglese — l'unica non ambigua tra la convenzione
    americana, che mette prima il mese, e quella britannica, che mette prima
    il giorno.

    La conversione è volutamente fatta a mano invece che con ``datetime``: il
    formato è fisso e non serve alcun fuso orario, mentre un parsing vero
    solleverebbe eccezioni su valori malformati che qui si vogliono solo
    ignorare. Il controllo su lunghezza e cifre basta a scartarli.
    """
    if not raw or len(raw) != 8 or not raw.isdigit():
        return '—'
    return t('date.format', d=raw[6:8], m=raw[4:6], y=raw[0:4])


def _display_video_card(info: dict) -> None:
    """Mostra la scheda di un video: canale, numeri, categoria, durata.

    È il riepilogo che si vede dopo aver incollato un URL, prima di
    confermare il download: serve a capire a colpo d'occhio se il video
    è quello giusto. I campi assenti (YouTube non sempre li espone)
    vengono semplicemente omessi invece di mostrare un vuoto.
    """
    table = Table(show_header=False, box=None, padding=(0, 2), expand=False)
    table.add_column('Campo', style='dim_label', no_wrap=True)
    table.add_column('Valore', style='white')

    righe = [
        ('📺', t('card.channel'), info.get('uploader') or info.get('channel')),
        ('👁', t('card.views'), viste_abbreviate(info.get('view_count'))),
        ('👍', t('card.likes'), viste_abbreviate(info.get('like_count'))),
        ('👥', t('card.subscribers'), viste_abbreviate(info.get('channel_follower_count'))),
        ('🏷', t('card.category'), (info.get('categories') or [None])[0]),
        ('🗣', t('card.language'), _format_language(info.get('language'))),
        ('📅', t('card.published'), _format_upload_date(info.get('upload_date'))),
        ('⏱', t('card.duration'), durata_o_ignota(info.get('duration'))),
    ]
    # I segnaposto dei formattatori ('—', '??:??') indicano un dato che
    # YouTube non ha esposto: meglio togliere la riga che mostrare un vuoto.
    for icona, etichetta, valore in righe:
        if valore and str(valore) not in ('—', '??:??'):
            table.add_row(f'{icona}  {etichetta}', str(valore))

    capitoli = info.get('chapters') or []
    if capitoli:
        table.add_row(f"📑  {t('card.chapters')}", t('card.sections', n=len(capitoli)))

    console.print()
    console.print(Panel(
        table,
        title=f"[title]🎬 {info.get('title', t('common.unknown'))[:60]}[/title]",
        border_style='bright_blue',
        box=ROUNDED,
        expand=False,
        padding=(1, 2),
    ))


def _confirm_video(info: dict) -> bool:
    """Mostra la scheda del video e chiede conferma prima di scaricare.

    Esiste perché un URL incollato può facilmente non essere quello giusto —
    un ricaricamento, una cover, un live — e un video pesa da 20 a 100 volte
    l'audio: meglio due secondi di lettura che un download da rifare.

    Viene usata **solo** in modalità interattiva. Con ``--url`` la scheda si
    vede lo stesso ma senza domanda, altrimenti uno script resterebbe appeso
    a un prompt.

    Accetta come conferma sia le forme italiane sia quelle inglesi — se ne
    occupa ``i18n.is_yes`` — a prescindere dalla lingua dell'interfaccia: chi
    usa un terminale digita `y` per riflesso, e chi è italiano digita `s`.
    """
    _display_video_card(info)
    return i18n.is_yes(console.input(t('card.confirm')))


def _display_search_results(results: list[dict], table_title: str | None = None) -> None:
    """Mostra un elenco di tracce in una tabella numerata (per la selezione).

    Usata sia per i risultati di ricerca sia per le tracce di una playlist.

    Il titolo predefinito si risolve qui dentro e non nella firma: un valore
    di default viene calcolato all'import del modulo, quando la lingua non è
    ancora stata scelta, e resterebbe congelato in italiano per sempre.
    """
    table = Table(
        title=table_title or t('table.search_results'),
        box=ROUNDED,
        border_style='bright_blue',
        header_style='bold bright_cyan',
        row_styles=['', 'dim'],
        expand=False,
    )
    # Nelle playlist YouTube non fornisce le views: la colonna compare
    # solo quando almeno una riga ha il dato (es. risultati di ricerca).
    show_views = any(r.get('views') for r in results)

    table.add_column('#', style='bold yellow', justify='right', width=4)
    table.add_column(t('table.title'), style='white', max_width=45, no_wrap=True)
    table.add_column(t('table.artist'), style='bright_magenta', max_width=25, no_wrap=True)
    table.add_column(t('table.duration'), style='cyan', justify='right', width=8)
    if show_views:
        table.add_column(t('table.views'), style='green', justify='right', width=9)

    for i, r in enumerate(results, 1):
        artist, track = _split_artist_title(r['title'], r.get('uploader'))
        row = [
            str(i),
            track[:45],
            (artist or '??')[:25],
            durata_o_ignota(r.get('duration')),
        ]
        if show_views:
            row.append(viste_abbreviate(r.get('views')))
        table.add_row(*row)

    console.print()
    console.print(table)


# Stati di visibilità che YouTube dichiara per una playlist. Il testo mostrato
# sta nel catalogo: qui resta solo la corrispondenza con il valore grezzo.
_VISIBILITA = {
    'public': 'visibility.public',
    'unlisted': 'visibility.unlisted',
    'private': 'visibility.private',
}


def _display_playlist_info(title: str, entries: list[dict], meta: dict | None = None) -> None:
    """Mostra la scheda della playlist: canale, tracce, durata, visualizzazioni.

    I dati d'insieme arrivano da get_playlist_entries, che li ricava dalla
    stessa chiamata usata per l'elenco: nessuna richiesta aggiuntiva. I
    campi che YouTube non espone vengono omessi.
    """
    meta = meta or {}
    total_duration = sum(e.get('duration', 0) or 0 for e in entries)

    table = Table(show_header=False, box=None, padding=(0, 2), expand=False)
    table.add_column('Campo', style='dim_label', no_wrap=True)
    table.add_column('Valore', style='white')

    visibilita = _VISIBILITA.get(meta.get('availability') or '')
    righe = [
        ('📺', t('playlist.channel'), meta.get('channel')),
        ('🎵', t('playlist.tracks'), str(len(entries))),
        ('⏱', t('playlist.total_duration'), durata_o_ignota(total_duration)),
        ('👁', t('playlist.views'), viste_abbreviate(meta.get('views'))),
        ('📅', t('playlist.updated'), _format_upload_date(meta.get('modified'))),
        ('🔓', t('playlist.visibility'), t(visibilita) if visibilita else None),
    ]
    for icona, etichetta, valore in righe:
        if valore and str(valore) not in ('—', '??:??'):
            table.add_row(f'{icona}  {etichetta}', str(valore))

    # Se YouTube dichiara più video di quelli estratti, la differenza sono
    # voci private o rimosse: meglio dirlo che lasciar contare all'utente.
    dichiarati = meta.get('count')
    if dichiarati and dichiarati > len(entries):
        table.add_row(
            f"⚠  {t('playlist.unavailable')}",
            t('playlist.unavailable_n', n=dichiarati - len(entries)),
        )

    console.print()
    console.print(Panel(
        table,
        title=f'[title]💿 {title[:60]}[/title]',
        border_style='bright_blue',
        box=ROUNDED,
        expand=False,
        padding=(1, 2),
    ))


def _display_download_summary(results: list[dict]) -> None:
    """Mostra il riepilogo finale: quante tracce scaricate, già presenti, fallite.

    Dopo una playlist lunga le barre di avanzamento sono scorse via e il
    terminale non dice più com'è andata: questo pannello è il verdetto, e
    l'unico punto in cui compaiono i titoli delle tracce fallite.

    I tre esiti restano distinti perché richiedono azioni diverse: `skip`
    significa che il file c'era già ed è tutto a posto, `fail` che va
    ritentato. Le righe che valgono zero non vengono stampate, per non
    suggerire un problema dove non c'è.

    Il colore del bordo e l'icona seguono la presenza di fallimenti, così
    l'esito si legge senza mettersi a contare i numeri.
    """
    ok = sum(1 for r in results if r['status'] == 'ok')
    fail = sum(1 for r in results if r['status'] == 'fail')
    skip = sum(1 for r in results if r['status'] == 'skip')

    summary_table = Table(show_header=False, box=None, padding=(0, 2), expand=False)
    summary_table.add_column('Label', style='dim_label')
    summary_table.add_column('Value')

    summary_table.add_row(t('summary.total'), f'[bold]{len(results)}[/bold]')
    summary_table.add_row(f"{SYM_OK} {t('summary.downloaded')}", f'[success]{ok}[/success]')
    tracce_divise = sum(r.get('tracce', 0) for r in results)
    if tracce_divise:
        summary_table.add_row(f"{SYM_NOTE} {t('summary.split')}",
                              f'[info]{tracce_divise}[/info]')

    lyrics_found = sum(1 for r in results if r.get('lyrics'))
    if lyrics_found > 0:
        summary_table.add_row(f"{SYM_NOTE} {t('summary.lyrics')}", f'[info]{lyrics_found}[/info]')
    if skip > 0:
        summary_table.add_row(f"{SYM_DOT} {t('summary.already')}", f'[info]{skip}[/info]')
    if fail > 0:
        summary_table.add_row(f"{SYM_FAIL} {t('summary.failed')}", f'[error]{fail}[/error]')
        failed_titles = [r['title'] for r in results if r['status'] == 'fail']
        summary_table.add_row(
            t('summary.failed_tracks'),
            f"[error]{', '.join(x[:30] for x in failed_titles)}[/error]",
        )

    border = 'red' if fail else 'bright_green'
    title_icon = '❌' if fail else '✅'

    console.print()
    console.print(Panel(
        summary_table,
        title=f"{title_icon} {t('summary.title')}",
        border_style=border,
        box=DOUBLE,
        expand=False,
        padding=(1, 3),
    ))


def _select_from_results(results: list[dict]) -> list[dict]:
    """Chiede all'utente quali tracce scaricare tra quelle elencate.

    Accetta un numero singolo (3), un intervallo (1-5), un elenco (1,3,7),
    'all'/'tutti' per tutte oppure 'q' per annullare. Ripete la domanda
    finché l'input non è valido. Restituisce le entry scelte, senza
    duplicati e nell'ordine di selezione.
    """
    console.print(t('select.hint.audio'))

    while True:
        choice = console.input(t('select.prompt')).strip().lower()
        if i18n.is_quit(choice):
            return []
        if i18n.is_all(choice):
            return results

        selected = []
        try:
            parts = choice.replace(' ', ',').split(',')
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                if '-' in part:
                    start, end = part.split('-', 1)
                    for n in range(int(start), int(end) + 1):
                        if 1 <= n <= len(results):
                            selected.append(results[n - 1])
                else:
                    n = int(part)
                    if 1 <= n <= len(results):
                        selected.append(results[n - 1])

            if selected:
                # Rimuovi duplicati mantenendo l'ordine
                seen = set()
                unique = []
                for s in selected:
                    if s['id'] not in seen:
                        seen.add(s['id'])
                        unique.append(s)
                return unique
        except ValueError:
            pass

        console.print(t('common.invalid_selection'))


def _ask_media_type() -> tuple[str, str] | None:
    """Chiede se scaricare il video intero o il solo audio.

    Restituisce (media, formato) con media in {'audio', 'video'}, oppure
    None se l'utente annulla. Il formato proposto è quello nativo di
    YouTube per il tipo scelto (m4a / mp4): in entrambi i casi non serve
    ricodificare, quindi non si perde qualità.
    """
    table = Table(show_header=False, box=ROUNDED, border_style='bright_blue',
                  padding=(0, 2), expand=False)
    table.add_column('N', style='bold yellow', justify='right', width=3)
    table.add_column(t('media.column_choice'))
    table.add_row('1', f"{SYM_NOTE} [bold]{t('media.audio_only')}[/bold] [dim](m4a)[/dim]\n"
                       f"{t('media.audio_note')}")
    table.add_row('2', f"🎬 [bold]{t('media.full_video')}[/bold] [dim](mp4)[/dim]\n"
                       f"{t('media.video_note')}")

    console.print()
    console.print(table)

    while True:
        choice = console.input(t('media.prompt')).strip().lower()
        if i18n.is_quit(choice):
            return None
        if choice in ('1', 'a', 'audio', ''):
            return 'audio', 'm4a'
        if choice in ('2', 'v', 'video'):
            return 'video', 'mp4'
        console.print(t('common.invalid_choice.audio'))


def _chiedi_divisione(info: dict) -> bool:
    """Se il video sembra un disco, chiede se dividerlo. Altrimenti tace.

    La domanda si pone solo quando i capitoli superano i criteri: proporla
    su un video qualunque sarebbe una domanda in piu' a ogni download, e le
    domande inutili si imparano a ignorare — anche quelle che contano.
    """
    capitoli = capitoli_album(info)
    if not capitoli:
        return False

    durata = sum(c['fine'] - c['inizio'] for c in capitoli) / len(capitoli)
    console.print()
    console.print(t('split.detected', n=len(capitoli),
                    media=durata_o_ignota(durata)))
    # Le prime tre bastano a far riconoscere il disco senza riempire lo
    # schermo con la scaletta di un album da venti tracce.
    for cap in capitoli[:3]:
        console.print(t('split.sample', n=cap['n'],
                        titolo=escape(cap['titolo']),
                        durata=durata_o_ignota(cap['fine'] - cap['inizio'])))
    if len(capitoli) > 3:
        console.print(t('split.more', n=len(capitoli) - 3))

    return i18n.is_yes(console.input(t('split.ask')))


def main() -> None:
    """Punto di ingresso: legge gli argomenti da riga di comando e avvia il flusso.

    Tre modalità d'uso:
      - nessun argomento  -> modalità interattiva (loop: cerca o incolla URL);
      - --search "testo"  -> ricerca una tantum con selezione dei risultati;
      - --url <link>      -> download diretto di un video o di una playlist.
    Le playlist vengono scaricate in una sottocartella col nome dell'album.
    Opzioni trasversali: --format (m4a/mp3/opus), --workers (parallelismo),
    --no-lyrics (salta i testi karaoke), --cookies-from-browser (accesso
    a playlist e video privati con i cookie del browser).

    La lingua va fissata *prima* di costruire il parser, perché i testi di
    --help vengono composti mentre il parser si crea.
    """
    # Da riga di comando si parla solo italiano: nessuna domanda all'avvio,
    # nessuna opzione da ricordare. Il catalogo bilingue resta intatto perché
    # la GUI, dove cambiare lingua è un clic e non un argomento da digitare,
    # continua a offrire la scelta.

    parser = argparse.ArgumentParser(
        description=t('cli.desc.audio'),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--search', '-s', type=str, help=t('cli.search'))
    group.add_argument('--url', '-u', type=str, help=t('cli.url'))

    parser.add_argument('--output', '-o', type=str,
                        default=_musica(),
                        help=t('cli.output.audio'))
    parser.add_argument('--media', '-m', type=str, default=None,
                        choices=['audio', 'video'],
                        help=t('cli.media'))
    parser.add_argument('--format', '-f', type=str, default=None,
                        choices=['m4a', 'mp3', 'opus', 'mp4', 'mkv'],
                        help=t('cli.format'))
    parser.add_argument('--workers', '-w', type=int, default=MAX_DOWNLOAD_WORKERS,
                        help=t('cli.workers', n=MAX_DOWNLOAD_WORKERS))
    parser.add_argument('--max-results', type=int, default=MAX_SEARCH_RESULTS,
                        help=t('cli.max_results', n=MAX_SEARCH_RESULTS))
    parser.add_argument('--no-lyrics', action='store_true',
                        help=t('cli.no_lyrics'))
    parser.add_argument('--split', action='store_true', help=t('cli.split'))
    parser.add_argument('--no-split', action='store_true', help=t('cli.no_split'))
    parser.add_argument('--cookies-from-browser', type=str, default=None,
                        choices=['firefox', 'chrome', 'edge', 'brave', 'opera', 'vivaldi'],
                        help=t('cli.cookies'))

    args = parser.parse_args()
    fetch_lyrics = not args.no_lyrics
    # Fuori dalla modalita' interattiva non c'e' nessuno a rispondere:
    # senza --split non si divide, per non riorganizzare cartelle a
    # sorpresa dentro uno script.
    dividi = args.split and not args.no_split

    # Tipo di media e formato: coerenti tra loro. Un --format video implica
    # --media video (e viceversa), così non serve ricordarsi entrambi.
    media = args.media
    fmt = args.format
    if fmt in FORMATI_VIDEO:
        if media == 'audio':
            parser.error(t('cli.err_video_format', fmt=fmt))
        media = 'video'
    elif fmt in FORMATI_AUDIO:
        if media == 'video':
            parser.error(t('cli.err_audio_format', fmt=fmt))
        media = 'audio'
    if media and not fmt:
        fmt = 'mp4' if media == 'video' else 'm4a'

    global _cookies_browser
    _cookies_browser = args.cookies_from_browser

    signal.signal(signal.SIGINT, chiudi_con_garbo)

    scraper_db.init_db()

    _print_banner()

    if not _HAS_MUTAGEN:
        console.print(t('start.no_mutagen'))
        console.print(t('start.install_mutagen'))

    output_dir = os.path.abspath(args.output)

    if not spazio_disco_sufficiente(output_dir):
        console.print(t('common.cancelled_op'))
        return

    if not args.search and not args.url:
        # Modalita' interattiva
        console.print(t('interactive.header', dot=SYM_DOT))

        def resolve_media() -> tuple[str, str] | None:
            """Tipo di media da scaricare: da riga di comando o chiesto ora."""
            if media:
                return media, fmt
            return _ask_media_type()

        while not INTERROTTO.is_set():
            try:
                query = console.input(t('interactive.prompt', note=SYM_NOTE)).strip()
            except (EOFError, KeyboardInterrupt):
                break

            if not query or i18n.is_quit(query):
                break

            if query.startswith(('http://', 'https://', 'www.')):
                come_playlist = e_playlist(query)
                if come_playlist:
                    title, entries, meta = get_playlist_entries(query)
                    if not entries:
                        # Playlist inaccessibile (privata, rimossa, o di un tipo
                        # che YouTube non espone): se l'URL porta comunque con sé
                        # un video, si scarica quello invece di arrendersi.
                        if _url_ha_video(query):
                            console.print(t('error.playlist_unreachable'))
                            come_playlist = False
                        else:
                            console.print(t('error.no_tracks_playlist'))
                            continue

                if come_playlist:
                    _display_playlist_info(title, entries, meta)
                    _display_search_results(entries, table_title=t('table.playlist_tracks'))
                    console.print(t('interactive.download_all', n=len(entries)))
                    answer = console.input(t('interactive.answer_prompt')).strip()
                    if not i18n.is_yes(answer):
                        selected = _select_from_results(entries)
                        if not selected:
                            continue
                        entries = selected
                    choice = resolve_media()
                    if not choice:
                        continue
                    mtype, mfmt = choice
                    album_name = nome_file_pulito(title)
                    sub_dir = os.path.join(output_dir, album_name)
                    results = download_batch(entries, sub_dir, mfmt, album=title, max_workers=args.workers, fetch_lyrics=fetch_lyrics, numbered=True, media=mtype, dividi=dividi)
                else:
                    console.print(t('interactive.fetching_video'))
                    info = get_video_details(query)
                    if not info:
                        console.print(t('error.no_info_url'))
                        continue
                    if not _confirm_video(info):
                        console.print(t('common.cancelled.audio'))
                        continue
                    entries = [entry_da_info(info, query)]
                    choice = resolve_media()
                    if not choice:
                        continue
                    mtype, mfmt = choice
                    dividi_ora = dividi
                    if not args.split and not args.no_split:
                        dividi_ora = _chiedi_divisione(info)
                    results = download_batch(entries, output_dir, mfmt, max_workers=args.workers, fetch_lyrics=fetch_lyrics, media=mtype, dividi=dividi_ora)

                _display_download_summary(results)
                _export_failed(output_dir, results, entries)
            else:
                results = search_youtube(query, args.max_results)
                if not results:
                    console.print(t('error.no_results'))
                    continue
                _display_search_results(results)
                selected = _select_from_results(results)
                if not selected:
                    continue
                choice = resolve_media()
                if not choice:
                    continue
                mtype, mfmt = choice
                dl_results = download_batch(selected, output_dir, mfmt, max_workers=args.workers, fetch_lyrics=fetch_lyrics, media=mtype, dividi=dividi)
                _display_download_summary(dl_results)
                _export_failed(output_dir, dl_results, selected)

        console.print(t('common.goodbye.audio'))
        return

    # Fuori dalla modalità interattiva non si fanno domande: senza --media
    # esplicito si scarica l'audio, com'è sempre stato.
    media = media or 'audio'
    fmt = fmt or 'm4a'

    if args.search:
        results = search_youtube(args.search, args.max_results)
        if not results:
            console.print(t('error.no_results'))
            return
        _display_search_results(results)
        selected = _select_from_results(results)
        if not selected:
            return
        dl_results = download_batch(selected, output_dir, fmt, max_workers=args.workers, fetch_lyrics=fetch_lyrics, media=media, dividi=dividi)
        _display_download_summary(dl_results)
        _export_failed(output_dir, dl_results, selected)
        return

    if args.url:
        come_playlist = e_playlist(args.url)
        if come_playlist:
            title, entries, meta = get_playlist_entries(args.url)
            if not entries:
                # Stesso ripiego della modalità interattiva: un URL che
                # contiene un video resta scaricabile anche se la playlist
                # a cui appartiene non è consultabile.
                if _url_ha_video(args.url):
                    console.print(t('error.playlist_unreachable'))
                    come_playlist = False
                else:
                    console.print(t('error.no_tracks'))
                    return

        if come_playlist:
            _display_playlist_info(title, entries, meta)
            _display_search_results(entries, table_title=t('table.playlist_tracks'))
            album_name = nome_file_pulito(title)
            sub_dir = os.path.join(output_dir, album_name)
            results = download_batch(entries, sub_dir, fmt, album=title, max_workers=args.workers, fetch_lyrics=fetch_lyrics, numbered=True, media=media, dividi=dividi)
        else:
            info = get_video_details(args.url)
            if not info:
                console.print(t('error.no_info'))
                return
            # Scheda mostrata anche qui, ma senza chiedere conferma: con
            # --url si è già dichiarato cosa si vuole scaricare.
            _display_video_card(info)
            entries = [entry_da_info(info, args.url)]
            results = download_batch(entries, output_dir, fmt, max_workers=args.workers, fetch_lyrics=fetch_lyrics, media=media, dividi=dividi)

        _display_download_summary(results)
        _export_failed(output_dir, results, entries)
        return


if __name__ == '__main__':
    main()
