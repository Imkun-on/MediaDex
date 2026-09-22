"""Le frasi di BurnDex: unita', dischi, scaletta, diagnosi degli errori.

Stessa forma degli altri cataloghi, ``'chiave': 'frase'``, con i segnaposto di
``str.format``.

Qui le frasi sono piu' lunghe che altrove, ed e' voluto: su un CD-R non si
torna indietro, quindi ogni diagnosi non dice solo cosa e' andato storto ma
anche cosa fare. La struttura a elenco numerato e' quella che si segue davvero
mentre si cerca di capire perche' una masterizzazione e' fallita.
"""
from __future__ import annotations

TESTI: dict[str, str] = {

    # ── Banner e struttura ───────────────────────────────────────────────────
    'banner.subtitle.burn': 'Masterizzatore di CD audio',
    'banner.standard': 'standard Red Book CD-DA',
    'step.label': ' Passo {n}/{tot} ',
    'step.collection': 'Raccolta',
    'step.tracklist': 'Scaletta',
    'step.disc_speed': 'Disco e velocita\'',
    'step.burning': 'Masterizzazione',

    # ── Voci comuni ──────────────────────────────────────────────────────────
    'common.cancelled.burn': '[dim]Annullato.[/dim]\n',
    'common.cancelled_op': '[error]Operazione annullata.[/error]',
    'common.goodbye.burn': '\n[dim]Arrivederci![/dim]\n',
    'common.invalid_choice.burn': '[error]Scelta non valida.[/error]',
    'common.invalid_choice_retry': '[error]Scelta non valida. Riprova.[/error]',
    'common.invalid_selection': '[error]Selezione non valida. Riprova.[/error]',
    'common.interrupted': '\n[warning]Interrotto dall\'utente.[/warning]\n',
    'common.continue': '[bold]Continuare? (s/n): [/bold]',
    'common.min': 'min',
    'common.automatic': 'automatica',
    'common.empty': 'vuoto',
    'common.folder_missing': '[error]Cartella inesistente: {path}[/error]',

    # ── Tipi di disco ────────────────────────────────────────────────────────
    'media.unknown': 'sconosciuto',
    'media.disc': 'disco',

    # ── Strumenti esterni ────────────────────────────────────────────────────
    'tools.missing': '\n[error]{tools} non trovato nel PATH.[/error]',
    # 'tools.install_ffmpeg' stava anche qui, e diceva solo «installa con
    # winget». Adesso a stamparla e' una funzione sola - check_ffmpeg in
    # server/utils/ffmpeg.py - quindi la versione che resta e' una: quella di
    # PixDex e ClipDex, che spiega anche perche' pip non basta.
    'tools.no_pywin32': '\n[error]pywin32 non installato.[/error]',
    'tools.no_pywin32_burn': '\n[error]pywin32 non installato: impossibile masterizzare.[/error]',
    'tools.no_pywin32_skip': '[dim]pywin32 non installato: controllo dell\'unita\' saltato.[/dim]\n',
    'tools.install_pywin32': '[dim]Installa con: pip install pywin32[/dim]\n',

    # ── Spazio temporaneo ────────────────────────────────────────────────────
    'temp.low': '\n[warning]ATTENZIONE: solo {free} MB liberi per i file '
                'temporanei (ne servono ~{need}).[/warning]',

    # ── Ordinamento delle tracce ─────────────────────────────────────────────
    'order.file': 'ordine.txt',
    'order.number': 'numero di traccia nel nome',
    'order.created': 'data di creazione',
    'order.missing_file': '[error]ordine.txt cita un file inesistente: {name}[/error]',

    # ── Scelta della raccolta ────────────────────────────────────────────────
    'collection.none_found': '[error]Nessuna raccolta trovata in {base}[/error]',
    'collection.column': 'Raccolta',
    'collection.tracks': 'Tracce',
    'collection.duration': 'Durata',
    'collection.scanning': '[dim]Analisi delle raccolte...[/dim]',
    'collection.singles': '[dim]brani singoli[/dim]',
    'collection.prompt': '\n{disc} [bold]Quale raccolta? (numero, invio per uscire) > [/bold]',
    'collection.default_name': 'Raccolta',
    'collection.no_audio': '[error]Nessun file audio in {path}[/error]',
    'collection.selection_suffix': '{name} · selezione',

    # ── Scaletta ─────────────────────────────────────────────────────────────
    'tracklist.column': 'Traccia',
    'tracklist.duration': 'Durata',
    'tracklist.count': '[dim]{n} tracce[/dim]',
    'tracklist.order_note': '[dim]Ordine: {criterion}  ·  stacchi da 2 s inclusi nel totale[/dim]',
    'tracklist.unreadable': '[error]File illeggibili: {files}[/error]',

    # ── Selezione delle tracce ───────────────────────────────────────────────
    'select.hint.burn': '\n[dim_label]Quali tracce:[/dim_label] numero singolo ([accent]3[/accent]), '
                        'intervallo ([accent]1-5[/accent]), multipli ([accent]1,3,7[/accent]), '
                        '[accent]invio[/accent] per tutte, [accent]q[/accent] per annullare',
    'select.prompt': '\n[bold]Scegli > [/bold]',
    'select.too_long_pick': '[warning]Non ci stanno tutte: {over} min oltre il limite di {limit}. '
                            'Scegli quali masterizzare.[/warning]',

    # ── Unita' e disco ───────────────────────────────────────────────────────
    'drive.panel_title': '[bold bright_blue]Unita\' pronta[/bold bright_blue]',
    'drive.burner': 'Masterizzatore',
    'drive.disc': 'Disco',
    'drive.speed': 'Velocita\'',
    'drive.capacity': '[dim]vuoto · {min} min di capienza[/dim]',
    'drive.none_detected': '[error]Nessun masterizzatore rilevato. Collegalo e riprova.[/error]',
    'drive.index_missing': '[error]Unita\' {index} inesistente (ne risultano {total}).[/error]',
    'drive.available': '\n[dim_label]Masterizzatori disponibili:[/dim_label]',
    'drive.which': '[bold]Quale? > [/bold]',
    # Quando non c'e' un terminale a cui chiedere (l'interfaccia grafica): si
    # prende la prima e lo si dice, invece di restare fermi ad aspettare una
    # risposta che non puo' arrivare.
    'drive.auto_first': 'Piu\' di un masterizzatore: uso il primo, [accent]{name}[/accent].',
    'drive.no_readable_disc': '\n[error]Nessun disco leggibile nell\'unita\'.[/error]',
    'drive.insert_blank': '[dim]Inserisci un CD-R vuoto e riprova.[/dim]\n',
    'drive.external_warning': '[dim]Unita\' esterna: se la scrittura si interrompe a meta\', '
                              'e\' quasi sempre\nla porta USB che non regge l\'assorbimento del '
                              'laser.[/dim]',

    # ── Scelta della velocita' ───────────────────────────────────────────────
    'speed.column': 'Velocita\'',
    'speed.result': 'Resa',
    'speed.recommended': '[success]consigliata[/success][dim] — incisione piu\' netta, '
                         'la piu\' sicura per autoradio e stereo datati[/dim]',
    'speed.fastest': '[dim]la piu\' rapida, ma qualche lettore vecchio puo\' faticare[/dim]',
    'speed.middle': '[dim]via di mezzo[/dim]',
    'speed.prompt': '\n[bold]A che velocita\' scrivo? (1-{n} · invio = {default}): [/bold]',
    'speed.writing_at': '{arrow} [dim_label]Velocita\' di scrittura:[/dim_label] [info]{speed}[/info]',
    'speed.refused': '[warning]L\'unita\' rifiuta l\'impostazione: uso la velocita\' '
                     'automatica.[/warning]',
    'speed.would_use': '\n{arrow} [dim_label]Velocita\' che verrebbe usata:[/dim_label] '
                       '[info]{speed}[/info] [dim](supportate: {supported})[/dim]',
    'speed.none': 'n/d',

    # ── Conferma finale ──────────────────────────────────────────────────────
    'confirm.title': '[bold bright_magenta]💿  Pronto a masterizzare[/bold bright_magenta]',
    'confirm.subtitle': '[bold red]la scrittura su CD-R e\' irreversibile[/bold red]',
    'confirm.drive': 'Unita\'',
    'confirm.disc': 'Disco',
    'confirm.speed': 'Velocita\'',
    'confirm.tracks': 'Tracce',
    'confirm.audio': 'Audio',
    'confirm.levelled': '[bright_green]volume livellato[/bright_green]',
    'confirm.trimmed': '[bright_green]silenzi rifilati[/bright_green]',
    'confirm.audio_untouched': 'nessuna modifica, solo dither a 16 bit',
    'confirm.duration': 'Durata',
    'confirm.free_after': '[dim]({min} min liberi dopo)[/dim]',
    'confirm.prompt': '\n[bold]Procedo con la masterizzazione? (s/n): [/bold]',
    'confirm.disc_intact': '[dim]Annullato. Il disco e\' intatto.[/dim]\n',

    # ── Ricognizione del sistema ─────────────────────────────────────────────
    'system.panel_title': '[bold bright_blue]Il tuo sistema[/bold bright_blue]',
    'system.computer': 'Computer',
    'system.laptop': 'PC portatile',
    'system.desktop': 'PC fisso',
    'system.unknown_type': 'tipo non riconosciuto',
    'system.cd_drive': 'Lettore CD',
    'system.none_detected': '[error]nessuno rilevato[/error]',
    'system.drive_label': 'Unita\' {letter}',
    'system.usb_external': '[warning]collegata in USB (esterna)[/warning]',
    'system.internal': '[success]interna[/success]',
    'system.advice_none': '[error]Questo computer non ha nessun lettore CD.[/error]\n'
                          '[dim]Per masterizzare serve un masterizzatore esterno USB. Su un '
                          'portatile\nrecente e\' la norma: i lettori interni non si montano '
                          'piu\' da anni.[/dim]',
    'system.advice_usb': '[warning]L\'unita\' e\' esterna e si alimenta dalla porta USB.[/warning]\n'
                         '[dim]In scrittura il laser assorbe molto piu\' che in lettura, e una '
                         'porta al limite\nfa riavviare l\'unita\' a meta\' masterizzazione. '
                         'Se una scrittura fallisce:\n'
                         '  1. collega entrambi gli spinotti, se il cavo ne ha due\n'
                         '  2. usa una porta diretta sul PC, mai un hub non alimentato[/dim]',
    'system.advice_internal': '[success]Unita\' interna: alimentazione stabile, nessuna '
                              'precauzione particolare.[/success]',

    # ── Valutazione del disco inserito ───────────────────────────────────────
    'disc.unusable': '\n[error]Disco non utilizzabile: {reason}.[/error]',
    'disc.unknown_type': 'tipo non riconosciuto',
    'disc.unknown_type_why': 'L\'unita\' non e\' riuscita a identificare il disco. Puo\' essere '
                             'graffiato,\ninserito male, oppure di un tipo che questo '
                             'masterizzatore non gestisce.\nProva a estrarlo e reinserirlo.',
    'disc.not_a_cd_why': 'Il CD audio esiste solo sui CD: lo standard Red Book non e\' '
                         'definito\nper DVD e Blu-ray, e nessun lettore da auto saprebbe '
                         'leggerlo.\nServe un CD-R, anche se questo disco ha molto piu\' '
                         'spazio.',
    'disc.pressed_cdrom': 'CD-ROM stampato',
    'disc.pressed_cdrom_why': 'E\' un CD prodotto in fabbrica, di sola lettura. Serve un CD-R vuoto.',
    'disc.cdrw_written': 'CD-RW gia\' scritto',
    'disc.cdrw_written_why': 'Essendo riscrivibile puoi svuotarlo: Esplora risorse, tasto destro\n'
                             'sull\'unita\', "Cancella questo disco". Poi rilancia BurnDex.',
    'disc.cdr_written': 'CD-R gia\' scritto',
    'disc.cdr_written_why': 'Su un CD-R la scrittura e\' definitiva: non si cancella. Serve un '
                            'disco nuovo.',
    'disc.cdrw_blank': 'CD-RW vuoto',
    'disc.cdrw_blank_why': 'Riscrivibile, ma riflette meno luce di un CD-R: molte autoradio e\n'
                           'gli stereo datati non lo leggono. Per l\'auto conviene un CD-R.',
    'disc.cdr_blank': 'CD-R vuoto',
    'disc.not_writable_audio': '\n[error]Questo disco non e\' scrivibile come CD audio.[/error]',
    'disc.too_long': '\n[error]Troppo lungo: il limite prudenziale e\' {limit} min '
                     '({over} min di troppo).[/error]',
    'disc.trim_hint': '[dim]Togli qualche brano, oppure usa ordine.txt per fissare '
                      'cosa masterizzare.[/dim]\n',
    'disc.does_not_fit': '\n[error]Non ci sta: servono {need} min ma il disco ne regge '
                         '{have}.[/error]\n',
    'disc.does_not_fit_exact': '\n[error]Non ci sta sul disco: servono {need} min ma ce ne sono '
                               '{have}.[/error]',

    # ── Prova a vuoto ────────────────────────────────────────────────────────
    'dry.tracklist_ok': '\n{ok} [success]Scaletta valida: ci sta su un CD-R.[/success]',
    'dry.passed': '\n{ok} [success]Prova a vuoto superata: scaletta valida, disco '
                  'idoneo, spazio sufficiente.[/success]',
    'dry.nothing_touched': '[dim]Nessun disco e\' stato toccato. Togli --dry-run per '
                           'masterizzare davvero.[/dim]\n',

    # ── Decodifica e scrittura ───────────────────────────────────────────────
    'burn.measuring': 'Misura del volume...',
    'burn.measured': '[bright_green]Volume misurato[/bright_green]',
    'burn.decoding': 'Decodifica in corso...',
    'burn.decoded': '[bright_green]Decodifica completata[/bright_green]',
    'burn.decode_failed': '\n[error]Decodifica fallita: {file}[/error]',
    'burn.starting': 'Avvio scrittura...',
    'burn.all_written': '[bright_green]Tutte le tracce scritte[/bright_green]',
    'burn.closing': '\n[dim]Chiusura della sessione...[/dim]',
    'burn.close_failed': '[warning]L\'unita\' non ha risposto nemmeno alla chiusura: '
                         'scollegala e ricollegala prima di riprovare.[/warning]',
    'burn.timeout': '\n[error]L\'unita\' non ha risposto al comando di scrittura.[/error]',
    'burn.timeout_why': '[dim]Tipico dei masterizzatori USB alimentati dalla sola porta dati: quando il\n'
                        'laser passa in potenza di scrittura l\'assorbimento sale di colpo e l\'unita\'\n'
                        'si riavvia. Da provare, in quest\'ordine:\n'
                        '  1. se il cavo ha due spinotti USB, collegarli entrambi (uno e\' solo corrente)\n'
                        '  2. porta USB diretta sul PC, mai un hub non alimentato\n'
                        '  3. un hub USB con alimentatore esterno[/dim]',
    'burn.write_error': '\n[error]Errore durante la scrittura: {error}[/error]',

    # ── Riepilogo finale ─────────────────────────────────────────────────────
    'result.ok_title': '[bold bright_green]✓  Masterizzazione completata[/bold bright_green]',
    'result.fail_title': '[bold red]✗  Masterizzazione fallita[/bold red]',
    'result.tracks_written': 'Tracce scritte',
    'result.out_of': '[dim]su {total}[/dim]',
    'result.total_duration': 'Durata totale',
    'result.outcome': 'Esito',
    'result.finalised': '[success]disco finalizzato[/success]',
    'result.ready_to_play': '[dim]pronto da provare nel lettore[/dim]',
    'result.aborted': '[error]interrotto[/error]',
    'result.disc': 'Disco',
    'result.disc_still_good': '[info]nessun dato audio scritto: e\' ancora buono[/info]',
    'result.disc_ruined': '[warning]scritto a meta\': non e\' recuperabile[/warning]',

    # ── Modalita' --info ─────────────────────────────────────────────────────
    'info.no_imapi_drive': '\n[error]Nessun masterizzatore utilizzabile da IMAPI.[/error]',
    'info.check_external': '[dim]Se e\' esterno, controlla che sia collegato e acceso.[/dim]\n',
    'info.drive_column': 'Unita\'',
    'info.disc_column': 'Disco inserito',
    'info.speed_column': 'Vel.',
    'info.no_disc': '[dim]nessun disco[/dim]',
    'info.blank': '[success]{type} vuoto[/success] [dim]{capacity}[/dim]',
    'info.written': '[warning]{type} gia\' scritto[/warning]',

    # ── Riga di comando ──────────────────────────────────────────────────────
    'cli.desc.burn': 'BurnDex - Masterizzatore di CD audio per le raccolte di AudioDex',
    'cli.epilog.burn': 'Esempi:\n'
                       '  python -m cli burn --info\n'
                       '  python -m cli burn --dir "risultati/musica/Molchat Doma - Etazhi" --dry-run\n'
                       '  python -m cli burn --dir "risultati/musica/Molchat Doma - Etazhi" --speed 4\n',
    'cli.dir.burn': 'Cartella da masterizzare. Se omessa, la scegli da un elenco',
    'cli.base.burn': 'Cartella delle raccolte (default: risultati/musica)',
    'cli.speed': 'Velocita\' di scrittura in "x". Se omessa viene chiesta '
                 '(o {default}x con --yes). Piu\' bassa = piu\' compatibile con le autoradio',
    'cli.drive': 'Indice del masterizzatore da usare (vedi --info)',
    'cli.dry_run': 'Mostra la scaletta e verifica che ci stia, senza toccare il disco',
    'cli.info.burn': 'Elenca i masterizzatori e il disco inserito, poi esce',
    'cli.yes.burn': 'Nessuna domanda: tutte le tracce, velocita\' predefinita, nessuna conferma',
    'cli.no_level': 'Non livellare il volume fra le tracce: lascia ogni brano al volume '
                    'con cui e\' stato caricato, salti in auto compresi',
    'cli.trim': 'Rifila i silenzi a inizio e fine traccia, che si sommano ai 2 '
                'secondi di stacco inseriti comunque fra un brano e l\'altro',
    'cli.no_eject': 'Non espellere il disco a fine masterizzazione',
}
