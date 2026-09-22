"""Scaricare una playlist intera: l'orchestra.

Da solo questo modulo non sa scaricare niente - lo fa ``audio/download.py``.
Sa pero' le cose che contano quando i brani sono cinquanta invece di uno:
quanti scaricarne insieme senza farsi rifiutare da YouTube, come tenere il
conto di un avanzamento che procede su tre fronti contemporaneamente, cosa
fare di quelli che cadono, e come fermarsi con garbo quando arriva un Ctrl+C
a meta'.

L'ultima non e' un dettaglio: interrompere venti download in parallelo senza
lasciare venti file mezzi scritti e' il motivo per cui esiste ``INTERROTTO``.
"""
from __future__ import annotations

import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from rich.console import Group
from rich.live import Live
from rich.progress import (
    Progress, SpinnerColumn, BarColumn, DownloadColumn, MofNCompleteColumn,
    TextColumn, TaskProgressColumn, TimeElapsedColumn, TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.text import Text

from server.config import i18n
from server.config.settings import MAX_DOWNLOAD_WORKERS
from server.audio.download import download_single
from server.state.jobs import INTERROTTO
from server.utils.console import console, setup_logger

# Ci si passa anche cio' che le interfacce chiedono a YouTube. Non e' pigrizia
# da import: e' il punto. Questo modulo E' quello che la finestra e il
# terminale conoscono di AudioDex, e avere un elenco solo da guardare vale piu'
# di cinque import sparsi in due file. Prima la finestra entrava dentro il
# motore a prendersi 'ad._entry_from_info' e 'ad._is_playlist_url': due nomi
# che l'underscore dichiarava privati e che erano invece il contratto vero.
from server.sources.youtube import (      # noqa: F401
    e_playlist,
    entry_da_info,
    get_playlist_entries,
    get_video_details,
    search_youtube,
)

t = i18n.t

log = setup_logger('audiodex', 'audiodex.log')


class _PhaseTracker:
    """Tiene le barre di avanzamento delle quattro fasi di ogni traccia.

    Scaricare un brano non è un solo passaggio: dopo il trasferimento dei
    byte c'è la conversione FFmpeg, la ricerca del testo su LRCLIB e il
    tagging con la copertina. Con una sola barra il file sembrava fermo al
    100% mentre in realtà stava ancora lavorando; qui ogni fase ha la sua
    barra, che conta quante tracce l'hanno superata.

    I metodi sono chiamati dai thread di download, quindi lo stato è
    protetto da un lock. Ogni fase viene contata **una volta sola** per
    traccia: un retry che rifà il download non la conteggia due volte.
    """

    # Solo i nomi interni: le etichette mostrate stanno nel catalogo, alle
    # voci 'phase.<nome>', e vengono lette a ogni download perché la lingua
    # si conosce solo dopo l'avvio, non all'import di questo modulo.
    PHASES = ('download', 'convert', 'lyrics', 'tag')

    def __init__(self, progress: Progress, total: int, skip: frozenset[str] = frozenset()):
        """Crea una barra per ogni fase pertinente al download in corso.

        Parametri
        ---------
        progress : Progress
            La barra Rich condivisa su cui registrare le quattro attività.
        total : int
            Numero di tracce da elaborare: è il fondo scala di ogni barra.
        skip : frozenset[str]
            Fasi da non mostrare affatto. Serve ai download video, dove i
            testi karaoke non vengono cercati: una barra ferma a zero per
            tutta la sessione sembrerebbe un blocco invece di una scelta.

        Le etichette sono riempite di spazi a lunghezza uguale perché le
        barre partano tutte dalla stessa colonna: disallineate darebbero
        l'impressione di un errore di stampa. Il riempimento è calcolato sulla
        parola più lunga e non scritto a mano, perché cambia con la lingua.
        """
        self._progress = progress
        self._lock = threading.Lock()
        # Fasi già superate da ciascuna traccia, per non contarle due volte
        # quando un retry ripercorre passaggi già fatti.
        self._seen: dict[int, set[str]] = {}
        etichette = {name: t(f'phase.{name}') for name in self.PHASES}
        larghezza = max(len(e) for e in etichette.values())
        self._tasks = {
            name: progress.add_task(etichette[name].ljust(larghezza), total=total)
            for name in self.PHASES if name not in skip
        }

    def done(self, key: int, phase: str) -> None:
        """Segna che la traccia `key` ha superato la fase indicata.

        Le fasi senza barra (perché non pertinenti al tipo di download)
        vengono ignorate: chi le segnala non deve sapere quali sono attive.
        """
        with self._lock:
            if phase not in self._tasks:
                return
            reached = self._seen.setdefault(key, set())
            if phase in reached:
                return
            reached.add(phase)
            self._progress.advance(self._tasks[phase])

    def finish(self, key: int) -> None:
        """Chiude tutte le fasi rimaste aperte per una traccia.

        Serve a fine lavorazione: una traccia saltata non attraversa alcuna
        fase, e una fallita si ferma a metà. Senza questo, le barre non
        arriverebbero mai in fondo pur essendo il lavoro concluso.
        """
        for name in self.PHASES:
            self.done(key, name)


def download_batch(entries: list[dict], output_dir: str, audio_format: str = 'm4a',
                   album: str | None = None, max_workers: int = MAX_DOWNLOAD_WORKERS,
                   fetch_lyrics: bool = True, numbered: bool = False,
                   media: str = 'audio', dividi: bool = False) -> list[dict]:
    """Scarica più tracce in parallelo mostrando le barre di avanzamento.

    Usa un pool di thread (max_workers download simultanei) e due barre
    Rich aggiornate live: una complessiva sulle tracce e una per ciascun
    file in corso. Un Ctrl+C ferma l'accodamento di nuove tracce lasciando
    finire quelle già partite. I risultati vengono riordinati secondo
    l'ordine originale delle entry (i thread terminano in ordine sparso).

    Con numbered=True i file vengono salvati con il numero di traccia in
    testa al nome ('01 - Titolo.m4a'): i download finiscono in ordine
    sparso, ma sul disco le tracce restano nell'ordine della playlist.
    Il numero è quello della playlist di origine (campo 'index' della
    entry), non la posizione nella lista passata: scaricando solo le
    tracce 5-8 i file restano '05'-'08'.
    """
    os.makedirs(output_dir, exist_ok=True)
    total = len(entries)
    results_by_index: dict[int, dict] = {}

    # Larghezza dello zero-padding: la dimensione della playlist di origine
    # se nota, altrimenti il numero di traccia più alto da scaricare.
    highest = max(
        (max(e.get('index') or 0, e.get('playlist_size') or 0) for e in entries),
        default=total,
    ) or total

    kind = 'video' if media == 'video' else 'audio'
    console.print()
    console.rule(f'[phase]⬇ Download {kind}[/phase]', style='bright_green')
    console.print(
        f"  [dim_label]{t('download.threads')}[/dim_label] [info]{max_workers}[/info]  "
        f"[dim_label]{t('download.tracks')}[/dim_label] [bold]{total}[/bold]  "
        f"[dim_label]{t('download.format')}[/dim_label] [info]{audio_format}[/info]\n"
    )

    overall_progress = Progress(
        SpinnerColumn('dots', style='bright_green'),
        TextColumn('[bold bright_green]{task.description}'),
        BarColumn(bar_width=50, style='bar.back', complete_style='bright_green', finished_style='bold green'),
        TaskProgressColumn(),
        MofNCompleteColumn(),
        TextColumn('[dim]│[/dim]'),
        TimeElapsedColumn(),
        TextColumn('[dim]→[/dim]'),
        TimeRemainingColumn(),
        console=console,
        expand=False,
    )

    # Una barra per fase: scaricare un brano non è un passaggio solo, e
    # senza queste il file sembrava fermo al 100% mentre convertiva,
    # cercava il testo o scriveva i tag.
    phase_progress = Progress(
        SpinnerColumn('dots', style='bright_blue'),
        TextColumn('[bright_blue]{task.description}'),
        BarColumn(bar_width=32, style='bar.back', complete_style='bright_blue', finished_style='bold blue'),
        MofNCompleteColumn(),
        console=console,
        expand=False,
    )

    file_progress = Progress(
        SpinnerColumn('dots', style='cyan'),
        TextColumn('{task.description}', markup=True),
        BarColumn(bar_width=30, style='bar.back', complete_style='cyan', finished_style='bold cyan'),
        TaskProgressColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TextColumn('[dim]→[/dim]'),
        TimeRemainingColumn(),
        console=console,
        expand=False,
    )

    overall_task = overall_progress.add_task(t('download.bar_tracks'), total=total)
    # Nel Matroska il testo non è scrivibile, quindi non viene nemmeno
    # cercato: senza lavoro da fare, quella barra non ha senso.
    phases = _PhaseTracker(
        phase_progress, total,
        skip=frozenset({'lyrics'}) if audio_format == 'mkv' else frozenset(),
    )

    layout = Group(
        overall_progress,
        phase_progress,
        Text('  ' + '─' * 46, style='dim'),
        file_progress,
    )

    with Live(layout, console=console, refresh_per_second=10):
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            task_ids = {}

            for i, entry in enumerate(entries):
                if INTERROTTO.is_set():
                    break
                track_num = entry.get('index') or (i + 1)
                tid = file_progress.add_task(
                    f"[bold]#{track_num}[/bold] {entry['title'][:40]}",
                    total=None,
                    visible=True,
                )
                task_ids[i] = tid
                future = executor.submit(
                    download_single, entry, output_dir, audio_format,
                    track_num=track_num, album=album,
                    progress=file_progress, task_id=tid,
                    fetch_lyrics=fetch_lyrics,
                    total_tracks=highest, numbered=numbered,
                    on_phase=lambda name, k=i: phases.done(k, name),
                    media=media, dividi=dividi,
                )
                futures[future] = i

            for future in as_completed(futures):
                idx = futures[future]
                try:
                    result = future.result()
                except Exception as e:
                    result = {
                        'title': entries[idx]['title'],
                        'status': 'fail',
                        'error': str(e)[:100],
                        'file': '',
                    }
                    log.error('Eccezione download: %s', e)

                results_by_index[idx] = result
                overall_progress.advance(overall_task)
                # Traccia conclusa: chiude le fasi non attraversate (una
                # saltata non ne fa nessuna, una fallita si ferma a metà),
                # così le barre arrivano in fondo insieme al lavoro.
                phases.finish(idx)

                tid = task_ids.get(idx)
                if tid is not None:
                    file_progress.remove_task(tid)

                if INTERROTTO.is_set():
                    for f in futures:
                        f.cancel()
                    break

    # Ricostruisce l'ordine originale dalla posizione della entry, non dal
    # titolo: titoli duplicati o rinominati non spostano più le tracce.
    return [results_by_index[i] for i in sorted(results_by_index)]


def _export_failed(output_dir: str, results: list[dict], entries: list[dict]) -> None:
    """Salva titoli e URL delle tracce fallite in failed_tracks.txt.

    Così l'utente può ritentarle in un secondo momento con --url senza
    dover rifare la ricerca o ricaricare l'intera playlist.
    """
    failed = [r for r in results if r['status'] == 'fail']
    if not failed:
        return

    filepath = os.path.join(output_dir, 'failed_tracks.txt')
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(t('failed.file_header'))
            for r in failed:
                matching = [e for e in entries if e['title'] == r['title']]
                url = matching[0]['url'] if matching else '??'
                f.write(f"{r['title']} | {url}\n")
        console.print(t('failed.saved', path=filepath))
    except OSError as e:
        log.error('Impossibile salvare tracce fallite: %s', e)
