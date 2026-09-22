"""Le frasi di AudioDex: ricerca, download, tag, testi sincronizzati.

Una voce per frase mostrata a chi usa il programma, nella forma
``'chiave': 'frase'``. I segnaposto sono quelli di ``str.format``: chi scrive
la frase li mette dove gli servono, chi la chiama passa i valori per nome e
non deve sapere in che ordine finiranno.

Il markup Rich (``[error]``, ``[bold]``...) resta dentro le frasi quando fa
parte della frase: evidenziare una parola e' una scelta di chi la scrive, e
tenerlo fuori costringerebbe a spezzare le stringhe in pezzi senza senso
compiuto. La finestra lo toglie da sola (``t()`` in ``client/app.js``), perche'
a schermo non serve.

I commenti e i docstring del programma non stanno qui: si rivolgono a chi
legge il codice, non a chi lo usa.
"""
from __future__ import annotations

TESTI: dict[str, str] = {

    # ── Riga di comando ──────────────────────────────────────────────────────
    'cli.desc.audio': 'AudioDex - Downloader audio da YouTube',
    'cli.search': 'Cerca per nome canzone/artista',
    'cli.url': 'URL diretto (video, playlist, album)',
    'cli.output.audio': 'Cartella di destinazione (default: risultati/musica)',
    'cli.media': 'Scarica solo audio o il video intero. Se omesso, in modalita\' '
                 'interattiva viene chiesto; con --search/--url il default e\' audio',
    'cli.format': 'Formato del file (audio: m4a/mp3/opus · video: mp4/mkv). '
                  'Default: m4a per l\'audio, mp4 per il video',
    'cli.workers': 'Worker paralleli (default: {n})',
    'cli.max_results': 'Risultati ricerca max (default: {n})',
    'cli.no_lyrics': 'Non cercare i testi sincronizzati su LRCLIB',
    'cli.cookies': 'Usa i cookie del browser indicato per accedere a playlist/video privati',
    # ── Divisione di un album in tracce ──────────────────────────────────────
    'split.detected': "[accent]Questo sembra un disco:[/accent] {n} capitoli, "
                      "in media {media} l'uno.",
    'split.sample': '  [dim]{n:>2}.[/dim] {titolo}  [dim]{durata}[/dim]',
    'split.more': '  [dim]… e altri {n}[/dim]',
    'split.ask': '\n[accent]Lo divido nelle sue tracce?[/accent] '
                 '[dim](s/n — il file intero resta comunque)[/dim]: ',
    'split.done': '{sym} Diviso in [bold]{n}[/bold] tracce: [dim]{cartella}[/dim]',
    'cli.split': 'Divide in tracce i video che hanno i capitoli di un disco '
                 '(album interi caricati come un unico video)',
    'cli.no_split': 'Non chiedere mai di dividere, nemmeno in modalita\' interattiva',

    # ── Verifica d'integrita' ────────────────────────────────────────────────
    # Sono messaggi che finiscono nell'elenco dei brani falliti: devono dire
    # cosa non va in modo che si capisca se val la pena ritentare.
    'verify.unreadable': 'file illeggibile: il contenitore non si apre',
    'verify.truncated': 'download troncato: dura {reale} invece di {attesa}',
    'verify.corrupt': 'audio danneggiato ({reason})',
    'cli.err_video_format': '--format {fmt} e\' un formato video, incompatibile con --media audio',
    'cli.err_audio_format': '--format {fmt} e\' un formato audio, incompatibile con --media video',

    # ── Avvio e controlli ────────────────────────────────────────────────────
    'start.no_mutagen': '[warning]mutagen non installato - tagging disabilitato[/warning]',
    'start.install_mutagen': '[dim]Installa con: pip install mutagen[/dim]\n',
    'disk.low': '\n[warning]ATTENZIONE: solo {mb} MB liberi.[/warning]',
    'disk.continue': '[bold]Continuare? (s/n): [/bold]',
    'common.cancelled_op': '[error]Operazione annullata.[/error]',
    'common.cancelled.audio': '[dim]Annullato.[/dim]',
    'common.goodbye.audio': '\n[dim]Arrivederci![/dim]\n',
    'common.invalid_choice.audio': '[error]Scelta non valida. Riprova.[/error]',
    'common.invalid_selection': '[error]Selezione non valida. Riprova.[/error]',
    'common.unknown': 'Sconosciuto',

    # ── Unita' di misura compatte ────────────────────────────────────────────
    # Le abbreviazioni dei grandi numeri non coincidono: 'Mrd' (miliardi) in
    # inglese non significa nulla, e 'B' (billion) in italiano si leggerebbe
    # come un errore.
    'unit.billions': 'Mrd',
    'unit.millions': 'Mln',
    'unit.thousands': 'K',

    # Ordine dei campi di una data. L'italiano scrive giorno/mese/anno;
    # per l'inglese si usa la forma ISO, che e' l'unica non ambigua tra
    # convenzione americana (mese prima) e britannica (giorno prima).
    'date.format': '{d}/{m}/{y}',

    # ── Nomi delle lingue nella scheda video ─────────────────────────────────
    'lang.it': 'Italiano',
    'lang.en': 'Inglese',
    'lang.es': 'Spagnolo',
    'lang.fr': 'Francese',
    'lang.de': 'Tedesco',
    'lang.pt': 'Portoghese',
    'lang.ru': 'Russo',
    'lang.ja': 'Giapponese',
    'lang.ko': 'Coreano',
    'lang.zh': 'Cinese',
    'lang.ar': 'Arabo',
    'lang.nl': 'Olandese',
    'lang.pl': 'Polacco',
    'lang.tr': 'Turco',
    'lang.hi': 'Hindi',
    'lang.sv': 'Svedese',
    'lang.ro': 'Rumeno',
    'lang.el': 'Greco',
    'lang.uk': 'Ucraino',
    'lang.cs': 'Ceco',

    # ── Scheda del video ─────────────────────────────────────────────────────
    'card.channel': 'Canale',
    'card.views': 'Visualizzazioni',
    'card.likes': 'Mi piace',
    'card.subscribers': 'Iscritti',
    'card.category': 'Categoria',
    'card.language': 'Lingua',
    'card.published': 'Pubblicato',
    'card.duration': 'Durata',
    'card.chapters': 'Capitoli',
    'card.sections': '{n} sezioni',
    'card.confirm': '\n[bold]Procedo con il download di questo video? (s/n): [/bold]',

    # ── Tabella dei risultati ────────────────────────────────────────────────
    'table.search_results': 'Risultati ricerca',
    'table.playlist_tracks': 'Tracce della playlist',
    'table.title': 'Titolo',
    'table.artist': 'Artista',
    'table.duration': 'Durata',
    'table.views': 'Views',

    # ── Scheda della playlist ────────────────────────────────────────────────
    'playlist.channel': 'Canale',
    'playlist.tracks': 'Tracce',
    'playlist.total_duration': 'Durata totale',
    'playlist.views': 'Visualizzazioni',
    'playlist.updated': 'Aggiornata',
    'playlist.visibility': 'Visibilita\'',
    'playlist.unavailable': 'Non disponibili',
    'playlist.unavailable_n': '[warning]{n} (privati o rimossi)[/warning]',
    'visibility.public': 'Pubblica',
    'visibility.unlisted': 'Non in elenco',
    'visibility.private': 'Privata',

    # ── Download ─────────────────────────────────────────────────────────────
    'download.threads': 'Thread:',
    'download.tracks': 'Tracce:',
    'download.format': 'Formato:',
    'download.bar_tracks': 'Tracce',
    'phase.download': 'Download',
    'phase.convert': 'Conversione',
    'phase.lyrics': 'Testi',
    'phase.tag': 'Tag',

    # ── Riepilogo ────────────────────────────────────────────────────────────
    'summary.title': 'Riepilogo',
    'summary.total': 'Tracce totali',
    'summary.downloaded': 'Scaricate',
    'summary.split': 'Tracce ricavate dai capitoli',
    'summary.lyrics': 'Testi karaoke',
    'summary.already': 'Gia\' presenti',
    'summary.failed': 'Fallite',
    'summary.failed_tracks': '  Tracce',

    # ── Tracce fallite ───────────────────────────────────────────────────────
    'failed.file_header': '# Tracce fallite\n'
                          '# Per ritentare, copia gli URL e usa: python -m cli audio --url <URL>\n#\n',
    'failed.saved': '\n  Tracce fallite salvate in: [info]{path}[/info]',

    # ── Selezione delle tracce ───────────────────────────────────────────────
    'select.hint.audio': '\n[dim_label]Seleziona:[/dim_label] numero singolo ([accent]3[/accent]), '
                         'intervallo ([accent]1-5[/accent]), multipli ([accent]1,3,7[/accent]), '
                         '[accent]all[/accent] per tutti, [accent]q[/accent] per uscire',
    'select.prompt': '\n[bold]Scegli > [/bold]',

    # ── Audio o video ────────────────────────────────────────────────────────
    'media.column_choice': 'Scelta',
    'media.audio_only': 'Solo audio',
    'media.audio_note': '  [dim]pochi MB, taggato, con il testo karaoke[/dim]',
    'media.full_video': 'Video intero',
    'media.video_note': '  [dim]immagine + audio, file molto piu\' grande[/dim]',
    'media.prompt': '\n[bold]Cosa scarico? (1 = audio · 2 = video · q = annulla): [/bold]',

    # ── Modalita' interattiva ────────────────────────────────────────────────
    'interactive.header': '\n[dim_label]Modalita\' interattiva[/dim_label]\n  '
                          '{dot} Digita un [accent]nome canzone/artista[/accent] per cercare\n  '
                          '{dot} Incolla un [accent]URL[/accent] (video/playlist) per download diretto\n  '
                          '{dot} Digita [accent]q[/accent] per uscire\n',
    'interactive.prompt': '\n{note} [bold]Cerca o incolla URL > [/bold]',
    'interactive.download_all': '\n[dim_label]Scaricare tutte le {n} tracce? (s/n)[/dim_label]',
    'interactive.answer_prompt': '[bold]> [/bold]',
    'interactive.fetching_video': '\n[dim]Recupero le informazioni del video...[/dim]',

    # ── Errori di estrazione ─────────────────────────────────────────────────
    'error.playlist_unreachable': '[warning]Playlist non accessibile: scarico il singolo video.[/warning]',
    'error.no_tracks_playlist': '[error]Nessuna traccia trovata nella playlist.[/error]',
    'error.no_tracks': '[error]Nessuna traccia trovata.[/error]',
    'error.no_results': '[error]Nessun risultato trovato.[/error]',
    'error.no_info_url': '[error]Impossibile estrarre info dal URL.[/error]',
    'error.no_info': '[error]Impossibile estrarre info.[/error]',
}
