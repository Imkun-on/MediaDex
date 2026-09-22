# Com'è fatto dentro

Le cartelle, la regola che le tiene in ordine, e come parlano fra loro i due
mondi. Se stai leggendo per capire dove mettere una cosa nuova, è questa la
pagina.

> Torna al [README](../README.md).

---

## L'alberatura

```
MediaDex/
├── MediaDex.py            apre la finestra, e nient'altro
├── client/                l'interfaccia: una pagina web dentro Windows
│   ├── index.html         le quattro sezioni
│   ├── app.js             nucleo: testi, sezioni, avanzamento, avvisi
│   ├── components/        pezzi riusabili: tendine, finestra modale
│   ├── features/          una per sezione: audio, burn, pix, clip
│   └── styles/            il tema, verde marcio su nero
├── cli/                   le quattro interfacce da terminale
├── server/                il motore: tutto quello che sa fare
│   ├── config/            le manopole, i testi, i percorsi
│   ├── utils/             gli attrezzi buoni per tutti
│   ├── sources/           da dove arriva la roba: YouTube, testi, copertine
│   ├── audio/             cosa si fa a un file audio
│   ├── burn/              cosa si fa a un CD
│   ├── video/             cosa si fa a un filmato
│   ├── state/             cosa sopravvive al singolo gesto
│   ├── services/          il direttore d'orchestra
│   └── controllers/       il filo con la pagina
├── installer/             MediaDex.iss, per Inno Setup
├── docs/                  questa cartella
├── assets/                icona e marchio
├── costruisci.ps1         PyInstaller + Inno Setup, in un comando
└── MediaDex.spec          come impacchettare
```

E accanto, create quando servono e mai versionate:

```
risultati/                 tutto quello che il programma produce
├── musica/                i brani scaricati, una cartella per playlist
├── rimasterizzati/        i video rifatti da PixDex, col confronto prima/dopo
└── montaggi/              spezzoni, unioni, GIF e provini
logs/                      audiodex.log, burndex.log, pixdex.log, clipdex.log
Database_Globale/          il registro SQLite dei download
```

Non si sceglie dove salvare, e infatti la finestra non lo chiede. C'era un
campo con un bottone «sfoglia» da riempire prima di poter premere Scarica, e
PixDex e ClipDex scrivevano accanto al file di partenza, cioè sparsi per il
disco dovunque fosse l'originale. Adesso c'è un posto, le sottocartelle si
creano da sole al primo file, e in fondo alla barra laterale c'è il bottone che
le apre.

Da riga di comando la scelta resta, ed è giusto: `--output` e `--base`
esistono ancora, con questi come valori predefiniti. Chi lancia
`clip taglia` su un video in una cartella sua si aspetta lo spezzone lì.

---

## Le tre regole

### 1. Le dipendenze vanno solo verso il basso

L'elenco delle cartelle di `server/` qui sopra è anche il loro ordine:
`config` sta in fondo e non chiama nessuno, `controllers` sta in cima e può
chiamare tutti. Al contrario mai.

Il giorno in cui `server/burn/` importasse `server/services/` si chiuderebbe un
cerchio, e da quel momento non si potrebbe più leggere un modulo senza averne
aperti altri due. È la differenza fra una pila di strati e un groviglio, e si
mantiene solo rifiutandola ogni volta.

### 2. `server/` non sa che la pagina esiste

E non importa **mai** niente da `cli/`. Il lavoro non sa chi lo sta guardando:
per questo lo stesso motore serve la finestra e il terminale, e per questo
aggiungere una terza interfaccia non vorrebbe dire riscrivere niente.

C'è una sola eccezione, ed è dichiarata: `server/services/burn.py` parla con un
terminale. Il motivo sta scritto in cima a quel file — la procedura di
masterizzazione è una sola e i due modi di usarla differiscono solo in quanto
viene chiesto, quindi averne due copie sarebbe più pericoloso che avere questa
irregolarità in una sola.

### 3. Nella pagina non si decide niente

`client/` raccoglie quello che si scrive, lo passa a Python, e mostra quello
che Python risponde. Ogni scelta vera — se un URL sia una playlist, quale
risoluzione abbia senso, se un ordine di tracce ci stia su un CD — sta già nei
motori. Duplicarla nella pagina significherebbe due risposte diverse alla
stessa domanda, e prima o poi due risposte diverse le dai davvero.

---

## Come parlano i due mondi

In una sola direzione ciascuno, ed è questo che tiene il tutto semplice.

**Dalla pagina a Python** ci pensa pywebview da solo: ogni metodo pubblico di
`Api` (in `server/controllers/api.py`) diventa
`window.pywebview.api.<nome>()`, e la risposta torna come promessa. Nessun
protocollo, nessun server, nessuna porta aperta.

**Da Python alla pagina** no: non esiste un canale, esiste solo «esegui questa
riga di JavaScript». `bridge.verso_pagina(...)` è quella riga, ed è l'unico
posto del programma in cui si chiama `evaluate_js`.

### L'indirizzo viaggia per primo

Ogni sezione della pagina ha la sua barra di avanzamento, la sua spia e la sua
parola di stato: un messaggio che non dica a chi è diretto non sa più dove
andare.

L'indirizzo non si passa di mano in mano — vorrebbe dire aggiungere un
argomento a trenta chiamate, e ricordarselo ogni volta che se ne aggiunge una.
Sta invece nel **thread**, perché il thread *è* la risposta: un lavoro alla
volta, e ogni lavoro appartiene alla sezione che lo ha chiesto. Lo scrive
`bridge.entra()`, prima riga di ogni metodo che la pagina può chiamare.

Lato pagina c'è una porta sola, `window.__instrada(dove, nome, argomenti)`, e
gli ascoltatori si registrano con `ascolta(nome, funzione)`. Ogni gestore
riceve la sezione come primo argomento.

---

## Dove finisce quello che va storto

Non c'è una scheda dei log dentro la finestra, ed è una scelta: finché c'era,
un errore era una riga rossa in mezzo ad altre duecento, e su un download da
cinquanta brani si perdeva davvero.

Al suo posto, due destinazioni e una regola netta:

| Cosa | Dove va |
|---|---|
| Un rifiuto immediato (cartella vuota, link non valido, nessuna traccia scelta) | **Avviso** in basso a destra, quattro secondi |
| Un lavoro che cade **dopo** essere partito | **Finestra**, con la causa in italiano e il testo tecnico sotto |
| Il racconto riga per riga di quello che è successo | `logs/<sezione>.log`, dove si va a cercarlo |

La causa in italiano la ricava `server/utils/contract.py`, che riconosce le
famiglie di guasti che MediaDex produce davvero — FFmpeg assente, disco pieno,
nessun masterizzatore, 403 di yt-dlp — e per ognuna dice cosa fare. Quando non
riconosce niente non inventa: dice che è andato storto qualcosa e lascia
parlare il riquadro col traceback.

Un caso a parte sono i **rifiuti spiegati** (`ErroreSpiegato`): una richiesta
che non si poteva soddisfare e che il programma sa già raccontare — un video
illeggibile, un montaggio «unisci» con un file solo. Lì la finestra mostra la
frase e basta, senza traceback: di una frase che si capisce già, il testo
tecnico sotto direbbe solo in che riga di Python è scritta.

### Da terminale

- Ogni traccia fallita finisce nel **riepilogo finale**, con il motivo nel log
- Titoli e URL delle tracce fallite vanno in **`failed_tracks.txt`** nella
  cartella di output, pronti per ritentare con `--url <URL>` senza rifare la
  ricerca
- Il logger scrive **solo su file**: righe di log a video rovinerebbero le
  barre di avanzamento live
- 🛑 **Ctrl+C**: il primo avvia l'arresto pulito (finiscono i download in
  corso, si annullano quelli in coda), il secondo forza l'uscita

---

## Perché l'interfaccia è una pagina web

Non c'è nessun motore grafico da scaricare: **WebView2 è già nel sistema**, da
Windows 10 in poi. Lo sfondo animato non è un file video da settantaquattro
megabyte ma venti righe di CSS, e pesa zero. E le cose che un'interfaccia deve
fare — bagliori, sfocature, transizioni, testo che scorre — sono esattamente
ciò per cui il CSS è nato.

Il prezzo è che l'interfaccia e il motore parlano due linguaggi diversi. Il
confine però è uno solo e sta scritto in due file (`bridge.py` e `api.py`), il
che è meno di quanto costi tenere allineati due framework grafici.

---

## Librerie usate, e perché proprio quelle

| Libreria | A cosa serve | Perché proprio questa |
|---|---|---|
| `yt-dlp` | Ricerca su YouTube ed estrazione/download del flusso audio | Lo standard de facto: gestisce stream, playlist, resume e metadati |
| `requests` | Download della copertina e chiamate a LRCLIB | Semplice e onnipresente; qui bastano due GET |
| `rich` | Interfaccia da terminale: tabelle, pannelli, barre live | Trasforma la CLI in un'esperienza curata (`Table`, `Progress`, `Live`) |
| `pywebview` | La finestra, e il ponte con la pagina | Usa il WebView già installato: non porta con sé nessun motore di rendering da distribuire |
| `mutagen` | *(opzionale)* Metadati e copertina nei file `.m4a` | Pure-python, legge/scrive i tag MP4 (iTunes) senza dipendenze esterne |
| `pywin32` | *(solo BurnDex)* Ponte verso COM: IMAPI2 per masterizzare, WMI per riconoscere il sistema | È l'unico modo di parlare con le API native di Windows da Python. Evita di dipendere da un programma di masterizzazione esterno |

### Strumento esterno (non pip)

| Strumento | A cosa serve | Note |
|---|---|---|
| **[FFmpeg](https://ffmpeg.org)** | Estrazione e conversione dell'audio; decodifica in PCM per BurnDex; tutto PixDex e ClipDex | **Obbligatorio**, da installare una volta. Con `m4a` non ricodifica: si limita al rimux |
| **ffprobe** | Lettura delle durate e delle caratteristiche senza decodificare | Incluso in FFmpeg. BurnDex lo usa per calcolare la capienza prima di impegnare il disco |

### API di sistema (nessuna installazione)

| API | A cosa serve | Note |
|---|---|---|
| **IMAPI2** | Masterizzazione dei CD audio | *Image Mastering API v2*, presente in Windows dal Vista. È la stessa che usano Esplora risorse e Windows Media Player |
| **WMI** | Tipo di computer e unità ottiche | `Win32_SystemEnclosure`, `Win32_ComputerSystem`, `Win32_CDROMDrive` |
| **WebView2** | L'interfaccia grafica | Già presente da Windows 10; l'installatore lo scarica se manca |

### Servizio esterno (nessuna chiave)

| Servizio | A cosa serve | Note |
|---|---|---|
| **[LRCLIB](https://lrclib.net)** | Testi sincronizzati (LRC) | API pubblica e gratuita, **senza registrazione né chiave**. Se non risponde, il download prosegue lo stesso |

### Libreria standard

`os`, `re`, `json`, `shutil`, `signal`, `time`, `random`, `threading`,
`sqlite3`, `tempfile`, `subprocess`, `concurrent.futures`: percorsi e file,
regex, spazio disco, gestione Ctrl+C, backoff dei retry, pool di thread,
database, file PCM temporanei e invocazione di FFmpeg.

---

## Dove stanno le cose, dentro e fuori dall'eseguibile

Due cartelle che coincidono solo quando si lavora sui sorgenti, e
`server/config/paths.py` è l'unico posto che sa distinguerle.

| | Cosa contiene | Da sorgente | Dall'eseguibile |
|---|---|---|---|
| **risorse** | La pagina, le icone: impacchettate, non cambiano mai | la radice del progetto | `_internal/` dentro l'installazione |
| **dati** | I brani, i log, il database, la lingua: sono di chi usa il programma e devono restare | la radice del progetto | accanto a `MediaDex.exe` |

È anche il motivo per cui l'installatore mette MediaDex in
`%LOCALAPPDATA%\Programs` e non in «Programmi»: il programma scrive accanto a
sé stesso, e dentro «Programmi» un utente normale non ha permesso di scrivere.

---

## I testi

Una lingua sola, l'italiano. Il catalogo è piatto — `'chiave': 'frase'` — con
chiavi puntate (`menu.audio`, `burn.title`), e vive in
`server/config/strings/`: una pagina per mestiere più quelle della finestra e
quelle degli errori.

C'è stato un menu a tendina per scegliere fra italiano e inglese, e ogni voce
del catalogo era `{'it': ..., 'en': ...}`. Il menu non c'è più: era l'unica
impostazione dell'intero programma, occupava un angolo fisso della barra
laterale, e per tenerlo in piedi servivano un metodo nell'API, un file di
preferenze accanto all'eseguibile e la riscrittura di tutta la pagina a ogni
cambio. Le traduzioni inglesi stanno nella storia di git, se un domani
servissero.

Si carica tutto insieme, al primo `t()` che qualcuno chiama. Questo ha una
conseguenza che vale la pena sapere prima di aggiungere una chiave: **due
mestieri non possono usare lo stesso nome per due frasi diverse**. Finché ogni
motore era un programma a sé la cosa non si poneva; adesso i cataloghi si
incontrano, e le chiavi che dicono cose diverse portano il cognome del mestiere
(`cli.desc.pix`, `cli.desc.clip`). Quelle che dicono davvero la stessa cosa si
fondono, ed è giusto così.

Il catalogo della pagina è un sottoinsieme: `Api.avvio()` le spedisce in un
colpo solo all'apertura, e il JavaScript ha la stessa `t()` con lo stesso
ripiego — una chiave che manca torna com'è, visibile a schermo, invece di far
saltare qualcosa.
