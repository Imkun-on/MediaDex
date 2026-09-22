# Il database globale dei download

Un registro SQLite condiviso fra piu' scraper: cosa e' stato scaricato, quando,
dove e' finito. Serve a non riscaricare due volte la stessa cosa e a ritrovare
un file mesi dopo.

> Torna al [README](../README.md).

---

## 📊 Database globale

Ogni download riuscito viene registrato in `Database_Globale/scraper_metadata.db`, un database SQLite **condiviso tra più scraper** con un'unica tabella `downloads`:

- **Campi comuni**: tipo di scraper, tipo di media (`audio`/`video`), ID sorgente, titolo, URL, percorso file (relativo, così sopravvive agli spostamenti della cartella), dimensione, data ISO 8601
- **Campi audio**: artista, durata, formato, numero traccia, album

Dettagli tecnici:

- 🧵 **Una connessione per thread** (`threading.local`): sqlite3 vieta di condividere la stessa connessione tra thread diversi, e le scritture arrivano dai thread di download
- ⚡ **Modalità WAL**: letture e scritture concorrenti senza blocchi reciproci
- ♻️ **`INSERT OR REPLACE`** sul vincolo `UNIQUE(scraper_type, source_id, media_kind)`: riscaricare la stessa traccia **nello stesso formato** aggiorna la riga esistente invece di duplicarla, mentre la versione **audio** e quella **video** dello stesso video YouTube convivono come due righe, sono due file distinti sul disco
- 🔄 **Migrazione automatica**: i database creati prima dell'arrivo del download video hanno la vecchia chiave `UNIQUE(scraper_type, source_id)`, che SQLite non sa modificare con un `ALTER TABLE`. Al primo avvio la tabella viene **ricostruita** e i dati ricopiati, dentro un'unica transazione e dopo una **copia di sicurezza** del file (`scraper_metadata.db.backup-pre-media-kind`). Le righe storiche vengono etichettate come `audio`. Se qualcosa va storto la migrazione si annulla e i dati restano intatti
- 🛡️ **Errori mai bloccanti**: il database è un registro accessorio, un suo problema viene loggato come warning e non interrompe mai i download

---
