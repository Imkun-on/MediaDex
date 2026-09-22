"""Le frasi di PixDex: diagnosi, trattamenti, quanto si puo' ingrandire.

Stessa forma degli altri cataloghi, ``'chiave': 'frase'``, con i segnaposto di
``str.format``.

Qui ricorre un tema che negli altri non c'e': dire con chiarezza cosa il
programma *non* fa. Chi arriva alla rimasterizzazione dopo aver visto un video
di ingrandimento con l'intelligenza artificiale si aspetta un dettaglio che non
puo' arrivare, e una frase onesta al momento giusto vale piu' di dieci opzioni
in piu'.
"""
from __future__ import annotations

TESTI: dict[str, str] = {

    # ── Banner e struttura ───────────────────────────────────────────────────
    'banner.subtitle.pix': 'Rimasterizzatore video',
    'banner.tagline.pix': 'pulizia, sbandatura, ingrandimento',
    'step.label': ' Passo {n}/{tot} ',
    'step.source': 'Sorgente',
    'step.diagnosis': 'Diagnosi',
    'step.quality': 'Risoluzione d\'arrivo',
    'step.plan': 'Piano di lavoro',
    'step.remaster': 'Rimasterizzazione',

    # ── Scelta della risoluzione ─────────────────────────────────────────────
    # Le note accanto a ogni voce sono il punto di tutta la schermata: la
    # stessa tabella che offre il 4K dice, sulla stessa riga, quando quel 4K
    # non porterebbe un solo dettaglio in piu'.
    'quality.col_mode': 'Come',
    'quality.col_result': 'Risultato',
    'quality.col_note': 'Quanto vale',
    'quality.auto': 'Automatica',
    'quality.none': 'Solo pulizia',
    'quality.hd': 'HD  1080p',
    'quality.2k': '2K  1440p',
    'quality.4k': '4K  2160p',
    'quality.custom': 'Altra altezza…',
    # I commenti stanno in una colonna da 18 caratteri: devono restare corti
    # o il riquadro spezza le parole a meta'. La spiegazione lunga sta nella
    # riga di aiuto sotto la tabella, dove c'e' spazio.
    'quality.note_native': 'originale',
    'quality.note_ok': 'credibile',
    'quality.note_soft': 'si ammorbidisce',
    'quality.note_fake': 'solo piu\' pesante',
    'quality.hint': '[dim]★ la consigliata: si ferma al doppio, il limite oltre cui\n'
                    '  l\'ingrandimento non aggiunge dettaglio ma solo peso.[/dim]',
    'quality.prompt': '\n[accent]Quale risoluzione[/accent] [dim](numero, invio per la consigliata)[/dim]: ',
    'quality.custom_prompt': '[accent]Altezza in pixel[/accent] [dim](es. 900)[/dim]: ',
    'quality.invalid': '[warning]Scelta non valida:[/warning] [dim]uso quella consigliata.[/dim]',

    # ── Voci comuni ──────────────────────────────────────────────────────────
    'common.cancelled.pix': '[dim]Annullato.[/dim]\n',
    'common.goodbye.pix': '[dim]Niente da fare, alla prossima.[/dim]\n',
    'common.file_missing': '[error]Il file non esiste:[/error] {path}',

    # ── Strumenti esterni ────────────────────────────────────────────────────
    'tools.no_ffmpeg': '[error]Manca all\'appello:[/error] {tools}',
    'tools.install_ffmpeg': '[dim]FFmpeg non e\' installabile con pip. Su Windows:[/dim]\n'
                            '  [accent]winget install Gyan.FFmpeg[/accent]\n'
                            '[dim]poi riapri il terminale, cosi\' il PATH viene riletto.[/dim]',
    'probe.error': '[error]Nessun flusso video leggibile in[/error] {path}\n'
                   '[dim]Un file di solo audio non ha niente da rimasterizzare.[/dim]',

    # ── Scelta del file ──────────────────────────────────────────────────────
    'choose.none': '[warning]Nessun video in[/warning] {path}',
    'choose.ask_path': '\n[accent]Percorso del video[/accent] [dim](invio per uscire)[/dim]: ',
    'choose.col_file': 'File',
    'choose.col_res': 'Risoluzione',
    'choose.col_size': 'Peso',
    'choose.hint': '[dim]I piu\' recenti per primi. Si puo\' anche incollare un percorso qualsiasi.[/dim]',
    'choose.prompt': '\n[accent]Quale video[/accent] [dim](numero o percorso, invio per uscire)[/dim]: ',

    # ── Carta d'identita' del file ───────────────────────────────────────────
    'info.title': ' Il file di partenza ',
    'info.file': 'Nome',
    'info.resolution': 'Risoluzione',
    'info.fps': 'Fotogrammi al secondo',
    'info.codec': 'Codifica',
    'info.bitrate': 'Bitrate',
    'info.duration': 'Durata',
    'info.size': 'Peso',
    'info.scan': 'Scansione',
    'info.interlaced': 'interlacciata [dim](materiale televisivo)[/dim]',

    # ── Diagnosi ─────────────────────────────────────────────────────────────
    'diag.title': ' Cosa c\'e\' da sistemare ',
    'diag.lowres': 'Risoluzione bassa ({h}p): l\'ingrandimento aiuta la resa a schermo '
                   'intero, ma il dettaglio resta quello di partenza.',
    'diag.compressed': 'Compressione marcata ({bpp} bit per pixel): quadretti nelle scene '
                       'scure e aloni intorno ai contorni.',
    'diag.very_compressed': 'Compressione estrema ({bpp} bit per pixel): il file e\' stato '
                            'strizzato al punto che i difetti si vedono anche in movimento.',
    'diag.interlaced': 'Immagine interlacciata: va separata in fotogrammi interi prima di '
                       'qualunque altra lavorazione.',
    'diag.banding_risk': 'Colore a 8 bit: cieli e dissolvenze tendono a mostrare bande a '
                         'scalini, che la lavorazione a 10 bit appiana.',
    'diag.clean': 'Niente di grave: il file e\' gia\' in buono stato, basta una '
                  'passata leggera.',
    'diag.suggested': 'Preset consigliato:',

    # ── Preset ───────────────────────────────────────────────────────────────
    'preset.pulito.name': 'Pulito',
    'preset.pulito.desc': 'Toglie quadretti e bande, non ingrandisce. Il piu\' veloce.',
    'preset.standard.name': 'Standard',
    'preset.standard.desc': 'Il caso normale di un video YouTube: pulizia misurata e '
                            'ingrandimento.',
    'preset.forte.name': 'Forte',
    'preset.forte.desc': 'Sorgente molto rovinata. Accetta di perdere micro-dettaglio pur '
                         'di togliere il disturbo.',
    'preset.animazione.name': 'Animazione',
    'preset.animazione.desc': 'Cartoni e anime: mano leggera sul disturbo per non mangiare le '
                              'linee, mano pesante sulle bande.',
    'preset.vecchio.name': 'Vecchio',
    'preset.vecchio.desc': 'Materiale televisivo o da nastro: prima separa i semiquadri, poi '
                           'pulisce a fondo.',

    # ── Piano di lavoro ──────────────────────────────────────────────────────
    'plan.title': ' Cosa sto per fare ',
    'plan.preset': 'Preset',
    'plan.resolution': 'Risoluzione',
    'plan.no_upscale': 'nessun ingrandimento',
    'plan.encoder': 'Codificatore',
    'plan.audio': 'Audio',
    'plan.audio_copy': 'copiato identico [dim](nessuna ricodifica, nessuna perdita)[/dim]',
    'plan.output': 'File in uscita',
    'plan.filters': 'Catena di filtri',
    'confirm.proceed': '\n[accent]Procedo?[/accent] [dim](invio per si\', n per annullare)[/dim]: ',

    # ── Lavorazione ──────────────────────────────────────────────────────────
    'run.working': 'Rimasterizzo',
    'run.failed': '\n[error]FFmpeg si e\' fermato.[/error]\n[dim]{reason}[/dim]',
    'run.interrupted': '\n[warning]Interrotto.[/warning] [dim]Il file parziale resta sul disco.[/dim]',

    # ── Risultato ────────────────────────────────────────────────────────────
    'result.title': ' Fatto ',
    'result.resolution': 'Risoluzione',
    'result.size': 'Peso',
    'result.file': 'File',
    'result.compare': 'Confronto',
    'result.compare_hint': 'a sinistra il file di partenza, a destra il rimasterizzato, alla '
                           'stessa altezza per non barare',

    # ── Riga di comando ──────────────────────────────────────────────────────
    'cli.desc.pix': 'PixDex — rimasterizza un video: toglie i difetti della '
                    'compressione, appiana le bande e ingrandisce.',
    'cli.epilog.pix': 'Nota: nessun filtro puo\' ricostruire dettaglio che nel file non '
                      'c\'e\'. PixDex lavora in sottrazione, togliendo il disturbo che '
                      'nasconde il dettaglio rimasto.\n'
                      'Esempi:\n'
                      '  python -m cli pix                        procedura guidata\n'
                      '  python -m cli pix -i video.mp4 --info    solo analisi, non scrive\n'
                      '  python -m cli pix -i video.mp4 -p forte  preset esplicito\n'
                      '  python -m cli pix -i video.mp4 --gpu -y  veloce, senza domande',
    'cli.input.pix': 'Video da rimasterizzare (senza, li elenca e li fa scegliere)',
    'cli.output.pix': 'File di destinazione (default: accanto all\'originale, col suffisso PixDex)',
    'cli.base.pix': 'Cartella in cui cercare i video (default: risultati/musica)',
    'cli.preset': 'Preset da usare; senza, lo sceglie la diagnosi',
    'cli.height': 'Risoluzione d\'arrivo: auto (fino al doppio), none (solo pulizia), '
                  'hd, 2k, 4k, oppure un\'altezza in pixel. Senza, la si sceglie a schermo',
    'cli.crf.pix': 'Qualita\' di libx264: piu\' basso = migliore e piu\' pesante (default {default})',
    'cli.gpu': 'Usa il codificatore hardware AMD: molto piu\' veloce, un filo meno pulito',
    'cli.no_compare': 'Non salvare l\'immagine di confronto prima/dopo',
    'cli.info.pix': 'Analizza il file e mostra la diagnosi, senza rimasterizzare',
    'cli.yes.pix': 'Nessuna domanda: usa il preset consigliato e parte',
}
