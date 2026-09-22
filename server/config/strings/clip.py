"""Le frasi di ClipDex: taglia, unisci, GIF, provini, compatibilita'.

Stessa forma degli altri cataloghi, ``'chiave': 'frase'``, con i segnaposto di
``str.format``.

Il tema ricorrente qui e' la distinzione fra copia e ricodifica: e' la scelta
che governa tempi, qualita' e vincoli di ogni operazione, e va detta a chi usa
il programma ogni volta che il programma la compie al posto suo.
"""
from __future__ import annotations

TESTI: dict[str, str] = {

    # ── Banner e struttura ───────────────────────────────────────────────────
    'banner.subtitle.clip': 'Montaggio e conversione',
    'banner.tagline.clip': 'taglia, unisci, GIF, provini',
    'step.label': ' Passo {n}/{tot} ',
    'step.inputs': 'File di partenza',
    'step.working': 'Lavorazione',

    # ── Menu delle operazioni ────────────────────────────────────────────────
    'menu.col_action': 'Operazione',
    'menu.col_desc': 'Cosa fa',
    'menu.taglia': 'Estrae uno spezzone. In copia e\' istantaneo',
    'menu.unisci': 'Mette in fila piu\' file, con un capitolo per ciascuno',
    'menu.gif': 'Ricava una GIF con la palette calcolata sul filmato',
    'menu.webp': 'Come la GIF ma in WebP: pesa quasi nove volte meno',
    'menu.provino': 'Una griglia di fotogrammi per capire cosa c\'e\' dentro',
    'menu.compat': 'H.264 leggibile da autoradio e TV datate',
    'menu.prompt': '\n[accent]Quale operazione[/accent] [dim](numero o nome, invio per uscire)[/dim]: ',

    # ── Scelta del file ──────────────────────────────────────────────────────
    'choose.none': '[warning]Nessun video in[/warning] {path}',
    'choose.ask_path': '\n[accent]Percorso del video[/accent] [dim](invio per uscire)[/dim]: ',
    'choose.col_file': 'File',
    'choose.col_dur': 'Durata',
    'choose.col_size': 'Peso',
    'choose.prompt': '\n[accent]Quale video[/accent] [dim](numero o percorso, invio per uscire)[/dim]: ',

    # ── Taglio ───────────────────────────────────────────────────────────────
    'cut.ask_from': '[accent]Da che punto[/accent] [dim](es. 1:20)[/dim]: ',
    'cut.ask_to': '[accent]Fino a[/accent] [dim](invio = fino alla fine)[/dim]: ',
    'cut.note_copy': 'tagliato in copia: nessuna perdita, ma l\'inizio si aggancia al '
                     'fotogramma chiave piu\' vicino',
    'cut.note_drift': 'chiesti {chiesta} s, ottenuti {reale}: {scarto} s in piu\'. In copia '
                      'l\'inizio si aggancia al fotogramma chiave precedente, e in questo '
                      'file sono distanziati. Con --preciso il taglio cade dove hai detto, '
                      'al prezzo di una ricodifica',
    'cut.note_precise': 'tagliato al fotogramma esatto, quindi ricodificato',

    # ── Unione ───────────────────────────────────────────────────────────────
    'merge.item': '  [dim]{n:>2}.[/dim] {file}  [dim]{durata}[/dim]',
    'merge.mode_copy': '\n[bright_green]I file sono omogenei:[/bright_green] li unisco in '
                       'copia, senza ricodificare.',
    'merge.mode_encode': '\n[warning]I file hanno formati diversi:[/warning] li porto tutti '
                         'alla misura del primo e ricodifico. Ci vorra\' di piu\'.',
    'merge.need_inputs': '[error]Serve indicare i file da unire[/error] [dim](--input a.mp4 '
                         'b.mp4, oppure --dir cartella)[/dim]',
    'merge.need_two': '[error]Per unire servono almeno due file.[/error]',
    'merge.note_chapters': 'un capitolo per ciascuno dei {n} file: il risultato resta navigabile',

    # ── GIF, WebP, provino, compatibilita' ───────────────────────────────────
    'gif.note': 'da {inizio}, {durata} s, {fps} fotogrammi al secondo, largo {w} px',
    'sheet.note': '{n} fotogrammi, uno ogni {ogni} circa, distribuiti su tutta la durata',
    'compat.note': 'H.264 baseline, colore yuv420p, indice in testa al file: le tre '
                   'cose che gli apparecchi datati pretendono',

    # ── Lavorazione ──────────────────────────────────────────────────────────
    'run.cutting': 'Taglio',
    'run.merging': 'Unione',
    'run.gif': 'Creo la GIF',
    'run.webp': 'Creo il WebP',
    'run.sheet': 'Compongo il provino',
    'run.compat': 'Riconverto',
    'run.failed': '\n[error]FFmpeg si e\' fermato.[/error]\n[dim]{reason}[/dim]',
    'run.interrupted': '\n[warning]Interrotto.[/warning] [dim]Il file parziale resta sul disco.[/dim]',

    # ── Risultato ────────────────────────────────────────────────────────────
    'result.title': ' Fatto ',
    'result.file': 'File',
    'result.size': 'Peso',
    'result.video': 'Video',

    # ── Errori ───────────────────────────────────────────────────────────────
    'error.unreadable': '[error]Nessun flusso video leggibile in[/error] {path}',
    'error.missing': '[error]Il file non esiste:[/error] {path}',
    'error.empty_range': '[error]L\'intervallo e\' vuoto:[/error] [dim]la fine deve venire '
                         'dopo l\'inizio.[/dim]',
    'error.bad_time': '[error]Tempo non riconosciuto.[/error] [dim]Usa 90, 1:30 oppure '
                      '01:02:03.5[/dim]',
    'error.bad_grid': '[error]Griglia non valida:[/error] {valore} [dim](usa la forma 4x4)[/dim]',
    'common.goodbye.clip': '[dim]Niente da fare, alla prossima.[/dim]\n',

    # ── Strumenti esterni ────────────────────────────────────────────────────
    'tools.no_ffmpeg': '[error]Manca all\'appello:[/error] {tools}',
    'tools.install_ffmpeg': '[dim]FFmpeg non e\' installabile con pip. Su Windows:[/dim]\n'
                            '  [accent]winget install Gyan.FFmpeg[/accent]\n'
                            '[dim]poi riapri il terminale, cosi\' il PATH viene riletto.[/dim]',

    # ── Riga di comando ──────────────────────────────────────────────────────
    'cli.desc.clip': 'ClipDex — taglia, unisce e converte i video: spezzoni, montaggi, '
                     'GIF, provini e ricodifiche per apparecchi datati.',
    'cli.epilog.clip': 'Senza sottocomando parte la procedura guidata.\n'
                       'Esempi:\n'
                       '  python -m cli clip taglia -i v.mp4 --da 1:20 --a 3:45\n'
                       '  python -m cli clip unisci -d "risultati/musica/Album"\n'
                       '  python -m cli clip gif -i v.mp4 --da 0:30 --durata 4\n'
                       '  python -m cli clip provino -i v.mp4 --griglia 5x3\n'
                       '  python -m cli clip compat -i v.mp4',
    'cli.base.clip': 'Cartella in cui cercare i video (default: risultati/musica)',
    'cli.crf.clip': 'Qualita\' quando si ricodifica: piu\' basso = migliore e piu\' '
                    'pesante (default {default})',
    'cli.input.clip': 'File di partenza (senza, li elenca e li fa scegliere)',
    'cli.input_multi': 'File da unire, nell\'ordine in cui vanno messi',
    'cli.dir.clip': 'Unisci tutti i video di questa cartella, in ordine di nome',
    'cli.output.clip': 'File di destinazione (default: accanto all\'originale)',
    'cli.da': 'Da che punto partire (90, 1:30 oppure 01:02:03.5)',
    'cli.a': 'Fino a che punto (senza, fino alla fine)',
    'cli.durata': 'Quanto deve durare (senza, 5 secondi)',
    'cli.preciso': 'Taglia al fotogramma esatto invece che al fotogramma chiave: '
                   'ricodifica, quindi molto piu\' lento',
    'cli.no_chapters': 'Non inserire un capitolo per ogni file unito',
    'cli.fps': 'Fotogrammi al secondo (default {default}: sopra, il peso raddoppia '
               'senza guadagno visibile)',
    'cli.larghezza': 'Larghezza in pixel (default {default}): e\' il fattore che pesa di piu\'',
    'cli.griglia': 'Griglia del provino, nella forma colonne x righe (es. 5x3)',
}
