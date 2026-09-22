# Changelog

Lo storico delle versioni, dalla più recente.

I nomi dei file nelle voci vecchie sono quelli che avevano allora: `AudioDex.py`,
`AudioDex.exe`, `web/`. Non sono refusi, e non vanno corretti — un changelog che
si riscrive il passato smette di essere un changelog. Dove sono finite quelle
cose lo dice la voce qui sotto.

> Torna al [README](../README.md).

---

### 2026-09-22

**La forma: strati, un installatore, e niente più diario**

- 🧱 **Il progetto ha un'alberatura.** Dieci file Python nella radice sono
  diventati `client/` + `cli/` + `server/` a strati (`config`, `utils`,
  `sources`, `audio`, `burn`, `video`, `state`, `services`, `controllers`), con
  una regola scritta: le dipendenze vanno solo verso il basso, e `server/` non
  importa mai niente da `cli/`. Il lavoro non sa chi lo sta guardando, ed è per
  questo che lo stesso motore serve la finestra e il terminale. Vedi
  [Com'è fatto dentro](architettura.md)
- 📦 **Un vero installatore.** `MediaDex-Setup.exe`, fatto con Inno Setup:
  installa in `%LOCALAPPDATA%\Programs` senza chiedere l'amministratore
  (il programma scrive accanto a sé, e dentro «Programmi» non potrebbe),
  scarica WebView2 se manca, e alla disinstallazione **chiede** prima di
  cancellare i brani scaricati. Si costruisce con `.\costruisci.ps1`, che fa
  PyInstaller e Inno in un comando. Vedi [Costruire l'installatore](costruire.md)
- ⚡ **Da file unico a cartella.** Il `.exe` da 64 MB si riestraeva in una
  cartella temporanea **a ogni avvio**. Adesso non si scompatta niente:
  misurati 9,7 s alla finestra contro i 6,9 s dei sorgenti. I primi due avvii
  restano lenti, ma è Defender che scansiona file nuovi e lo fa una volta sola
- 🗑️ **Via la scheda del diario.** Era un muro di righe tecniche che raccontava
  lo stesso lavoro già raccontato, meglio, dalla barra di avanzamento — e
  quando qualcosa andava storto, la riga che contava finiva sepolta sotto le
  altre. Adesso un rifiuto immediato è un **avviso**, un lavoro che cade è una
  **finestra** con la causa in italiano e il testo tecnico sotto, e il diario
  completo continua a scriversi in `logs/`, dove si va a cercarlo
- 🩺 **Gli errori parlano italiano.** `server/utils/contract.py` riconosce le
  famiglie di guasti che MediaDex produce davvero — FFmpeg assente, disco
  pieno, nessun masterizzatore, 403 di yt-dlp — e per ognuna dice cosa fare.
  Quando non riconosce niente non inventa
- 📊 **Ogni sezione ha la sua barra.** Ce n'era una sola, che traslocava nella
  stanza aperta: avviato un download e passati a Montaggio, in Montaggio ci si
  trovava davanti l'avanzamento di quello che stava scaricando di là. Adesso i
  messaggi di Python viaggiano con l'indirizzo della sezione, e una targhetta
  nel menu dice dove sta girando il lavoro anche da un'altra stanza
- 🖥️ **La schermata di caricamento è una sola, e copre lo schermo.** Ce
  n'erano due: quella di PyInstaller, che compariva subito ma era un
  rettangolo di quattrocento pixel al centro, e il velo dentro la finestra,
  che copriva tutto ma arrivava dopo — con in mezzo un incastro da azzeccare
  per non far vedere un buco. Adesso la finestra nasce **massimizzata** e
  visibile subito, e il velo è l'unica attesa. Escono di scena
  `assets/caricamento.png`, `assets/binario.py`, `server/config/splash.py` e
  il metodo `dipinta()`; e **tkinter esce dal pacchetto**, perché era lì solo
  per disegnare quella schermata
- 📶 **La barra dell'avvio scorre invece di scattare.** I sette passi non sono
  distribuiti nel tempo: tre arrivano in mezzo secondo, poi c'è un buco di
  diversi secondi mentre Python risponde. Saltava al 40% e restava immobile,
  che si legge come «piantata». Adesso insegue un tetto che scivola avanti
  piano: non torna mai indietro, non tocca la fine finché c'è lavoro da fare,
  e non resta ferma più di sei decimi di secondo
- 📁 **Non chiede più dove salvare.** C'era un campo con un bottone «sfoglia»
  da riempire prima di poter premere Scarica, e PixDex e ClipDex scrivevano
  accanto al file di partenza, cioè sparsi per il disco dovunque fosse
  l'originale. Adesso c'è `risultati/` con dentro `musica/`,
  `rimasterizzati/` e `montaggi/`, le sottocartelle si creano da sole, e in
  fondo alla barra laterale c'è **Apri la cartella dei risultati**. Da riga di
  comando `--output` e `--base` restano: chi lancia `clip taglia` su un video
  in una cartella sua si aspetta lo spezzone lì
- 💿 **Icona nuova: un disco che si apre in un'onda sonora.** Quella di prima
  era un cerchio con quattro barre di livello dentro, e si confondeva con
  EchoScript, che ha le barre di livello anche lui — due icone simili nella
  barra delle applicazioni sono due programmi che si aprono per sbaglio l'uno
  al posto dell'altro. Il disegno sta in `assets/marchio.py` e da lì escono il
  `.ico`, il `.png` **e i due SVG dentro la pagina**: un comando, tre posti che
  non possono più divergere
- 🗣️ **Solo italiano.** Il menu a tendina per scegliere fra italiano e inglese
  non c'è più: era l'unica impostazione del programma, e per tenerla in piedi
  servivano un metodo nell'API, un file di preferenze e la riscrittura della
  pagina a ogni cambio. I 589 testi sono stati appiattiti da
  `{'it': ..., 'en': ...}` alla sola frase italiana, verificando una per una
  che nessuna cambiasse. Via anche il sottotitolo sotto il marchio
- 🎨 **Barra laterale e intestazioni.** Il marchio è diventato il disegno
  vettoriale dell'icona, sopra il nome; i titoli delle sezioni sono centrati con
  la descrizione sotto e un divisore che sfuma ai capi
- 🧹 **Quattro copie diventate una.** `_check_ffmpeg` era scritto tre volte,
  `probe` due, `_passo` tre, `LARGHEZZA` quattro, le formattazioni di durata e
  peso due a testa. E la finestra arrivava dentro i motori a prendersi
  `px._fattore` e `bd._ordina_tracce`: nomi che l'underscore dichiarava privati
  e che erano invece il contratto vero. Adesso ogni strato ha un'API pubblica
  dichiarata
- 📚 **Il README è sceso da 1642 righe a 344.** Il resto non è stato buttato:
  sta in `docs/`, una pagina per mestiere più architettura, costruzione,
  database e questo changelog
- ▶️ **`python -m cli`** elenca i quattro mestieri e li lancia:
  `python -m cli audio`, `burn`, `pix`, `clip`

---

### 2026-08-02

**Nuovo**

- 🖼️ **Copertine quadrate e volume nei tag, in automatico.** La miniatura 16:9 di YouTube finiva nel tag com'era, e i lettori che mostrano la copertina in un quadrato la schiacciavano o la tagliavano a metà faccia: ora l'immagine intera sta al centro di un quadrato riempito da una sua copia sfocata, e non si perde niente (0,4 s). Il volume viene misurato secondo EBU R128 e annotato nei tag ReplayGain, l'audio non viene toccato, sono due tag che si cancellano. La misura usa `ebur128` invece di `loudnorm`: stessi numeri, **2,3 s invece di 11,6**. Vedi [Copertina e volume](audiodex.md#copertina-e-volume-in-automatico)
- ⚖️ **Il livellamento di BurnDex è diventato il default**, ora che costa quattro secondi a traccia invece di venti. Si spegne con `--no-level`
- 📦 **Un solo file: `AudioDex.exe`.** Doppio clic e parte: niente Python da installare, nessun file `.py` in vista. 64 MB, costruito con `pyinstaller AudioDex.spec`. FFmpeg resta fuori di proposito - in modalita' a file unico il contenuto viene riestratto a ogni avvio, e mezzo gigabyte da scompattare ogni volta renderebbe l'attesa insopportabile per una cosa che si installa una volta sola. I brani, i log e la lingua scelta finiscono accanto all'.exe, dove si ritrovano. Vedi [Un solo file](costruire.md)
- ✂ **ClipDex, il banco di montaggio.** Sei operazioni da riga di comando: `taglia` uno spezzone (in copia è istantaneo, e se lo scostamento dal fotogramma chiave si nota te lo dice con un numero), `unisci` più file scegliendo da solo fra copia e ricodifica e mettendo un capitolo per ciascuno, `gif` e `webp` con la palette calcolata sul filmato (+1,72 dB misurati rispetto a quella generica; il WebP pesa nove volte meno), `provino` a griglia e `compat` per autoradio e TV datate. Vedi [ClipDex](clipdex.md)
- 📀 **Album interi divisi nelle loro tracce.** Moltissimi caricamenti sono "Full Album": un unico video da tre quarti d'ora con i capitoli. AudioDex li riconosce e li taglia **senza ricodificare**, in una cartella numerata e taggata già pronta per BurnDex. Il punto non è tagliare ma capire *se* tagliare: cinque criteri distinguono un disco da un indice, e se anche uno solo non regge non viene chiesto niente. Da riga di comando `--split` e `--no-split`. Vedi [Album interi divisi in tracce](audiodex.md#-album-interi-divisi-in-tracce)
- 🔊 **Dither a 16 bit in BurnDex, sempre attivo.** La riduzione a 16 bit avveniva per troncatura, che genera distorsione *correlata al segnale*: quella che sui passaggi deboli si sente come suono sporco. Misurato su un tono a −70 dBFS, l'energia sulle armoniche scende da +46,9 dB a +31,1 dB rispetto alla fondamentale. Vedi [Cosa succede all'audio prima di incidere](burndex.md#cosa-succede-allaudio-prima-di-incidere)
- ⚖️ **`--level` in BurnDex**: livella il volume fra le tracce secondo lo standard EBU R128, rispettando il picco reale. Su tre brani a −7, −14 e −21 dB lo scarto passa da 14,0 dB a **0,59 dB**
- ✂️ **`--trim` in BurnDex**: rifila i silenzi a inizio e fine traccia, che si sommano ai 2 secondi di stacco inseriti da IMAPI2. Sulla raccolta di prova, 3,4 secondi per traccia
- 🛡 **Verifica d'integrità dei download in AudioDex.** Il controllo era «il file supera i 10 KB», e un download troncato passava: per poi essere riconosciuto come già scaricato al tentativo successivo, e non ripescato mai più. Ora si controllano contenitore, durata effettiva contro quella annunciata, e decodifica del flusso audio. Un file non integro viene cancellato e la traccia finisce fra quelle fallite
- 🎞 **PixDex, rimasterizzatore video.** `PixDex.py` prende un video di qualità scarsa e lo ripulisce: toglie i quadretti della compressione, appiana le bande a scalini nei cieli e nelle dissolvenze, e ingrandisce con Lanczos. **Cinque preset** (Pulito, Standard, Forte, Animazione, Vecchio) scelti automaticamente da una **diagnosi** che legge risoluzione, bit per pixel e ordine dei campi senza decodificare il file. La sbandatura è svolta a **10 bit**, perché a 8 bit il rimedio genera bande nuove. A fine lavoro salva un PNG col **confronto prima/dopo**, i due fotogrammi alla stessa altezza per non barare. Non inventa dettaglio: lavora in sottrazione. Vedi [PixDex](pixdex.md)
- 🔧 **Sbandatura ritarata su misure, non a occhio.** Le soglie di `deband` erano troppo aggressive e producevano puntinato nelle zone piatte: il filtro non appiattisce i gradini, li dissolve in rumore, e dove banda non c'è resta solo il rumore. Misurato su un video AV1 a 305 kbit/s, la taratura prudente vince su **entrambi** i fronti (granulosità da 2,686 a 1,581 e quadretti da 1,204 a 1,166) e produce file molto più leggeri, perché l'encoder non spende più bit per descrivere il puntinato. Vedi [Come è tarata la sbandatura](pixdex.md#come-è-tarata-la-sbandatura)
- ⚡ **GPU accesa di default nella GUI**: misurata 2,4× più veloce sulla catena di filtri vera (30,9 s contro 73,6 s per lo stesso spezzone su Ryzen 5 3500U + Vega 8)
- 🎚 **Scelta della risoluzione d'arrivo al terzo passo**, con una tabella che per ogni modalità mostra il risultato su *quel* file, il fattore di ingrandimento e quanto vale davvero: la stessa riga che offre il 4K dice che da un 360p non aggiunge un solo dettaglio. Da riga di comando `--height auto|none|hd|2k|4k|PIXEL`. Vedi [Fin dove ingrandisce](pixdex.md#fin-dove-ingrandisce-e-come-sceglierlo)
- 🖥 **Sezione Rimasterizza video nella GUI**, con la diagnosi mostrata *prima* di impegnare ore di lavorazione e il confronto prima/dopo direttamente nella finestra

**Modifiche**

- 🇮🇹 **Le tre CLI parlano solo italiano.** Niente più domanda sulla lingua all'avvio e niente più `--lang`: chi apre il terminale vuole vedere il banner e partire. La scelta Italiano/English resta nella GUI, dove è un clic e se ne vede subito l'effetto
- 🔤 **Uscita a video in UTF-8 su tutti gli strumenti.** Frecce, riquadri ed emoji facevano cadere i programmi con `UnicodeEncodeError` dentro il `cmd.exe` classico, che usa la vecchia tabella caratteri cp1252: a metà di un download o, peggio, di una masterizzazione. Ora i flussi vengono riconfigurati all'avvio

### 2026-07-26

**Nuovo**

- 🌍 **Interfaccia in italiano o in inglese.** La GUI ha un menu a tendina **Italiano / English** nella barra laterale: cambia lingua all'istante (voci di menu, etichette, pulsanti, diagnosi, messaggi) e ricorda la scelta in `settings.json`. I tre programmi da terminale parlano invece solo italiano: nessuna domanda all'avvio e nessuna opzione da ricordare. Vedi [Lingua dell'interfaccia](../README.md#-requisiti)
- 🗣 **Risposte accettate in entrambe le lingue** a prescindere da quella scelta: `s`/`si`/`y`/`yes` come conferma, `q`/`esci`/`exit` per uscire, `all`/`tutti`/`tutte` per selezionare tutto. Chi ha l'interfaccia in inglese ma digita `s` per abitudine non si vede più annullare l'operazione

**Modifiche**

- 🧱 **Testi separati dal codice**: le frasi mostrate all'utente stanno in `Shared/strings_audiodex.py` e `Shared/strings_burndex.py`, la macchina che le sceglie in `Shared/i18n.py`. Commenti, docstring e log su file restano in italiano: si rivolgono a chi mantiene il programma, non a chi lo usa
- 📅 **Data di pubblicazione in forma ISO in inglese** (`2013-04-19`) invece di giorno/mese/anno: è l'unica non ambigua tra la convenzione americana, che mette prima il mese, e quella britannica, che mette prima il giorno. In italiano resta `19/04/2013`
- 🔢 **Abbreviazioni dei grandi numeri tradotte**: `1.2 Mrd` / `4.3 Mln` in italiano diventano `1.2 B` / `4.3 M` in inglese

### 2026-07-25

**Nuovo strumento**

- 💿 **BurnDex, masterizzatore di CD audio.** `BurnDex.py` trasforma una raccolta scaricata in un **CD audio** vero (Red Book CD-DA), l'unico formato che autoradio e stereo datati leggono con certezza. Usa **IMAPI2**, l'API COM nativa di Windows: nessun programma di masterizzazione esterno. Procedura guidata a quattro passi con UI Rich coerente con AudioDex, selezione raccolta, scaletta con barra di capienza, scelta della velocità, scheda di conferma, più `--dry-run` per provare tutto senza consumare un disco
- 🔢 **Ordine delle tracce a tre criteri**: `ordine.txt` per il controllo manuale, prefisso numerico nel nome (quello che AudioDex già scrive), data di creazione come ripiego. Il criterio usato è **sempre dichiarato** prima della conferma, perché su un CD-R la scaletta si decide una volta sola
- 💾 **Riconoscimento del disco inserito**: distingue CD-R, CD-RW, CD-ROM, DVD±R/RW, DVD-RAM, BD-R/RE e supporti non identificati, dicendo per ciascuno **perché** non va bene e come rimediare. Il caso critico è il **DVD vergine**, che risulta "vuoto e scrivibile" ma non può contenere un CD audio: il Red Book non è definito su DVD
- 💻 **Riconoscimento del sistema** via WMI: portatile o fisso, presenza di un lettore ottico, e soprattutto se l'unità è **interna o USB esterna**. Sulle esterne l'avviso sull'alimentazione compare **prima** di masterizzare
- ⚡ **Velocità di scrittura dai valori reali dell'unità**: `SupportedWriteSpeeds` espone pochi gradini discreti, e chiedere un valore fuori elenco fa fallire `SetWriteSpeed` invece di rallentare. BurnDex sceglie il gradino più vicino senza superare il richiesto, con 8x consigliata per l'ascolto in auto

**Correzioni**

- 🐛 **Le Mix di YouTube facevano fallire il download di un video singolo** *(AudioDex)*: copiando il link dal player, YouTube ci attacca un `&list=RD<idVideo>&start_radio=1`, la radio automatica costruita su quel brano. `_is_playlist_url` vedeva il `&list=` e la trattava da playlist, ma l'URL canonico `playlist?list=RD…` fa rispondere a YouTube *"This playlist type is unviewable"*, e il download si fermava con «Nessuna traccia trovata nella playlist». Ora le Mix vengono riconosciute (`RD` + id del video, prefissi `RDMM`/`RDEM`/`RDAMVM`/`RDGMEM`/`RDAO`, oppure `start_radio=1`) e si scarica il video, mentre le playlist di YouTube Music `RDCLAK5uy_…`, che invece sono consultabili, restano trattate da playlist. In più, se **una playlist qualsiasi** risulta inaccessibile ma l'URL contiene un `v=`, il programma ripiega sul singolo video invece di arrendersi
- 🐛 **Formato sorgente scelto in base al formato di uscita** *(AudioDex)*: il selettore era fisso su `bestaudio[ext=m4a]` a prescindere dal formato richiesto, quindi `--format opus` scaricava l'**AAC** e poi lo ricomprimeva in Opus, due compressioni con perdita in cascata. Ora la tabella `AUDIO_SOURCE_FORMATS` chiede a YouTube il codec che serve nativamente: `opus` prende l'itag 251 e lo **copia** senza ricodificare, `mp3` parte dal flusso di qualità più alta disponibile. Il comportamento di `m4a`, il default, è invariato
- 🐛 **Interrogazione del disco prima di impegnare l'unità** *(BurnDex)*: `FreeSectorsOnMedia` sul writer Track-At-Once risponde solo **dopo `PrepareMedia()`**, che ha però già aperto la sessione di scrittura. La prima versione moriva lì con un `com_error`. Ora il supporto si legge con `MsftDiscFormat2Data`, che risponde subito, e il Track-At-Once resta per la sola scrittura
- 🐛 **Conteggio veritiero delle tracce scritte** *(BurnDex)*: il riepilogo mostrava le tracce **preparate** invece di quelle effettivamente incise, e dopo un fallimento a zero tracce dichiarava "9 scritte". Ora conta gli `AddAudioTrack` andati a buon fine e distingue i due casi che contano: `0 su 9` (disco ancora vergine e riutilizzabile) da `4 su 9` (scritto a metà, da buttare)
- 🐛 **Percorsi e nomi file nei markup Rich** *(BurnDex)*: una stringa come `D:\` finiva dentro un tag di markup, e siccome in Rich il backslash è carattere di escape si mangiava il tag di chiusura, stampando `D:[/dim]`. Valeva per qualsiasi nome contenente `\` o `[`. Ora ogni stringa che viene da disco passa per `rich.markup.escape()`
- 🐛 **Totali coerenti tra selettore e scaletta** *(BurnDex)*: l'elenco delle raccolte sommava le durate grezze mentre la scaletta aggiungeva gli stacchi da 2 secondi, mostrando due numeri diversi per lo stesso album. Ora entrambi usano `_settori_totali()`
- 🐛 **`ReleaseMedia()` protetta** *(BurnDex)*: quando è l'unità stessa a scomparire dal bus fallisce anche la chiusura della sessione, e l'eccezione secondaria copriva l'errore vero

**Modifiche**

- 🎨 **Livello di presentazione uniformato** *(BurnDex)*: tabelle, pannelli e separatori condividono la stessa larghezza; barre di avanzamento con percentuale e colonna descrizione a larghezza fissa, per non far tremolare la barra a ogni cambio di traccia; barra di capienza a colori sotto ogni scaletta
- 🩺 **Errori IMAPI tradotti**: il codice `0xC0AA020D` (*command timeout*) viene riconosciuto e presentato come problema di alimentazione USB con i rimedi in ordine di efficacia, invece del messaggio COM grezzo
- 📦 **`pywin32>=306`** aggiunto a `requirements.txt`, marcato come necessario solo per BurnDex

### 2026-07-19

**Nuove funzionalità**

- 🔢 **Ordine della playlist rispettato sul disco**: i file delle playlist vengono salvati con il numero di traccia in testa al nome (`01 - Brano.m4a`), zero-padded sulla dimensione della playlist. Il numero è quello della **playlist di origine**: una selezione parziale (tracce 5-8) mantiene `05`-`08`, e un video rimosso non fa scalare le tracce successive
- ♻️ **Numerazione dei file già scaricati**: i brani già presenti **senza numero** (scaricati con una versione precedente) vengono **rinominati** invece che riscaricati, rilanciare il download su una vecchia cartella allinea la numerazione a costo zero
- 📊 **Barre di avanzamento per fase**: quattro barre (Download, Conversione, Testi, Tag) mostrano quante tracce hanno superato ciascun passaggio. Prima esisteva solo la barra dei byte, che restava al 100% mentre la traccia stava ancora convertendo, cercando il testo o scrivendo i tag, sembrava piantata
- 🎬 **Download del video intero**, oltre al solo audio: in modalità interattiva viene **chiesto** prima di partire, da riga di comando c'è `--media video` (o direttamente `--format mp4`/`mkv`). Anche i video vengono **taggati come l'audio** (titolo, artista, album, numero di traccia, copertina, capitoli): nell'`mp4` con mutagen, nell'`mkv` con FFmpeg. L'anti-duplicati ora distingue i formati audio da quelli video, così lo stesso brano può esistere in entrambe le versioni
- 🎬 **Scheda del video prima del download**: incollando l'URL di un video singolo compare un pannello con canale, visualizzazioni, mi piace, iscritti, categoria, lingua, data e capitoli, seguito da una richiesta di conferma. Prima un URL di video singolo faceva partire il download **senza mostrare nulla**
- 💿 **Scheda della playlist arricchita**: al riepilogo si aggiungono canale, visualizzazioni complessive, data dell'ultimo aggiornamento, visibilità e il numero di video **non disponibili**. Erano dati che yt-dlp già restituiva nella stessa chiamata e che venivano scartati: **nessuna richiesta di rete in più**
- 🗄️ **Database: audio e video convivono**. La chiave univoca comprende il **tipo di media**, quindi scaricare lo stesso video prima in audio e poi in video non sovrascrive più la riga precedente. I database esistenti vengono **migrati automaticamente** al primo avvio, con copia di sicurezza

**Correzioni**

- 🐛 **«Fallite» che erano in realtà tracce già presenti**: nel ramo «già scaricato» si leggeva `progress.tasks[task_id]`, ma `Progress.tasks` di Rich è una **lista posizionale**, non indicizzata per `TaskID`. Poiché le barre dei file completati vengono rimosse man mano, gli indici scalavano e partiva un `IndexError`, che `download_batch` catturava marcando la traccia come **fallita**, pur avendo il file sano su disco. Su una playlist tutta già scaricata il riepilogo mostrava metà tracce «Fallite»
- 🐛 **Tracce omonime che si contendevano lo stesso file**: con due brani dallo stesso titolo nella stessa playlist (es. versione singolo e versione album), la rinumerazione riconosceva «stesso titolo, numero qualsiasi» e le due tracce si rinominavano il file a vicenda, lasciandone scaricare una sola. Ora un file **già numerato non viene mai rinominato**
- 🐛 **Ordine dei risultati nel riepilogo**: il riordino finale confrontava i **titoli**, quindi due tracce omonime (o un titolo cambiato da yt-dlp) finivano fuori posto o in fondo. Ora i risultati sono ricomposti dalla **posizione della traccia**

### 2026-06-11

**Correzioni**

- **Ricerca YouTube riparata**: l'opzione `default_search` di yt-dlp restituiva sempre 0 risultati con le versioni recenti, ora la ricerca usa il prefisso esplicito `ytsearchN:`. Aggiornato anche yt-dlp alla 2026.6.9 e vincolata come versione minima in `requirements.txt`
- **Import compatibile con gli IDE**: `scraper_db` viene importato come `from Database_Globale import scraper_db` invece che tramite manipolazione di `sys.path`, così Pylance/VS Code lo risolvono senza falsi errori
- **Fallback artista/canale**: i campi `uploader`/`channel` con valore `None` non producono più "None" nelle tabelle
- **Nomi dei file compatibili con i telefoni**: `_sanitize_filename` ora converte in `_` i "sosia" Unicode a tutta larghezza che yt-dlp usa al posto dei caratteri vietati (`/ : | ? * " < >` → `⧸ ： ｜ …`) e rimuove le emoji; dopo il download il file viene rinominato di conseguenza. Questi caratteri facevano fallire la copia delle tracce verso il telefono tramite cavo USB

**Modifiche**

- **Solo audio**: rimosso del tutto il percorso di download video. Il default è passato da `mp4` (video completo) a `m4a` (solo traccia audio): file di pochi MB invece di centinaia, a parità di qualità sonora. Formati disponibili: `m4a`, `mp3`, `opus`
- **Documentazione del codice in italiano**: ogni funzione, classe e modulo ha una docstring che spiega cosa fa e perché esiste; commenti mirati sulle parti non ovvie (opzioni yt-dlp, threading, database)

**Nuove funzionalità**

- **Testi sincronizzati stile karaoke**: dopo ogni download il testo con i timestamp viene cercato su LRCLIB e incorporato nei tag del file audio (formato LRC), un file unico con dentro anche il testo. Riepilogo con conteggio `♫ Testi karaoke`; disattivabile con `--no-lyrics`
- **Playlist e video privati**: nuova opzione `--cookies-from-browser <browser>` che autentica yt-dlp con i cookie del browser; documentata anche l'alternativa più semplice (playlist "Non in elenco")
- **Tabella delle tracce di una playlist** mostrata prima della conferma di download, e colonna **Views** (formato compatto: `2.1 Mrd`, `45 Mln`, `350 K`) dove YouTube fornisce il dato, nelle playlist non lo espone, quindi lì la colonna è nascosta. I like non sono mostrati: recuperarli costerebbe ~5 s per traccia
- **Colonne Titolo e Artista separate**: l'artista viene ricavato dal titolo (`Artista - Brano`) o dal nome del canale, e il titolo viene ripulito dalle decorazioni (`(Official Video)`, `(Lyrics)`, …)
- **`requirements.txt`** con versioni minime e note su FFmpeg e sull'aggiornamento frequente di yt-dlp
- **Repository GitHub** con `.gitignore` che esclude contenuti scaricati, database locale e log

---
