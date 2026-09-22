"""Database SQLite globale dei download per gli scraper Audio, Manga e Anime.

Un'unica tabella 'downloads' raccoglie lo storico di tutti gli scraper:
i campi comuni (titolo, percorso, dimensione, data) più colonne specifiche
per tipo. Così lo storico è interrogabile da un punto solo e ogni scraper
può verificare cosa è già stato scaricato.

Filosofia degli errori: il database è un registro accessorio, quindi ogni
problema viene solo loggato come warning e non interrompe mai i download.
"""
from __future__ import annotations

import logging
import os
import re
import shutil
import sqlite3
import threading
from datetime import datetime, timezone

log = logging.getLogger('scraper_db')

# Il file .db vive accanto a questo modulo, condiviso da tutti gli scraper.
#
# «Accanto a questo modulo» pero' non si puo' calcolare da __file__: dentro
# l'eseguibile costruito con PyInstaller quella cartella e' temporanea e viene
# cancellata alla chiusura, quindi lo storico dei download sparirebbe a ogni
# uscita dal programma e ogni avvio ripartirebbe da un database vuoto. E' lo
# stesso motivo per cui i log e la lingua passano da server.config.paths: qui
# mancava, ed era l'ultimo modulo rimasto indietro.
#
# Fuori dall'eseguibile il percorso e' identico a prima - server.config.paths
# risolve nella cartella dei sorgenti - quindi il database gia' esistente resta
# dov'e' e non se ne crea un secondo.
from server.config.paths import dati as _dati


def percorso_db() -> str:
    """Il file del database, accanto all'eseguibile o ai sorgenti.

    E' una funzione e non una costante per lo stesso motivo di
    ``i18n._file_impostazioni``: una costante fisserebbe la radice del progetto
    alla prima riga dell'import, cioe' nel momento in cui se ne sa di meno. Qui
    il costo e' ancora piu' basso, perche' la si chiede solo aprendo la
    connessione, una volta per thread.
    """
    return _dati('Database_Globale', 'scraper_metadata.db')


# Una connessione per thread: sqlite3 vieta di usare la stessa connessione
# da thread diversi, e gli scraper scrivono dai thread di download.
_local = threading.local()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS downloads (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,

    scraper_type    TEXT NOT NULL,       -- 'audio', 'manga', 'anime'
    media_kind      TEXT DEFAULT '',     -- 'audio' / 'video' per lo scraper audio; '' per gli altri

    -- Campi universali
    source_id       TEXT NOT NULL,       -- YouTube video ID / MangaDex chapter UUID / AnimeUnity episode ID
    title           TEXT NOT NULL,
    source_url      TEXT DEFAULT '',
    file_path       TEXT NOT NULL,       -- Percorso relativo dal progetto
    file_size_bytes INTEGER DEFAULT 0,
    downloaded_at   TEXT NOT NULL,       -- ISO 8601

    -- Collezione (album/playlist, manga, anime)
    collection_name TEXT DEFAULT '',
    collection_id   TEXT DEFAULT '',

    -- Audio
    artist          TEXT DEFAULT '',
    duration_secs   REAL DEFAULT 0,
    audio_format    TEXT DEFAULT '',
    track_number    INTEGER DEFAULT 0,

    -- Manga
    chapter_number  TEXT DEFAULT '',
    page_count      INTEGER DEFAULT 0,
    scanlation_group TEXT DEFAULT '',
    language        TEXT DEFAULT '',
    is_cbz          INTEGER DEFAULT 0,

    -- Anime
    episode_number  TEXT DEFAULT '',
    anime_type      TEXT DEFAULT '',

    -- media_kind fa parte della chiave: lo stesso video YouTube può essere
    -- scaricato sia come audio sia come video, e sono due file distinti che
    -- meritano due righe. Per manga e anime la colonna resta '' e il
    -- vincolo si comporta come prima.
    UNIQUE(scraper_type, source_id, media_kind)
);

CREATE INDEX IF NOT EXISTS idx_scraper_type ON downloads(scraper_type);
CREATE INDEX IF NOT EXISTS idx_collection ON downloads(scraper_type, collection_name);
CREATE INDEX IF NOT EXISTS idx_downloaded_at ON downloads(downloaded_at);
"""


def _get_conn() -> sqlite3.Connection:
    """Restituisce la connessione SQLite del thread corrente, creandola al primo uso.

    La modalità WAL permette letture e scritture concorrenti dai vari
    thread di download senza che si blocchino a vicenda.

    Lo schema viene applicato **qui**, alla nascita di ogni connessione, e non
    solo in ``init_db()``. Il motivo e' che ``init_db()`` la chiamava una parte
    sola del progetto: la riga di comando di AudioDex, dentro il suo ``main()``.
    L'interfaccia grafica importa AudioDex come libreria e quel ``main()`` non
    lo esegue mai, quindi la tabella non veniva creata e ogni download
    registrato finiva contro un "no such table: downloads" - un warning nel log
    e nient'altro. Dalla finestra lo storico restava vuoto per sempre, senza
    che niente lo dicesse.

    ``CREATE TABLE IF NOT EXISTS`` costa una lettura del catalogo di SQLite e
    si puo' ripetere quanto si vuole: metterlo sulla strada obbligata di
    chiunque apra il database e' piu' sicuro che ricordarsi di chiamare una
    funzione di inizializzazione da ogni nuovo punto d'ingresso.
    """
    conn = getattr(_local, 'conn', None)
    if conn is None:
        percorso = percorso_db()
        os.makedirs(os.path.dirname(percorso), exist_ok=True)
        conn = sqlite3.connect(percorso, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        _local.conn = conn
        conn.executescript(_SCHEMA)
        conn.commit()
        _migrate_media_kind(conn)
    return conn


def init_db() -> None:
    """Apre il database e ne assicura lo schema.

    Resta come punto d'ingresso esplicito per la riga di comando, che cosi'
    segnala subito un database illeggibile invece di scoprirlo al primo
    download. Il lavoro vero lo fa pero' ``_get_conn()``, che passa dalla
    stessa strada anche quando nessuno chiama questa.
    """
    try:
        _get_conn()
        log.debug("Database inizializzato: %s", percorso_db())
    except Exception as e:
        log.warning("Errore init database: %s", e)


def _istruzioni(schema: str) -> list[str]:
    """Spezza uno schema SQL nelle sue istruzioni, una per elemento.

    Serve perché la migrazione non può usare ``executescript``: quello
    concluderebbe la transazione appena aperta. Le istruzioni vanno quindi
    eseguite una per volta, e prima separate.

    Non basta però tagliare sul punto e virgola. Lo schema qui sopra è
    commentato riga per riga, e uno di quei commenti — quello su ``media_kind``
    — un punto e virgola ce l'ha dentro: tagliando alla cieca, la CREATE TABLE
    si spezzava a metà e SQLite rispondeva "incomplete input". I commenti si
    tolgono prima, e il problema non si pone.
    """
    pulito = re.sub(r'--[^\n]*', '', schema)
    return [i for i in (s.strip() for s in pulito.split(';')) if i]


def _migrate_media_kind(conn: sqlite3.Connection) -> None:
    """Porta un database pre-esistente allo schema con 'media_kind'.

    Prima il vincolo era UNIQUE(scraper_type, source_id): scaricare lo
    stesso video prima in audio e poi in video sovrascriveva la riga
    invece di tenerne due. La chiave ora comprende 'media_kind', ma
    SQLite non sa modificare un vincolo con ALTER TABLE: l'unica via è
    ricostruire la tabella e ricopiare i dati.

    L'operazione è protetta su tre fronti: si esce subito se lo schema è
    già aggiornato, si fa una **copia di sicurezza** del file prima di
    toccarlo, e la ricostruzione avviene in un'unica transazione (o
    riesce tutta, o il database resta com'era).

    Sul terzo fronte la protezione era però solo dichiarata. Il blocco
    ``with conn:`` sembra una transazione ma non lo era: il modulo sqlite3 di
    Python ne apre una da sé soltanto prima di INSERT, UPDATE e DELETE, mai
    prima del DDL, e ``executescript`` per giunta conclude quella eventualmente
    aperta. ALTER TABLE e CREATE TABLE finivano quindi fuori da qualunque
    transazione, e un guasto a metà strada lasciava i dati dentro
    ``downloads_old`` con una ``downloads`` nuova e vuota accanto. Al lancio
    successivo il controllo qui sopra trovava 'media_kind' e usciva subito:
    lo storico restava lì, invisibile, e il programma diceva di non avere mai
    scaricato niente. La copia di sicurezza c'era, ma nessuno sapeva di doverla
    cercare.

    Adesso la transazione si apre a mano su una connessione in autocommit, che
    è l'unico modo di farci stare dentro anche il DDL, e ``_recupera_migrazione``
    rimette a posto i database già rovinati dalla versione precedente.
    """
    _recupera_migrazione(conn)

    columns = [r['name'] for r in conn.execute("PRAGMA table_info(downloads)")]
    if not columns or 'media_kind' in columns:
        return  # tabella appena creata dallo schema nuovo, o già migrata

    log.info("Migrazione database: aggiunta di 'media_kind' alla chiave univoca")

    # Il WAL può contenere scritture non ancora nel file principale:
    # senza questo passaggio la copia di sicurezza sarebbe incompleta.
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        percorso = percorso_db()
        backup = percorso + '.backup-pre-media-kind'
        if not os.path.exists(backup):
            shutil.copy2(percorso, backup)
            log.info("Copia di sicurezza del database: %s", backup)
    except Exception as e:
        log.warning("Copia di sicurezza non riuscita, migrazione annullata: %s", e)
        return

    # Si copiano solo le colonne presenti in entrambi gli schemi, così la
    # migrazione regge anche se il vecchio file ne ha qualcuna in meno.
    shared = [c for c in columns if c != 'id']
    cols_sql = ', '.join(shared)

    # Le PRAGMA sui vincoli non hanno effetto dentro una transazione, quindi
    # vanno prima; e la transazione la si apre a mano, perché è l'unico modo di
    # farci stare dentro anche ALTER TABLE e CREATE TABLE.
    precedente = conn.isolation_level
    try:
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.isolation_level = None          # da qui le transazioni le apriamo noi
        conn.execute("BEGIN")
        try:
            conn.execute("ALTER TABLE downloads RENAME TO downloads_old")
            # Una istruzione per volta invece di executescript, che concluderebbe
            # la transazione appena aperta rendendo irreversibile ciò che segue.
            for istruzione in _istruzioni(_SCHEMA):
                conn.execute(istruzione)
            conn.execute(
                f"INSERT INTO downloads ({cols_sql}) SELECT {cols_sql} FROM downloads_old"
            )
            # Le righe storiche dello scraper audio sono tutte download
            # audio (il ramo video non esisteva ancora). Vanno etichettate,
            # altrimenti riscaricare una vecchia traccia creerebbe una
            # seconda riga invece di aggiornare la sua.
            conn.execute(
                "UPDATE downloads SET media_kind='audio' "
                "WHERE scraper_type='audio' AND (media_kind IS NULL OR media_kind='')"
            )
            conn.execute("DROP TABLE downloads_old")
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        moved = conn.execute("SELECT COUNT(*) FROM downloads").fetchone()[0]
        log.info("Migrazione completata: %d righe conservate", moved)
    except Exception as e:
        log.warning("Migrazione fallita (i dati restano intatti): %s", e)
    finally:
        conn.isolation_level = precedente
        conn.execute("PRAGMA foreign_keys=ON")


def _recupera_migrazione(conn: sqlite3.Connection) -> None:
    """Rimette a posto una migrazione interrotta da una versione precedente.

    Fino a poco fa la ricostruzione non era davvero in transazione, e un guasto
    a metà strada lasciava sul disco due tabelle: una ``downloads`` nuova e
    vuota, e una ``downloads_old`` con dentro tutto lo storico. Il controllo
    all'inizio della migrazione trovava la colonna 'media_kind' nella tabella
    nuova, concludeva che non c'era niente da fare, e i download di anni
    restavano lì accanto senza che nulla li nominasse.

    Qui si guarda solo se ``downloads_old`` esiste: se c'è, la migrazione
    precedente non è arrivata in fondo e la si finisce. ``INSERT OR IGNORE``
    perché una parte delle righe potrebbe essere già passata, e in quel caso
    va tenuta quella nuova.
    """
    tabelle = {r[0] for r in
               conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if 'downloads_old' not in tabelle or 'downloads' not in tabelle:
        return

    vecchie = [r['name'] for r in conn.execute("PRAGMA table_info(downloads_old)")]
    nuove = {r['name'] for r in conn.execute("PRAGMA table_info(downloads)")}
    comuni = [c for c in vecchie if c != 'id' and c in nuove]
    if not comuni:
        return
    cols_sql = ', '.join(comuni)

    log.warning("Trovata una migrazione interrotta: recupero le righe da downloads_old")
    try:
        conn.execute(
            f"INSERT OR IGNORE INTO downloads ({cols_sql}) SELECT {cols_sql} FROM downloads_old")
        if 'media_kind' in nuove:
            conn.execute(
                "UPDATE downloads SET media_kind='audio' "
                "WHERE scraper_type='audio' AND (media_kind IS NULL OR media_kind='')")
        conn.execute("DROP TABLE downloads_old")
        conn.commit()
        recuperate = conn.execute("SELECT COUNT(*) FROM downloads").fetchone()[0]
        log.info("Recupero riuscito: %d righe di nuovo visibili", recuperate)
    except Exception as e:
        # Meglio lasciare downloads_old dov'è che perderla: se ne riparla al
        # prossimo avvio, e intanto i dati non sono andati da nessuna parte.
        log.warning("Recupero non riuscito, downloads_old resta sul posto: %s", e)


def _now_iso() -> str:
    """Timestamp corrente in UTC, formato ISO 8601 (ordinabile come testo)."""
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def _relative_path(path: str) -> str:
    """Converte un percorso assoluto in relativo rispetto alla cartella del database.

    Salvare percorsi relativi mantiene validi i riferimenti anche se la
    cartella del progetto viene spostata o rinominata. Su Windows il
    calcolo fallisce tra dischi diversi (ValueError): in quel caso si
    salva il percorso assoluto così com'è.

    Il riferimento è la cartella **del file .db**, non quella di questo
    modulo. Fuori dall'eseguibile sono la stessa cosa, ed è il motivo per cui
    la differenza non si notava; dentro no. Con ``__file__`` la base diventava
    la cartella temporanea di PyInstaller, e ogni percorso registrato veniva
    calcolato rispetto a una cartella che sarebbe stata cancellata pochi minuti
    dopo: i riferimenti nascevano già rotti, e nessuno se ne accorgeva perché
    la colonna la si guarda solo mesi dopo. Ancorandolo al database, il
    percorso relativo significa sempre qualcosa rispetto a dove il database si
    trova davvero.
    """
    try:
        return os.path.relpath(path, os.path.dirname(os.path.abspath(percorso_db())))
    except ValueError:
        return path


# === INSERT PER OGNI SCRAPER ===

def record_audio_download(
    source_id: str,
    title: str,
    source_url: str = '',
    file_path: str = '',
    file_size_bytes: int = 0,
    collection_name: str = '',
    collection_id: str = '',
    artist: str = '',
    duration_secs: float = 0,
    audio_format: str = '',
    track_number: int = 0,
    media_kind: str = 'audio',
) -> None:
    """Registra un brano (o un video) scaricato.

    'INSERT OR REPLACE' sul vincolo UNIQUE(scraper_type, source_id,
    media_kind): riscaricare la stessa traccia **nello stesso formato**
    aggiorna la riga esistente invece di duplicarla, mentre la versione
    audio e quella video dello stesso video YouTube convivono come due
    righe distinte — sono due file diversi sul disco.
    """
    try:
        conn = _get_conn()
        conn.execute(
            """INSERT OR REPLACE INTO downloads
               (scraper_type, media_kind, source_id, title, source_url, file_path,
                file_size_bytes, downloaded_at, collection_name, collection_id,
                artist, duration_secs, audio_format, track_number)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ('audio', media_kind, source_id, title, source_url, _relative_path(file_path),
             file_size_bytes, _now_iso(), collection_name, collection_id,
             artist, duration_secs, audio_format, track_number),
        )
        conn.commit()
        log.debug("DB audio: %s", title)
    except Exception as e:
        log.warning("DB audio errore per '%s': %s", title, e)


def record_manga_download(
    source_id: str,
    title: str,
    source_url: str = '',
    file_path: str = '',
    file_size_bytes: int = 0,
    collection_name: str = '',
    collection_id: str = '',
    chapter_number: str = '',
    page_count: int = 0,
    scanlation_group: str = '',
    language: str = '',
    is_cbz: bool = False,
) -> None:
    """Registra un capitolo manga scaricato (stessa logica di quello audio)."""
    try:
        conn = _get_conn()
        conn.execute(
            """INSERT OR REPLACE INTO downloads
               (scraper_type, source_id, title, source_url, file_path,
                file_size_bytes, downloaded_at, collection_name, collection_id,
                chapter_number, page_count, scanlation_group, language, is_cbz)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ('manga', source_id, title, source_url, _relative_path(file_path),
             file_size_bytes, _now_iso(), collection_name, collection_id,
             chapter_number, page_count, scanlation_group, language, int(is_cbz)),
        )
        conn.commit()
        log.debug("DB manga: %s", title)
    except Exception as e:
        log.warning("DB manga errore per '%s': %s", title, e)


def record_anime_download(
    source_id: str,
    title: str,
    source_url: str = '',
    file_path: str = '',
    file_size_bytes: int = 0,
    collection_name: str = '',
    collection_id: str = '',
    episode_number: str = '',
    anime_type: str = '',
) -> None:
    """Registra un episodio anime scaricato (stessa logica di quello audio)."""
    try:
        conn = _get_conn()
        conn.execute(
            """INSERT OR REPLACE INTO downloads
               (scraper_type, source_id, title, source_url, file_path,
                file_size_bytes, downloaded_at, collection_name, collection_id,
                episode_number, anime_type)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ('anime', source_id, title, source_url, _relative_path(file_path),
             file_size_bytes, _now_iso(), collection_name, collection_id,
             episode_number, anime_type),
        )
        conn.commit()
        log.debug("DB anime: %s", title)
    except Exception as e:
        log.warning("DB anime errore per '%s': %s", title, e)


# === QUERY ===

def is_recorded(scraper_type: str, source_id: str, media_kind: str | None = None) -> bool:
    """Indica se un download è già registrato (per saltare i duplicati).

    Senza `media_kind` risponde "sì" per qualunque versione; passandolo
    ('audio' o 'video') si chiede se esiste **quella** versione, utile
    ora che lo stesso video può essere presente in entrambe.
    """
    try:
        conn = _get_conn()
        query = "SELECT 1 FROM downloads WHERE scraper_type=? AND source_id=?"
        params = [scraper_type, source_id]
        if media_kind is not None:
            query += " AND media_kind=?"
            params.append(media_kind)
        return conn.execute(query, params).fetchone() is not None
    except Exception:
        return False


def get_downloads(
    scraper_type: str | None = None,
    collection_name: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """Elenca i download registrati, dal più recente, con filtri opzionali.

    Si può filtrare per tipo di scraper ('audio', 'manga', 'anime') e per
    nome della collezione (album, serie). Restituisce dizionari semplici,
    comodi da stampare o serializzare.
    """
    try:
        conn = _get_conn()
        query = "SELECT * FROM downloads WHERE 1=1"
        params: list = []
        if scraper_type:
            query += " AND scraper_type=?"
            params.append(scraper_type)
        if collection_name:
            query += " AND collection_name=?"
            params.append(collection_name)
        query += " ORDER BY downloaded_at DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        log.warning("DB query errore: %s", e)
        return []


def get_stats() -> dict:
    """Statistiche globali: numero di download e byte totali per ogni tipo di scraper."""
    try:
        conn = _get_conn()
        stats = {}
        for stype in ('audio', 'manga', 'anime'):
            row = conn.execute(
                "SELECT COUNT(*) as cnt, COALESCE(SUM(file_size_bytes),0) as total_bytes "
                "FROM downloads WHERE scraper_type=?",
                (stype,),
            ).fetchone()
            stats[stype] = {'count': row['cnt'], 'total_bytes': row['total_bytes']}
        return stats
    except Exception as e:
        log.warning("DB stats errore: %s", e)
        return {}
