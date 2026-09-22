# AudioDex — scaricare da YouTube

Come cercare, cosa arriva, e tutte le scelte che il programma fa per conto
tuo: l'ordine delle tracce, i tag, i testi sincronizzati, gli album caricati
come video unico.

> Torna al [README](../README.md).

---

## 🆚 Perché AudioDex e non i soliti convertitori online

I siti "YouTube to MP3" sono gratuiti solo in apparenza. Nella pratica:

- ti fanno cliccare su **pubblicità travestite** da pulsante di download;
- impongono un **tetto di durata** (spesso 10-20 minuti) o **una traccia alla volta**;
- restituiscono file **senza tag e senza copertina**, chiamati `video_1.mp3`;
- **ricodificano** l'audio in 128 kbps, peggiorandolo rispetto all'originale;
- per una playlist ti chiedono l'**account** o il piano **premium**.

AudioDex nasce per togliere di mezzo tutto questo:

| | Tipico convertitore online | **AudioDex** |
|---|---|---|
| **Costo reale** | gratis → poi premium / pubblicità invasiva | **gratis davvero**, gira sul tuo PC |
| **Playlist intere** | a pagamento o assenti | **sì**, in una cartella ordinata |
| **Durata massima** | spesso 10-20 min | **nessun limite** |
| **Qualità audio** | ricodifica a 128 kbps | **flusso originale**, `m4a` senza ricodifica |
| **Tag e copertina** | quasi mai | **sempre** (titolo, artista, album, traccia, cover) |
| **Testo del brano** | no | **sincronizzato, dentro il file** |
| **Ordine delle tracce** | casuale | **quello della playlist**, numerato |
| **Account obbligatorio** | frequente | **no** |
| **Download paralleli** | no | **sì** (3 di default, configurabili) |
| **Open source** | mai | **sì** |

In breve: **lo controlli tu**, gira sul **tuo computer**, e i file che ottieni sono quelli che avresti comprato.

---

---

## 🚀 Uso ed esempi

```bash
python -m cli audio
```

### Il flusso interattivo, passo per passo

1. **Avvio**: banner, controllo dello spazio disco, inizializzazione del database
2. **Cerca o incolla**: digita un nome di canzone/artista per cercare, oppure incolla direttamente un URL
3. **Selezione**: scegli quali risultati scaricare (numero, intervallo, elenco, `all`)
4. **Download**: le tracce vengono scaricate in parallelo con barre di avanzamento live; ogni file viene taggato (titolo, artista, album, copertina) e arricchito del testo sincronizzato se disponibile
5. **Riepilogo**: pannello finale con scaricate / già presenti / fallite
6. Il loop riparte: nuova ricerca oppure `q` per uscire

### Esempio 1: Ricerca per nome

```
╔═════════════════════════════════════════════════╗
║                                                 ║
║      ___             ___       ____             ║
║     /   | __  ______/ (_)___  / __ \___  _  __  ║
║    / /| |/ / / / __  / / __ \/ / / / _ \| |/_/  ║
║   / ___ / /_/ / /_/ / / /_/ / /_/ /  __/>  <    ║
║  /_/  |_\__,_/\__,_/_/\____/_____/\___/_/|_|    ║
║                                                 ║
╚═════════════════════════════════════════════════╝

Modalita' interattiva
  • Digita un nome canzone/artista per cercare
  • Incolla un URL (video/playlist) per download diretto
  • Digita q per uscire

♫ Cerca o incolla URL > linkin park in the end

                            Risultati ricerca
╭──────┬───────────────────────────────┬──────────────┬────────┬─────────╮
│    # │ Titolo                        │ Artista      │ Durata │   Views │
├──────┼───────────────────────────────┼──────────────┼────────┼─────────┤
│    1 │ In The End                    │ Linkin Park  │   3:54 │ 290 Mln │
│    2 │ In the End                    │ Linkin Park  │   3:36 │ 1.2 Mrd │
│    3 │ In The End                    │ Linkin Park  │   3:31 │  45 Mln │
│  ... │                               │              │        │         │
╰──────┴───────────────────────────────┴──────────────┴────────┴─────────╯

Seleziona: numero singolo (3), intervallo (1-5), multipli (1,3,7),
all per tutti, q per uscire

Scegli > 1

─────────────────────────── ⬇ Download audio ───────────────────────────
  Thread: 3  Tracce: 1

⠋ Tracce      ████████████████████████████████  100%  1/1  │ 0:00:05
⠋ Download    ████████████████████████████████  1/1
⠋ Conversione ████████████████████████████████  1/1
⠋ Testi       ████████████████████████████████  1/1
⠋ Tag         ████████████████████████████████  1/1
──────────────────────────────────────────────
⠋ #1 In The End [Official HD...  ██████████  100%  3.6/3.6 MB  2.1 MB/s

╔═════════════ ✅ Riepilogo ═════════════╗
║                                        ║
║   Tracce totali   1                    ║
║   ✓ Scaricate     1                    ║
║   ♫ Testi karaoke 1                    ║
║                                        ║
╚════════════════════════════════════════╝

♫ Cerca o incolla URL > q

Arrivederci!
```

### Esempio 2: Download di una playlist

Incollando l'URL di una playlist (o di un video che le appartiene, tipo `watch?v=...&list=...`), il programma la riconosce, mostra il riepilogo e chiede se scaricare tutto o selezionare le tracce:

```
♫ Cerca o incolla URL > https://www.youtube.com/playlist?list=OLAK5uy_kkk...

┌──────── 💿 Molchat Doma - Etazhi ────────┐
│                                          │
│    📺  Canale            Molchat Doma    │
│    🎵  Tracce            9               │
│    ⏱  Durata totale      33:18           │
│    👁  Visualizzazioni    2.4 Mln         │
│    📅  Aggiornata        14/03/2024      │
│    🔓  Visibilità        Pubblica        │
│                                          │
└──────────────────────────────────────────┘

                Tracce della playlist
╭──────┬─────────────────────────┬──────────────┬────────╮
│    # │ Titolo                  │ Artista      │ Durata │
├──────┼─────────────────────────┼──────────────┼────────┤
│    1 │ Na Dne                  │ Molchat Doma │   3:31 │
│    2 │ Tantsevat               │ Molchat Doma │   3:33 │
│    3 │ Volny                   │ Molchat Doma │   3:25 │
│  ... │                         │              │        │
╰──────┴─────────────────────────┴──────────────┴────────╯

Scaricare tutte le 9 tracce? (s/n)
> s

─────────────────────────── ⬇ Download audio ───────────────────────────
  Thread: 3  Tracce: 9

⠋ Tracce      ██████████████████░░░░░░░░░░  67%  6/9  │ 0:01:12 → 0:00:35
⠋ Download    ████████████████████████░░░░  8/9
⠋ Conversione ██████████████████████░░░░░░  7/9
⠋ Testi       ████████████████████░░░░░░░░  6/9
⠋ Tag         ████████████████████░░░░░░░░  6/9
──────────────────────────────────────────────
⠋ #7 Тоска           ██████████░░░░░  64%  2.1/3.3 MB  1.8 MB/s
⠋ #8 Клетка          ████░░░░░░░░░░░  28%  0.9/3.2 MB  2.0 MB/s
⠋ #9 Коммерсанты     ██░░░░░░░░░░░░░  11%  0.4/3.5 MB  1.7 MB/s
```

Le **quattro barre di fase** raccontano cosa sta succedendo davvero: scaricare un brano non è un passaggio solo, e senza di esse un file restava apparentemente fermo al 100% mentre in realtà stava ancora convertendo, cercando il testo o scrivendo i tag.

| Fase | Cosa fa |
|---|---|
| **Download** | trasferimento del flusso audio da YouTube (l'unica con i byte noti, mostrati sotto) |
| **Conversione** | FFmpeg estrae/rimuxa nel formato scelto |
| **Testi** | interrogazione di LRCLIB per il testo sincronizzato |
| **Tag** | scrittura di metadati e copertina nel file |

> Una traccia **già presente** o **fallita** non attraversa tutte le fasi: le barre vengono comunque completate a fine lavorazione, così arrivano in fondo insieme al lavoro invece di restare indietro per sempre.

Le tracce finiscono in una **sottocartella con il nome dell'album**, **numerate nell'ordine della playlist**:

```
risultati/musica/Molchat Doma - Etazhi/
├── 01 - Na Dne.m4a
├── 02 - Tantsevat.m4a
├── 03 - Volny.m4a
└── ...
```

Rispondendo `n` alla domanda si apre la selezione manuale (`1-5`, `1,3,7`, ecc.) usando i numeri della tabella.

> ℹ️ Nelle playlist la colonna **Views** non compare: YouTube non fornisce quel dato nell'elenco delle tracce (solo titolo e durata). L'artista viene ricavato dal titolo `Artista - Brano`; dove il formato manca compare `??`.

### Esempio 3: La scheda di un video singolo

Incollando l'URL di un **video singolo** (senza `list=`), prima di scaricare compare la sua scheda:

```
♫ Cerca o incolla URL > https://www.youtube.com/watch?v=...

Recupero le informazioni del video...

┌─ 🎬 But what is a neural network? | Deep learning chapter 1 ─┐
│                                                              │
│    📺  Canale            3Blue1Brown                         │
│    👁  Visualizzazioni    23.7 Mln                            │
│    👍  Mi piace          553 K                               │
│    👥  Iscritti          8.5 Mln                             │
│    🏷  Categoria          Education                           │
│    🗣  Lingua             Inglese                             │
│    📅  Pubblicato        05/10/2017                          │
│    ⏱  Durata             18:40                               │
│    📑  Capitoli          12 sezioni                          │
│                                                              │
└──────────────────────────────────────────────────────────────┘

Procedo con il download di questo video? (s/n):
```

Serve a capire a colpo d'occhio se è il video giusto prima di consumare banda. I campi che YouTube non espone vengono **omessi**, non mostrati vuoti.

> ℹ️ **Perché solo per i video singoli.** La scheda richiede l'estrazione **completa** dei metadati (`extract_flat` disattivato): è l'unica che riporta mi piace, iscritti, categoria e lingua, ma costa un paio di secondi. Per un video è tempo ben speso; su una playlist da 50 tracce sarebbero minuti di attesa, quindi lì resta l'estrazione veloce e la tabella riassuntiva.

> Con `--url` la scheda viene comunque **mostrata**, ma senza chiedere conferma: da riga di comando hai già dichiarato cosa vuoi scaricare, e un prompt bloccherebbe gli script.

### Esempio 4: Uso da riga di comando

Per saltare la modalità interattiva. Anche qui le righe sono esempi alternativi, uno per volta:

```bash
# Ricerca una tantum (mostra i risultati e chiede la selezione)
python -m cli audio --search "daft punk get lucky"

# Download diretto di un video o di una playlist
python -m cli audio --url "https://www.youtube.com/watch?v=..."
python -m cli audio --url "https://www.youtube.com/playlist?list=..."

# In mp3, in una cartella personalizzata, con 5 download paralleli
python -m cli audio --url "https://..." --format mp3 --output "D:\Musica" --workers 5

# Video intero invece del solo audio (mp4)
python -m cli audio --url "https://..." --media video
python -m cli audio --url "https://..." --format mkv     # --media video implicito
```

> Con `--search`/`--url` il default resta **audio**: la domanda non viene posta, così gli script non restano appesi a un prompt.

---

## 🔧 Opzioni della riga di comando

| Opzione | Abbrev. | Default | Descrizione |
|---|---|---|---|
| `--search "testo"` | `-s` | - | Cerca per nome canzone/artista (alternativa a `--url`) |
| `--url <link>` | `-u` | - | URL diretto di video, playlist o album |
| `--output <cartella>` | `-o` | `risultati/musica/` | Cartella di destinazione dei file |
| `--media {audio,video}` | `-m` | *(chiesto)* | Scarica solo l'audio o il video intero. Se omesso: in modalità interattiva viene **chiesto**, con `--search`/`--url` il default è `audio` |
| `--format {m4a,mp3,opus,mp4,mkv}` | `-f` | `m4a` / `mp4` | Formato di output. I primi tre sono audio, gli ultimi due video: indicarne uno **implica** il `--media` corrispondente |
| `--workers <n>` | `-w` | `3` | Numero di download paralleli |
| `--max-results <n>` | - | `15` | Numero massimo di risultati di ricerca |
| `--no-lyrics` | - | disattivato | Non cercare i testi sincronizzati su LRCLIB |
| `--split` | - | disattivato | Divide in tracce i video che hanno i capitoli di un disco: vedi [Album interi divisi in tracce](#-album-interi-divisi-in-tracce) |
| `--no-split` | - | disattivato | Non chiedere mai di dividere, nemmeno in modalità interattiva |
| `--cookies-from-browser <browser>` | - | - | Usa i cookie del browser (`firefox`, `chrome`, `edge`, …) per accedere a playlist e video **privati** |

> Senza `--search` né `--url` si avvia la **modalità interattiva**.

### Playlist private

Se incolli l'URL di una tua playlist **privata**, YouTube risponde *"The playlist does not exist"*: senza autenticazione la playlist è invisibile. Due soluzioni:

1. ⭐ **Consigliata:** su YouTube imposta la playlist su **"Non in elenco"**, non diventa pubblica (è visibile solo a chi ha il link) e l'URL funziona subito, senza altre opzioni.
2. Per tenerla **privata**: avvia con `--cookies-from-browser firefox` (o il tuo browser), yt-dlp legge i cookie e si presenta a YouTube autenticato come te.

> 🪟 **Nota per Windows:** con Chrome/Edge la lettura dei cookie può fallire per la cifratura recente del browser (prova a chiuderlo prima); con **Firefox** funziona in modo affidabile.

---

## 🔀 Come funziona il download

### 1. Ricerca

La ricerca usa il motore interno di yt-dlp con il prefisso `ytsearchN:<query>` e l'opzione `extract_flat`: vengono recuperati **solo i metadati** (titolo, canale, durata, URL) senza scaricare nulla. È la stessa tecnica usata per le playlist, dove `ignoreerrors` fa sì che i video privati o rimossi vengano saltati invece di far fallire l'intero elenco.

### 2. Normalizzazione degli URL playlist

Se si incolla l'URL di un video che fa parte di una playlist (`watch?v=...&list=...`), yt-dlp estrarrebbe **solo quel video**. Il programma estrae l'ID della playlist e lo converte nell'URL canonico `playlist?list=<ID>`, ottenendo l'elenco completo delle tracce.

### 3. Download: audio o video

**Solo audio** (default). yt-dlp viene configurato così:

```python
'format': AUDIO_SOURCE_FORMATS[<formato scelto>]   # niente traccia video
'postprocessors': [{'key': 'FFmpegExtractAudio',
                    'preferredcodec': <formato scelto>,
                    'preferredquality': '0'}]      # qualità massima
```

Il flusso richiesto **dipende dal formato di uscita**, così che sorgente e destinazione coincidano e FFmpeg possa limitarsi a **rimuxare** invece di ricodificare:

```python
AUDIO_SOURCE_FORMATS = {
    'm4a':  'bestaudio[ext=m4a]/bestaudio[acodec^=mp4a]/bestaudio/best',   # AAC, itag 140
    'opus': 'bestaudio[acodec=opus]/bestaudio[ext=webm]/bestaudio/best',   # Opus, itag 251
    'mp3':  'bestaudio/best',      # YouTube non serve mai l'mp3: conversione inevitabile
}
```

Ogni voce termina con dei ripieghi progressivi, per i video che non espongono il codec preferito. Quando sorgente e destinazione coincidono (il caso di `m4a`, il default) l'audio viene **ricopiato byte per byte**: nessuna perdita di qualità, nemmeno teorica.

**Video intero** (`--media video`). YouTube serve video e audio come **flussi separati**, le risoluzioni alte non hanno l'audio incorporato, quindi si prende il meglio di entrambi e FFmpeg li unisce nel container scelto:

```python
'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best'
'merge_output_format': 'mp4'    # oppure 'mkv'
```

Il fallback `best` in coda copre i video serviti a flusso unico.

**Anche i video vengono taggati**, con la stessa cura dell'audio, cambia solo lo strumento, perché i due container usano sistemi di metadati diversi:

| | `mp4` | `mkv` |
|---|---|---|
| **Titolo, artista, album, n. traccia** | ✅ mutagen (tag iTunes) | ✅ FFmpeg |
| **Copertina** | ✅ incorporata da mutagen | ✅ allegata da yt-dlp |
| **Capitoli del video** | ✅ FFmpeg | ✅ FFmpeg |
| **Testo karaoke** | ✅ nel tag `©lyr` | ❌ il Matroska non ha un campo equivalente |

Nel dettaglio: il postprocessor `FFmpegMetadata` scrive titolo, autore, data e capitoli durante il merge, l'unica via per il Matroska, che mutagen non sa taggare. **Album e numero di traccia** non stanno nell'info di yt-dlp (li ricaviamo noi dalla playlist), quindi vengono passati a ffmpeg come argomenti espliciti: senza, un video di playlist perderebbe proprio i due campi che tengono insieme una raccolta. Per l'`mp4` interviene poi `_tag_m4a` come per l'audio, aggiungendo copertina e testo.

> ⚠️ **Attenzione allo spazio**: un video pesa da **20 a 100 volte** più del solo audio. Una playlist da 20 brani passa da ~70 MB a diversi GB.

### 4. Parallelismo e avanzamento

I download girano su un `ThreadPoolExecutor` (default 3 thread). Un *progress hook* di yt-dlp fa da ponte verso le barre Rich: ogni blocco scaricato aggiorna la barra del singolo file con i byte ricevuti, mentre la barra complessiva avanza al completamento di ogni traccia. I risultati vengono ricomposti nell'ordine originale delle entry (i thread terminano in ordine sparso).

### 5. Anti-duplicati e retry

- Prima di scaricare, il titolo, sanificato dai caratteri vietati di Windows, dai "sosia" Unicode che yt-dlp usa al loro posto e dalle emoji, viene confrontato con i file già presenti nella cartella: se esiste un file valido (>10 KB), la traccia è marcata `skip`. Il confronto avviene **tra formati dello stesso tipo**: un `.m4a` già scaricato non fa saltare lo stesso titolo richiesto in video, e viceversa.
- Il nome del file scaricato viene poi ripulito allo stesso modo: niente emoji né caratteri a tutta larghezza (es. `⧸ ： ｜`), così i brani si copiano sul telefono via cavo USB senza errori.
- In caso di errore si riprova fino a **4 volte** con backoff esponenziale + jitter casuale, per non riprovare a raffica e non sincronizzare i retry dei vari thread.

---

### Copertina e volume, in automatico

Due cose succedono da sole a ogni download, senza opzioni da ricordare.

**La copertina esce quadrata.** Le miniature di YouTube sono 16:9, ma i lettori mostrano la copertina in un quadrato: o la schiacciano o la tagliano dove capita, spesso a metà faccia, o togliendo il titolo che sta ai bordi. AudioDex mette l'immagine **intera** al centro di un quadrato riempito da una sua copia sfocata e ingrandita: non si perde niente, e non restano le bande nere che in una griglia di copertine saltano all'occhio. Costa 0,4 secondi.

**Il volume viene misurato e annotato nei tag.** Una playlist YouTube ha salti di 9-10 LU fra un brano e l'altro. AudioDex misura ogni file secondo lo standard EBU R128 e scrive nei tag di quanto il lettore deve alzare o abbassare: `replaygain_track_gain` e `replaygain_track_peak`, nella forma che VLC e foobar2000 cercano.

**L'audio non viene toccato.** Sono due tag: nessuna ricodifica, nessuna perdita, e si disfa cancellandoli. La misura costa 2,3 secondi su un brano di quattro minuti, contro i 10-30 del download stesso: si perde nel rumore.

> 🎧 **Non tutti i lettori li leggono.** Nei file `.m4a` questi tag non sono standardizzati come nei FLAC o negli MP3. VLC, mpv e foobar2000 li usano; l'app Musica di Apple ha un suo campo diverso (`iTunNORM`); alcune autoradio li ignorano. Scriverli non costa e non rompe niente, ma non aspettarti che funzioni ovunque: se ascolti soprattutto su CD, è `BurnDex` a livellare davvero, applicando il guadagno all'audio inciso.

---

## 📀 Album interi divisi in tracce

Moltissimi caricamenti sono **"Full Album"**: un unico video da tre quarti d'ora con i capitoli scritti da chi ha caricato. AudioDex li riconosce e, se glielo chiedi, li taglia nelle singole tracce, **senza ricodificare**, quindi in pochi secondi e senza perdere un bit.

### Il punto non è tagliare: è capire *se* tagliare

Su YouTube i capitoli servono a tutto. Un tutorial ne ha cinque, una recensione tre, un'intervista li usa per le domande: dividere un video di dieci minuti in cinque spezzoni da due non fa piacere a nessuno. Perché AudioDex proponga la divisione devono reggere **tutti** questi criteri:

| Criterio | Soglia | Perché |
|---|---|---|
| Numero di capitoli | **≥ 3** | con due è quasi sempre "intro + resto" |
| Durata del video | **≥ 10 min** | sotto, per lungo che sembri, non è un disco |
| Durata dei capitoli | **≥ 30 s** per almeno l'80% | sotto sono segnaposto, non brani |
| Copertura | i capitoli coprono **≥ 80%** del video | se ne coprono un terzo, indicizzano un pezzo, non l'insieme |
| Ordine | tempi crescenti e non sovrapposti | se i dati sono incoerenti, tagliare alla cieca produce tracce accavallate |

Se anche uno solo non regge, **non viene chiesto niente**: le domande inutili si imparano a ignorare, comprese quelle che contano.

Quando invece regge tutto:

```
Questo sembra un disco: 8 capitoli, in media 2:10 l'uno.
   1. Apertura  2:10
   2. Il secondo brano  2:10
   3. Interludio: pioggia  2:10
  … e altri 5

Lo divido nelle sue tracce? (s/n — il file intero resta comunque):
```

### Cosa ottieni

Una cartella col titolo del video, con dentro le tracce **numerate e taggate**:

```
risultati/musica/
├── Gruppo di Prova - Disco Finto Completo (Full Album).m4a   ← il file intero, resta
└── Gruppo di Prova - Disco Finto Completo (Full Album)/
    ├── 01 - Apertura.m4a
    ├── 02 - Il secondo brano.m4a
    └── …
```

Ogni traccia porta **titolo** (dal capitolo), **album** (dal titolo del video), **numero di traccia** e copertina. La cartella è già nella forma che si aspetta BurnDex: si può masterizzare direttamente, e l'ordine sul CD sarà quello giusto.

Il **file intero resta** e sta *fuori* dalla cartella delle tracce, di proposito: BurnDex scandisce una cartella intera, e trovarci dentro anche l'album da 45 minuti significherebbe ritrovarselo in scaletta come traccia da masterizzare.

### Come si comanda

| | Cosa fa |
|---|---|
| *(niente, in modalità interattiva)* | chiede, ma **solo** se i criteri reggono |
| `--split` | divide sempre che i criteri reggano, senza chiedere |
| `--no-split` | non chiede e non divide mai |
| `--url` / `--search` senza `--split` | non divide: non c'è nessuno a rispondere, e riorganizzare cartelle a sorpresa dentro uno script non si fa |

> ✂️ **Sui video il taglio si aggancia al fotogramma chiave.** In copia non si può tagliare a metà di un gruppo di immagini compresse insieme, quindi l'inizio può scostarsi di qualche secondo. Sull'audio la granularità è di millisecondi e non si nota. Del resto nemmeno i capitoli scritti a mano su YouTube sono precisi al fotogramma.

> 🗃 **Le tracce ricavate non finiscono nel database globale**: resta registrato il file di origine, che è ciò che è stato effettivamente scaricato.

---

## 🔢 L'ordine delle tracce

### Il problema

I download partono in parallelo su più thread e finiscono in **ordine sparso**: la traccia 7, più leggera, può completarsi prima della 2. Se i file venissero salvati con il solo titolo, la cartella li mostrerebbe in **ordine alfabetico**, e un album ascoltato dal telefono partirebbe da un brano a caso.

Il tag `trkn` (numero di traccia) da solo non basta: molti lettori da telefono, e la semplice esplorazione della cartella via USB, ordinano **per nome file**.

### Come viene risolto

Per le playlist il numero di traccia entra **nel nome del file**, zero-padded:

```
risultati/musica/Molchat Doma - Etazhi/
├── 01 - Na Dne.m4a
├── 02 - Tantsevat.m4a
├── 03 - Volny.m4a
└── ...
```

Così l'ordine alfabetico **coincide** con quello della playlist, ovunque tu apra la cartella. Le cifre si adattano alla dimensione della playlist: una raccolta da 150 brani usa tre cifre (`007 - …`), così anche lì l'ordinamento resta corretto.

> Il prefisso viene aggiunto **solo alle playlist**. Un video singolo o una selezione da ricerca non hanno un "ordine" da preservare, quindi conservano il nome pulito.

### Selezioni parziali e playlist con buchi

Il numero usato è quello della **playlist di origine**, non la posizione nella lista scaricata:

- scarichi solo le tracce **5-8** di un album → i file escono `05`, `06`, `07`, `08`, non `01`-`04`, e si incastrano con quelli già in cartella;
- la playlist contiene un video **privato o rimosso** → viene saltato, ma le tracce successive **non scalano** di posizione: la numerazione resta fedele all'originale.

### Numerazione dei file già scaricati

Il controllo anti-duplicati riconosce lo stesso brano anche se sul disco è **senza numero**, perché scaricato con una versione precedente del programma. In quel caso il file viene semplicemente **rinominato**, non riscaricato:

```
Na Dne.m4a  →  01 - Na Dne.m4a
```

Rilanciando lo stesso comando su una vecchia cartella, quindi, la numerazione si allinea **senza consumare banda**.

> ⚠️ **Un file che ha già un numero non viene mai rinominato**, nemmeno se la playlist è stata riordinata: in quel caso la traccia viene riscaricata con il numero nuovo e il vecchio file resta lì (puoi cancellarlo a mano).
>
> Il motivo è che una playlist può contenere **due tracce con lo stesso titolo**, succede spesso, es. lo stesso brano in versione singolo e in versione album. Riconoscendo "stesso titolo, numero qualsiasi", le due tracce si contenderebbero **lo stesso file**, rinominandolo a vicenda: ne resterebbe uno solo e la seconda non verrebbe mai scaricata. Meglio un file di troppo che una traccia persa.

---

## 🧾 Tagging dei metadati

Dopo il download, ogni file `.m4a` viene taggato con **mutagen** usando i tag standard iTunes (i file `.m4a` usano il container MP4):

| Tag | Contenuto | Fonte |
|---|---|---|
| `©nam` | Titolo | Metadati YouTube |
| `©ART` | Artista | Campo `artist` o, in mancanza, il nome del canale |
| `©alb` | Album | Nome della playlist (o campo `album` di YouTube) |
| `trkn` | Numero traccia | Posizione nella playlist di origine |
| `covr` | Copertina | Thumbnail del video, scaricata e incorporata (JPEG/PNG) |
| `©lyr` | Testo | LRCLIB, formato LRC con timestamp (vedi capitolo 10) |

Gli stessi tag vengono scritti nei video **`.mp4`**, che condividono il container MP4 con l'`.m4a`. Per i **`.mkv`** i metadati li scrive FFmpeg durante il merge (vedi [7.3](#3-download-audio-o-video)).

> Se mutagen non è installato il tagging viene semplicemente saltato: i file restano validi, solo senza metadati.

---

## 🎵 Testi sincronizzati (karaoke)

Dopo ogni download riuscito, il programma interroga **[LRCLIB](https://lrclib.net)** (API gratuita, senza chiave) con artista, titolo e durata della traccia. Se il testo esiste, viene **incorporato direttamente nel tag `©lyr` del file m4a**, in formato LRC con i timestamp: il brano resta **un file unico** che porta con sé anche il testo, su PC come su telefono.

I lettori che leggono il testo dai tag (**Musicolet**, **Oto Music**, **AIMP**, **Samsung Music** su Android; **MusicBee**, **foobar2000**, **AIMP** su PC) lo mostrano **riga per riga in stile karaoke**; quelli più basilari lo mostrano come testo statico.

Esempio del testo incorporato:

```
[00:18.98] We're no strangers to love
[00:22.55] You know the rules and so do I (do I)
[00:26.99] A full commitment's what I'm thinking of
```

Dettagli del funzionamento:

- il titolo YouTube viene **ripulito** dalle decorazioni (`(Official Video)`, `[HD]`, `(Lyrics)`, …) prima della ricerca, e i titoli nel formato `Artista - Brano` vengono separati nei due campi;
- prima si tenta la **corrispondenza esatta** artista + titolo + durata, poi una ricerca libera scartando i risultati con durata troppo diversa (>10 s: probabilmente live o remix);
- il testo pesa **pochi KB** (~0,1% dell'audio): l'impatto sulla dimensione del file è trascurabile;
- se il testo non esiste o la rete fallisce **non succede nulla**: i testi sono un extra, mai un motivo di fallimento del download;
- il riepilogo finale mostra quante tracce hanno ottenuto il testo (`♫ Testi karaoke`);
- per disattivare la ricerca: `--no-lyrics`.

---

## 💾 Formati di output

| Formato | Container | Note |
|---|---|---|
| `m4a` ⭐ *(default)* | MP4/AAC | Qualità nativa di YouTube, **nessuna ricodifica** (rimux), supporta tag e copertina via mutagen |
| `mp3` | MPEG | Massima compatibilità con dispositivi datati; richiede ricodifica (lieve perdita teorica) |
| `opus` | Ogg/Opus | Massima efficienza qualità/dimensione; supporto dispositivi meno diffuso |
| `mp4` ⭐ *(video)* | MP4/H.264 | Il default per `--media video`: nessuna ricodifica e **tag completi** (titolo, artista, album, traccia, copertina, testo) come l'`m4a` |
| `mkv` *(video)* | Matroska | Container più permissivo, utile quando i flussi migliori non stanno in un mp4. Tag e copertina ci sono, scritti da FFmpeg; manca solo il **testo karaoke**, che nel Matroska non ha un campo equivalente |

> 💡 **Consiglio:** lascia `m4a` se non hai esigenze particolari, è il formato in cui YouTube serve l'audio, quindi non c'è alcuna conversione né perdita. Per il video vale lo stesso con `mp4`.

> 🔎 **Il flusso scaricato dipende dal formato richiesto.** La tabella `AUDIO_SOURCE_FORMATS` associa a ogni formato di uscita il codec da chiedere a YouTube: `m4a` → AAC (itag 140), `opus` → Opus (itag 251), `mp3` → il flusso migliore disponibile. Quando sorgente e destinazione coincidono, FFmpeg cambia solo il contenitore e **ricopia l'audio byte per byte**. Prima si scaricava sempre l'AAC: chiedere `--format opus` significava scaricare AAC e poi ricomprimerlo in Opus, cioè **due compressioni con perdita in cascata**.

---
