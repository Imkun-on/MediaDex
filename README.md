
<div align="center">

# 🎧 MediaDex

<b>AudioDex</b> · <b>BurnDex</b> · <b>PixDex</b> · <b>ClipDex</b><br>
<i>quattro strumenti, una finestra sola</i>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/yt--dlp-downloader-FF0000?logo=youtube&logoColor=white" alt="yt-dlp">
  <img src="https://img.shields.io/badge/FFmpeg-richiesto-007808?logo=ffmpeg&logoColor=white" alt="FFmpeg">
  <img src="https://img.shields.io/badge/pywebview-6.2-2C5BB4?logo=python&logoColor=white" alt="pywebview">
  <img src="https://img.shields.io/badge/WebView2-già_nel_sistema-0078D4?logo=microsoftedge&logoColor=white" alt="WebView2">
  <img src="https://img.shields.io/badge/Rich-TUI-4EC820?logo=windowsterminal&logoColor=white" alt="Rich">
  <img src="https://img.shields.io/badge/SQLite-WAL-003B57?logo=sqlite&logoColor=white" alt="SQLite">
  <img src="https://img.shields.io/badge/IMAPI2-COM_nativa-0078D4?logo=windows&logoColor=white" alt="IMAPI2">
  <img src="https://img.shields.io/badge/Red_Book-CD--DA_44.1kHz_16bit-C0392B?logo=audiomack&logoColor=white" alt="Red Book">
  <img src="https://img.shields.io/badge/LRCLIB-testi_karaoke-8B5CF6?logo=musicbrainz&logoColor=white" alt="LRCLIB">
  <img src="https://img.shields.io/badge/Inno_Setup-installatore-264653?logo=windows11&logoColor=white" alt="Inno Setup">
</p>

<p align="center">
  Cerca brani su <b>YouTube</b> e scaricane il <b>solo flusso audio</b>, o il <b>video intero</b>:<br>
  file di pochi MB, <b>qualità originale</b>, nessuna ricodifica. Ogni traccia arriva già<br>
  <b>taggata</b> (titolo, artista, album, copertina) e con il <b>testo sincronizzato</b><br>
  dentro il file, pronta da copiare sul telefono.<br>
  Poi la incidi su un <b>CD audio vero</b>, rimasterizzi un vecchio video, o lo tagli.<br>
  <b>Niente account, niente pubblicità, niente limiti di durata.</b>
</p>

<br>

<a href="https://github.com/Imkun-on/MediaDex/releases/latest/download/MediaDex-Setup.exe">
  <img src="https://img.shields.io/badge/⬇_Scarica_MediaDex--Setup.exe-39FF88?style=for-the-badge&labelColor=0b160d&color=39FF88&logoColor=black" alt="Scarica MediaDex">
</a>

<sub>Windows 10 o successivo · non servono permessi di amministratore</sub>

</div>

---

## 📖 Indice

- [Installa l'app](#-installa-lapp)
- [Cosa fa](#-cosa-fa)
- [I quattro strumenti](#-i-quattro-strumenti)
- [Requisiti](#-requisiti)
- [Dalla riga di comando](#-dalla-riga-di-comando)
- [Com'è fatto dentro](#-comè-fatto-dentro)
- [Per sviluppatori](#-per-sviluppatori)
- [Privacy](#-privacy)
- [Note legali](#-note-legali)
- [Licenza](#-licenza)

---

## 📥 Installa l'app

1. Scarica **[`MediaDex-Setup.exe`](https://github.com/Imkun-on/MediaDex/releases/latest/download/MediaDex-Setup.exe)**
2. Doppio clic, avanti, fine
3. Installa **FFmpeg**, una volta sola:

   ```powershell
   winget install Gyan.FFmpeg
   ```

> 🔓 **Niente amministratore.** MediaDex si installa in
> `%LOCALAPPDATA%\Programs\MediaDex`, che è tuo. Non è una scorciatoia per
> evitare l'UAC: il programma scrive accanto a sé stesso — i brani, i log, il
> database — e dentro «Programmi» non potrebbe.

> 🌐 **WebView2** disegna l'interfaccia. C'è già da Windows 10 in poi; se manca,
> l'installatore lo scarica da Microsoft prima di procedere.

> ⏳ **Le prime aperture sono lente.** È Windows Defender che scansiona per la
> prima volta i file appena installati: lo fa una volta sola. Dopo, MediaDex
> mostra la sua schermata di caricamento in un paio di secondi e l'interfaccia
> poco dopo.

<details>
<summary><b>🛡️ Windows dice «non viene scaricato di frequente». È un virus?</b></summary>

<br>

**No, e Windows non sta dicendo che lo sia.** Quella frase è esattamente ciò che
afferma: questo file è nuovo e poche persone lo hanno scaricato. Il controllo si
chiama **SmartScreen** e non guarda dentro il file, guarda quanto è *conosciuto*. Lo
stesso avviso comparirebbe su un eseguibile perfettamente innocuo, come questo, e non
comparirebbe su un malware diffuso da mesi.

Sparisce da solo in due modi, e nessuno dei due dipende da cosa c'è nel programma:
quando abbastanza persone lo scaricano senza segnalarlo, oppure se l'eseguibile viene
**firmato** con un certificato di code signing — da un centinaio di euro l'anno per
uno OV, che comunque richiede di accumulare reputazione. Per un progetto non
commerciale, pagare un certificato per far sparire un avviso non ha molto senso.

**Come procedere:** nella barra dei download, `···` → **Mantieni** → **Mantieni
comunque**. Poi, se compare la finestra blu: **Ulteriori informazioni** → **Esegui
comunque**.

**Se preferisci verificare invece che fidarti** — ed è la scelta giusta con qualunque
eseguibile preso da internet:

```powershell
Get-FileHash .\MediaDex-Setup.exe -Algorithm SHA256
```

L'impronta deve coincidere con quella pubblicata nelle note della
[Release](https://github.com/Imkun-on/MediaDex/releases/latest). Se coincide, il file
che hai è bit per bit quello costruito da questi sorgenti. In alternativa puoi
caricarlo su [VirusTotal](https://www.virustotal.com/), o saltare del tutto
l'eseguibile e partire dai sorgenti: è lo stesso programma.

</details>

### Dove finiscono i tuoi file

Tutto accanto al programma, dove lo ritrovi aprendo la cartella:

```
%LOCALAPPDATA%\Programs\MediaDex\
├── risultati\
│   ├── musica\            i brani scaricati, una cartella per playlist
│   ├── rimasterizzati\    i video rifatti, col confronto prima/dopo
│   └── montaggi\          spezzoni, unioni, GIF e provini
├── logs\                    cosa è successo, sezione per sezione
└── Database_Globale\        il registro di cosa hai già scaricato
```

Non te lo chiede mai: c'è un posto solo, e in fondo alla barra laterale il
bottone **Apri la cartella dei risultati** ti ci porta.

### Aggiornare e disinstallare

Per aggiornare, scarica la versione nuova e installala sopra: riconosce quella
vecchia e la sostituisce. I tuoi file restano dove sono.

Disinstallando, MediaDex **chiede** prima di cancellare i brani scaricati.
Rispondendo No restano dove sono, e li ritrovi se reinstalli.

---

## 🎯 Cosa fa

Quattro mestieri che si incastrano, e che si usano anche uno alla volta.

1. **Cerchi** un brano per nome, o incolli il link di un video o di una playlist
2. **Scegli** cosa scaricare fra i risultati — le schede si spuntano una per una
3. **Scarichi**: solo audio (`m4a`, `mp3`, `opus`) o il video intero (`mp4`, `mkv`),
   più file insieme, con la barra di ciascuno
4. Ogni traccia arriva **taggata**, con **copertina** e **testo sincronizzato**
   dentro il file, e col nome pulito — niente emoji che il telefono rifiuta
5. Da lì la **incidi su CD**, oppure passi a **rimasterizzare** un vecchio video o
   a **tagliarlo**

Un album caricato su YouTube come video unico viene riconosciuto e **diviso in
tracce** dai suoi capitoli — ma solo quando ha davvero senso: la decisione e i
criteri sono spiegati in [docs/audiodex.md](docs/audiodex.md).

---

## 🧰 I quattro strumenti

| | Cosa fa | Dove si legge | Sistema |
|---|---|---|---|
| 🎧 **AudioDex** | Cerca su YouTube e scarica: audio o video, singoli o playlist intere, con tag, copertina e testo karaoke | [docs/audiodex.md](docs/audiodex.md) | ovunque |
| 💿 **BurnDex** | Trasforma una cartella di brani in un CD audio vero (Red Book CD-DA), leggibile da qualsiasi autoradio | [docs/burndex.md](docs/burndex.md) | solo Windows |
| 🎞 **PixDex** | Rimasterizza un video: toglie i difetti della compressione, appiana le bande, ingrandisce quando serve | [docs/pixdex.md](docs/pixdex.md) | ovunque |
| ✂ **ClipDex** | Taglia, unisce, converte: spezzoni, montaggi con capitoli, GIF, provini, ricodifiche per apparecchi datati | [docs/clipdex.md](docs/clipdex.md) | ovunque |

BurnDex è l'unico legato a Windows, e per una ragione precisa: incide passando
da **IMAPI2**, l'API nativa di sistema, invece di dipendere da un programma di
masterizzazione esterno.

---

## 📦 Requisiti

Se usi l'installatore, l'unica cosa che devi mettere tu è **FFmpeg**.

| | Serve per | Come si installa |
|---|---|---|
| **FFmpeg** | Tutto: convertire, decodificare, tagliare, ricodificare | `winget install Gyan.FFmpeg` |
| **WebView2** | Disegnare l'interfaccia | C'è già da Windows 10; l'installatore lo scarica se manca |
| **Python 3.10+** | *Solo* se parti dai sorgenti | [python.org](https://www.python.org/downloads/) |

Su macOS e Linux, FFmpeg si mette con `brew install ffmpeg` o
`sudo apt install ffmpeg`. Lì funzionano AudioDex, PixDex e ClipDex da riga di
comando; BurnDex no, e lo dice.

### Dai sorgenti

```bash
git clone https://github.com/Imkun-on/MediaDex.git
cd MediaDex
pip install -r requirements.txt
python MediaDex.py
```

> 🎞️ Lo **sfondo animato** della finestra sono venti righe di CSS e non pesa
> niente. Se metti un file video in `assets/cyberpunk-citadel.mp4`, viene usato
> quello; se non c'è — ed è il caso normale — restano i gradienti verdi, che
> non sono un ripiego mesto ma uno sfondo a sua volta guardabile.

---

## ⌨️ Dalla riga di comando

Gli stessi quattro motori, senza finestra:

```bash
python -m cli                  # elenca i mestieri
python -m cli audio            # cerca e scarica
python -m cli burn --info      # che masterizzatore c'è, e cosa c'è dentro
python -m cli pix --info       # diagnosi di un video, senza rimasterizzarlo
python -m cli clip taglia --input video.mp4 --from 1:20 --to 3:45
```

Ognuno ha il proprio `--help` con le proprie opzioni. Lanciati senza argomenti,
tutti e quattro fanno domande: è il modo in cui si usano quando non si sa
ancora cosa si vuole.

Non è una versione ridotta della finestra: è **lo stesso motore**. `server/` non
sa chi lo sta guardando, ed è la regola su cui è costruito tutto il resto.

---

## 🧩 Com'è fatto dentro

```
MediaDex/
├── MediaDex.py            apre la finestra, e nient'altro
├── client/                l'interfaccia: una pagina web dentro Windows
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
└── docs/                  la documentazione lunga
```

**Le dipendenze vanno solo verso il basso** di quell'elenco: `controllers` può
chiamare `services`, `services` può chiamare tutti, `config` non chiama
nessuno. Al contrario mai.

**`server/` non importa mai niente da `cli/`** e non sa che la pagina esiste. Il
lavoro non sa chi lo sta guardando: per questo lo stesso motore serve la
finestra e il terminale.

**Nella pagina non si decide niente.** `client/` raccoglie quello che si scrive,
lo passa a Python e mostra la risposta. Ogni scelta vera — se un URL sia una
playlist, quale risoluzione abbia senso, se un ordine di tracce ci stia su un
CD — sta nei motori, dove è una risposta sola.

→ Il dettaglio, compreso come parlano fra loro i due mondi e dove finisce quello
che va storto: **[docs/architettura.md](docs/architettura.md)**.

---

## 🔧 Per sviluppatori

| Pagina | Cosa contiene |
|---|---|
| [docs/architettura.md](docs/architettura.md) | Gli strati, il ponte JS↔Python, la gestione degli errori, le librerie |
| [docs/costruire.md](docs/costruire.md) | Da sorgenti a `MediaDex-Setup.exe`, e da lì a una Release |
| [docs/database.md](docs/database.md) | Lo schema SQLite condiviso dei download |
| [docs/changelog.md](docs/changelog.md) | Lo storico delle versioni |

### Costruire l'installatore

```powershell
winget install JRSoftware.InnoSetup    # una volta sola
.\costruisci.ps1 -Versione 1.0.0
```

PyInstaller fa la cartella eseguibile, Inno Setup ne fa un installatore. Alla
fine lo script stampa dove è finito, quanto pesa e la sua impronta SHA256.

> ⚠️ MediaDex scrive **accanto a sé stesso**. Se hai provato l'eseguibile da
> `dist\`, lì dentro sono rimasti i tuoi brani e i tuoi log: il passo 2 di
> `costruisci.ps1` te lo dice e si offre di cancellarli, perché altrimenti
> finirebbero dentro l'installatore.

### Pubblicare una versione

```bash
git tag v1.0.0 && git push --tags
```

Il resto lo fa GitHub Actions, lanciando **lo stesso `costruisci.ps1`**.

---

## 🔒 Privacy

- Non c'è nessun account, nessuna registrazione e nessuna chiave da inserire
- Niente esce da questo computer se non le richieste a YouTube (via yt-dlp) e
  quelle a [LRCLIB](https://lrclib.net) per i testi, che non chiedono chi sei
- Il database dei download, i log e la lingua scelta restano in locale, accanto
  al programma
- Non c'è telemetria, non c'è un server, non c'è una porta aperta

---

## 📜 Note legali

MediaDex scarica contenuti da YouTube. L'uso potrebbe essere soggetto ai
[Termini di Servizio di YouTube](https://www.youtube.com/t/terms) e alle norme
sul **diritto d'autore** della tua giurisdizione. È pensato per uso **personale
ed educativo** — ascoltare offline musica di cui hai i diritti — e va usato in
modo responsabile, solo per contenuti di cui hai il diritto di fruire.

Lo stesso vale per **BurnDex**: masterizzare su CD è un atto di copia, e in
molte giurisdizioni la copia privata è ammessa solo a partire da contenuti di
cui si ha legittimamente il diritto di fruire, per uso personale e senza fini di
lucro. Verifica cosa prevede la normativa del tuo paese.

Le librerie utilizzate (yt-dlp, Rich, pywebview, mutagen, requests, pywin32)
sono distribuite con le rispettive licenze open source.

---

## 📄 Licenza

Rilasciato sotto **[PolyForm Noncommercial License 1.0.0](LICENSE)**.

In breve. **Non è un riassunto legale: fa fede il testo della licenza.**

- ✅ **Puoi** usare, studiare, modificare e ridistribuire MediaDex per **scopi
  non commerciali**: uso personale, ricerca, progetti hobbistici, e uso da parte
  di **enti caritatevoli o educativi** (scuole, università).
- ❌ **Non puoi** usarlo per scopi commerciali: venderlo, offrirlo come servizio
  a pagamento, o usarlo nell'attività di un'azienda.
- 📎 Se lo ridistribuisci, devi **allegare la licenza** (o il suo URL) e
  mantenere la riga `Required Notice:`.

> Serve un uso commerciale? Scrivimi: una licenza separata è negoziabile.
