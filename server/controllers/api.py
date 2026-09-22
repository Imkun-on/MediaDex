"""Cosa la pagina puo' chiedere, e nient'altro.

La regola di questo file
    Qui non si decide niente di importante. Si riceve una richiesta, si
    controlla che abbia senso, si chiama chi la sa eseguire, e si traduce la
    risposta in qualcosa che la pagina possa mostrare. Se in un metodo qui
    dentro compare una decisione vera - quale preset abbia senso, se un ordine
    di tracce ci stia su un CD, se un URL sia una playlist - e' nel posto
    sbagliato: sta gia' nei motori, ed e' li' che deve restare, o si finisce
    con due risposte diverse alla stessa domanda.

Ogni metodo risponde con un dizionario
    Sempre, e sempre con almeno ``ok``. La pagina non deve mai ricevere
    un'eccezione Python: in JavaScript arriverebbe come un rifiuto senza
    spiegazione, e non c'e' una console aperta in cui andarla a leggere.

I motori si caricano quando servono
    I quattro ``_motore()``, ``_burndex()``, ``_pixdex()``, ``_clipdex()`` non
    importano niente finche' nessuno preme un bottone. E' il motivo per cui la
    finestra si apre in meno di un secondo invece che in cinque: yt-dlp, COM e
    il resto arrivano al primo uso, mentre chi guarda sta gia' leggendo la
    schermata.
"""
from __future__ import annotations

import io
import logging
import os
import re
import sys
import threading
import traceback

import webview

from server.config import i18n
from server.config.paths import (
    cartella_montaggi as _montaggi, cartella_musica as _musica,
    cartella_rimasterizzati as _rimasterizzati, dati as _dati,
    risultati as _risultati)
from server.config.strings.app import TESTI as TESTI_APP
from server.config.strings.audio import TESTI as TESTI_AUDIO
from server.controllers import bridge
from server.state import progress as _spia
from server.state.jobs import Posto
from server.config.strings.errori import TESTI as TESTI_DIAGNOSI
from server.utils.contract import ErroreSpiegato, classifica_errore
from server.utils.media import VIDEO_EXTS as _VIDEO_EXTS
from server.utils.text import leggi_tempo as _leggi_tempo

# pywebview 6 ha rinominato le costanti dei selettori di file. Si prendono le
# nuove quando esistono e si ricade sulle vecchie: cosi' il programma non
# stampa avvisi di deprecazione sulle versioni recenti e continua a girare su
# quelle precedenti.
_DLG_CARTELLA = getattr(getattr(webview, 'FileDialog', None), 'FOLDER',
                        getattr(webview, 'FOLDER_DIALOG', 2))
_DLG_APRI = getattr(getattr(webview, 'FileDialog', None), 'OPEN',
                    getattr(webview, 'OPEN_DIALOG', 10))


# ── Dalla fase finita alla fase in corso ─────────────────────────────────────
#
# AudioDex riferisce la fase *conclusa*: ``_PhaseTracker.done`` si legge "la
# traccia ha superato la fase indicata", e infatti ``phase('convert')`` sta
# subito sotto il commento "FFmpeg ha finito". La pastiglia accanto alla traccia
# dice invece cosa sta succedendo adesso, che e' l'unica cosa utile mentre si
# guarda: passando il nome cosi' com'e', diceva "converto" a conversione finita
# e "scrivo i tag" a lavoro concluso - un passo indietro su tutta la riga.
#
# Fra le due letture c'e' esattamente un passo, ed e' questa tabella. 'tag' e'
# l'ultima: dopo di lei non c'e' una fase successiva da annunciare, e un istante
# dopo arriva comunque tracciaFinita a scrivere l'esito.
_DOPO = {'download': 'convert', 'convert': 'lyrics', 'lyrics': 'tag', 'tag': 'tag'}


# ── Moduli del motore, caricati alla prima richiesta ──────────────────────────
# Importare AudioDex costa qualche secondo (yt-dlp non e' leggero): farlo qui
# invece che all'avvio fa comparire la finestra subito, che e' la prima cosa
# che si giudica di un programma.
_audiodex = None


_burn = None


_pix = None


_clip = None


def _motore():
    global _audiodex
    if _audiodex is None:
        from server.services import audio as _ad
        _audiodex = _ad
    return _audiodex


def _burndex():
    global _burn
    if _burn is None:
        from server import burn as _bd
        _burn = _bd
    return _burn


def _pixdex():
    global _pix
    if _pix is None:
        from server import video as _px
        _pix = _px
    return _pix


def _clipdex():
    global _clip
    if _clip is None:
        from server.video import edit as _cd
        _clip = _cd
    return _clip


# Il file di log di ciascuna sezione. I nomi sono quelli che i motori danno ai
# propri logger in setup_logger(), e vanno tenuti allineati a quelli.
_LOG_DI = {'audio': 'audiodex', 'burn': 'burndex', 'pix': 'pixdex', 'clip': 'clipdex'}


class Diario(io.TextIOBase):
    """Raccoglie cio' che i moduli stampano e lo scrive nel log su file.

    Prima queste righe finivano in una scheda dentro la finestra. Non ci vanno
    piu', ed e' il punto: erano il racconto tecnico, riga per riga, dello
    stesso lavoro che la barra di avanzamento racconta meglio in una riga
    sola. Peggio, quando qualcosa andava storto la riga che contava finiva
    sepolta sotto le altre invece di farsi notare - adesso quella apre una
    finestra e le altre restano qui.

    «Qui» e' ``logs/<sezione>.log``, che i motori scrivono gia' per conto
    loro: questo non aggiunge un secondo diario, si limita a versare nello
    stesso file anche cio' che i motori *stampano* invece di registrare.
    Quindi non si e' perso niente, e chi va a cercare trova tutto in un posto
    solo.

    I moduli del motore parlano con Rich, che colora scrivendo sequenze di
    controllo ANSI: dentro un file di testo diventerebbero caratteri strani in
    mezzo alle righe, quindi si tolgono.
    """

    _ANSI = re.compile(r'\x1b\[[0-9;]*[A-Za-z]')

    def __init__(self, dove: str):
        self._log = logging.getLogger(_LOG_DI.get(dove, 'mediadex'))
        self._resto = ''
        self._lucchetto = threading.Lock()

    def write(self, s: str) -> int:      # type: ignore[override]
        if not s:
            return 0
        with self._lucchetto:
            self._resto += s
            while '\n' in self._resto:
                riga, self._resto = self._resto.split('\n', 1)
                self._manda(riga)
        return len(s)

    def flush(self) -> None:
        with self._lucchetto:
            if self._resto:
                self._manda(self._resto)
                self._resto = ''

    def _manda(self, grezza: str) -> None:
        testo = self._ANSI.sub('', grezza).rstrip()
        if testo:
            self._log.info(testo)


def _riporta_avanzamento(descrizione: str, fatti: float, totale: float | None) -> None:
    """Porta alla pagina un avanzamento riferito da un motore.

    E' l'unico traduttore fra il modo in cui i motori contano - tracce,
    fotogrammi, settori - e la barra: qui si decide soltanto come mostrarlo,
    mai quanto sia avanzato il lavoro.
    """
    if not totale:
        # Un motore che non sa quanto manca non deve far finta di saperlo:
        # resta la scritta, la barra non si muove.
        bridge.verso_pagina('avanzaLavoro', 0, 0, None, descrizione)
        return
    bridge.verso_pagina('avanzaLavoro', int(fatti), int(totale),
                  min(fatti / totale, 1.0), descrizione)


class Api:
    """I metodi che la pagina puo' chiamare, e nient'altro.

    Ogni metodo restituisce un dizionario con almeno ``ok``: la pagina non
    deve mai ricevere un'eccezione Python, che in JavaScript arriverebbe come
    un rifiuto senza spiegazione.
    """

    def __init__(self):
        # Il posto di lavoro e' uno solo per tutto il programma, e la sua
        # meccanica sta in server/state/jobs.py: qui la si usa e basta.
        self._posto = Posto()
        self._risultati: list[dict] = []

    # ── Avvio ────────────────────────────────────────────────────────────────

    def avvio(self) -> dict:
        """Tutto cio' che serve alla pagina per disegnarsi la prima volta.

        Qui accanto c'era anche ``dipinta()``, che la pagina chiamava al primo
        fotogramma davvero composto per far togliere a Python l'immagine di
        caricamento di PyInstaller. Quell'immagine non c'e' piu' - l'attesa
        sta tutta dentro la pagina, sotto il velo - e con lei se n'e' andato
        tutto il giro: mostrare la finestra, contare i fotogrammi, la scadenza
        di sicurezza che la scopriva comunque. La finestra nasce visibile e
        massimizzata, e non c'e' niente da scoprire.
        """
        return {
            'ok': True,
            # I tre cataloghi che la pagina puo' avere bisogno di dire, e solo
            # quelli: i testi di AudioDex, quelli dell'interfaccia, e le frasi
            # con cui si spiega un guasto. I cataloghi di BurnDex, PixDex e
            # ClipDex restano fuori: sono le loro schermate a terminale, piene
            # di markup di Rich, e la finestra non ne dice una riga.
            'testi': {**TESTI_AUDIO, **TESTI_APP, **TESTI_DIAGNOSI},
            # Non e' piu' una cartella da scegliere: e' dove BurnDex va a
            # cercare le raccolte, cioe' dove i download finiscono.
            'cartella': _musica(),
            'sfondo': self._video_sfondo(),
        }

    @staticmethod
    def _video_sfondo() -> str:
        """Indirizzo del video di sfondo, se e' gia' sul disco.

        Nessuno lo scarica: se qualcuno lo ha messo li' si mostra, altrimenti
        restano i gradienti animati del tema - che non sono un ripiego mesto
        ma uno sfondo a sua volta guardabile, ed e' il motivo per cui il file
        e' rimasto facoltativo invece di diventare un download all'avvio.
        """
        percorso = _dati('assets', 'cyberpunk-citadel.mp4')
        try:
            if os.path.getsize(percorso) < 1_000_000:
                return ''
        except OSError:
            return ''
        return Api._url_file(percorso)

    def scegli_cartella(self) -> dict:
        """Apre il selettore di cartelle del sistema."""
        try:
            scelta = bridge.attuale().create_file_dialog(_DLG_CARTELLA)
        except Exception as exc:
            return {'ok': False, 'errore': str(exc)}
        return {'ok': True, 'cartella': scelta[0] if scelta else ''}

    def apri_risultati(self) -> dict:
        """Apre in Esplora risorse la cartella dove il programma salva tutto.

        E' la risposta alla domanda che nasce dal non chiedere piu' dove
        salvare: «e allora dove sono finiti?». La cartella si crea qui se non
        c'e' ancora, altrimenti al primo avvio il bottone aprirebbe il nulla.

        ``os.startfile`` esiste solo su Windows, che e' dove gira la finestra;
        altrove si ripiega su xdg-open e open, cosi' chi lavora ai sorgenti da
        Linux o da Mac non si trova un bottone che non fa niente.
        """
        cartella = _risultati()
        try:
            os.makedirs(cartella, exist_ok=True)
            if hasattr(os, 'startfile'):
                os.startfile(cartella)          # noqa: S606  (e' una cartella nostra)
            else:
                import subprocess
                comando = 'open' if sys.platform == 'darwin' else 'xdg-open'
                subprocess.Popen([comando, cartella])
        except Exception as exc:                # noqa: BLE001
            return {'ok': False, 'errore': f'{cartella}\n{exc}'}
        return {'ok': True}

    # ── Ricerca e analisi ────────────────────────────────────────────────────

    def analizza(self, testo: str, modo: str) -> dict:
        """Guarda cosa c'e' dietro un link o una ricerca, senza scaricare nulla.

        Torna subito: il lavoro vero avviene in un thread, e la pagina viene
        avvisata a cose fatte. Cosi' la finestra non si congela nei secondi in
        cui yt-dlp interroga YouTube.
        """
        bridge.entra('audio')
        testo = (testo or '').strip()
        if not testo:
            return {'ok': False, 'errore': i18n.t('err.no_input')}
        # Il posto si prende dopo i controlli, non prima: un modulo compilato
        # male non deve lasciare il programma occupato senza che giri niente.
        if not self._posto.occupa():
            return {'ok': False, 'errore': i18n.t('err.busy')}

        self._in_thread(self._analizza_davvero, testo, modo)
        return {'ok': True, 'avviato': True}

    def _analizza_davvero(self, testo: str, modo: str) -> None:
        ad = _motore()
        if modo == 'search':
            trovati = ad.search_youtube(testo)
            titolo = i18n.t('res.search', n=len(trovati))
        elif ad.e_playlist(testo):
            nome, trovati, _meta = ad.get_playlist_entries(testo)
            titolo = i18n.t('res.playlist', n=len(trovati), titolo=nome)
        else:
            info = ad.get_video_details(testo)
            trovati = [ad.entry_da_info(info, testo)] if info else []
            titolo = i18n.t('res.single',
                            titolo=(info or {}).get('title', '')) if info else ''

        self._risultati = trovati or []
        bridge.verso_pagina('mostraRisultati', {
            'titolo': titolo,
            'voci': [{
                'titolo': v.get('title', ''),
                'durata': self._durata(v.get('duration')),
                'canale': v.get('uploader') or v.get('channel') or '',
                'viste': self._viste(v.get('views')),
                'miniatura': self._miniatura(v.get('id')),
            } for v in self._risultati],
        })

    # ── Download ─────────────────────────────────────────────────────────────

    def scarica(self, opzioni: dict) -> dict:
        """Avvia il download di cio' che l'analisi ha trovato."""
        bridge.entra('audio')
        if not self._risultati:
            return {'ok': False, 'errore': i18n.t('err.nothing')}
        if not self._posto.occupa():
            return {'ok': False, 'errore': i18n.t('err.busy')}

        self._in_thread(self._scarica_davvero, opzioni)
        return {'ok': True, 'avviato': True}

    def _scarica_davvero(self, opzioni: dict) -> None:
        """Scarica le tracce scelte, raccontando alla pagina cosa succede a
        ciascuna mentre succede.

        Non si usa ``download_batch``, che disegna da se' le proprie barre con
        Rich: qui il ciclo lo si tiene in mano per poter dire alla pagina, per
        ogni singola traccia, se sta scaricando, convertendo, cercando il
        testo o scrivendo i tag. E' la differenza fra una barra che gira e
        un'interfaccia che dice cosa sta facendo.

        ``download_single`` protegge ogni uso di Rich con un controllo, quindi
        passandogli ``progress=None`` lavora in silenzio.
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        ad = _motore()
        cartella = _musica()

        scelti = opzioni.get('scelti')
        indici = ([i for i in scelti if 0 <= i < len(self._risultati)]
                  if scelti else list(range(len(self._risultati))))
        if not indici:
            bridge.verso_pagina('mostraRiepilogo',
                          {'testo': i18n.t('err.nothing'), 'ok': False})
            return

        totale = len(indici)
        fatte = [0]
        bridge.verso_pagina('iniziaLavoro', totale)

        # Quanto e' avanzato il download di ogni traccia ancora in corso, da 0
        # a 1, ricavato dai byte che yt-dlp conta gia' per conto suo.
        #
        # Il peso 0.9 non e' un abbellimento: scaricare i byte e' quasi tutto
        # il lavoro di una traccia, ma non tutto - dopo restano la conversione
        # con FFmpeg, il testo sincronizzato e i tag. Contando i byte per
        # l'intero, la barra arriverebbe in fondo con il programma ancora al
        # lavoro, che e' il difetto peggiore che possa avere una barra. Cosi'
        # invece l'ultimo decimo lo mette solo la traccia davvero finita.
        PESO_BYTE = 0.9
        quote: dict[int, float] = {}
        ultimo_invio = [0.0]
        serratura = threading.Lock()

        def riferisci(forza: bool = False) -> None:
            """Manda alla pagina l'avanzamento complessivo, byte compresi."""
            import time as _time
            with serratura:
                adesso = _time.monotonic()
                # Il ponte con JavaScript non va intasato: con otto download in
                # parallelo yt-dlp chiama decine di volte al secondo, e l'occhio
                # non vede nessuna differenza sotto il decimo di secondo.
                if not forza and adesso - ultimo_invio[0] < 0.12:
                    return
                ultimo_invio[0] = adesso
                parziale = fatte[0] + sum(quote.values()) * PESO_BYTE
            bridge.verso_pagina('avanzaLavoro', fatte[0], totale,
                          min(parziale / totale, 1.0) if totale else 0)

        def una(indice: int) -> dict:
            entry = self._risultati[indice]
            bridge.verso_pagina('tracciaFase', indice, 'download')

            def byte(scaricati: int, totali: int, k=indice) -> None:
                frazione = min(scaricati / totali, 1.0) if totali else 0.0
                # Sotto serratura perche' riferisci() somma questo stesso
                # dizionario: aggiungere una chiave mentre un altro thread lo
                # sta scorrendo fa alzare a Python un RuntimeError, e questa
                # funzione gira dentro il gancio di yt-dlp, dove un'eccezione
                # abortisce un download altrimenti sano.
                with serratura:
                    quote[k] = frazione
                bridge.verso_pagina('tracciaAvanza', k, round(frazione, 4))
                riferisci()

            esito = ad.download_single(
                entry, cartella, opzioni.get('formato', 'm4a'),
                track_num=indice + 1,
                total_tracks=totale,
                fetch_lyrics=bool(opzioni.get('testi', True)),
                media=opzioni.get('media', 'audio'),
                dividi=bool(opzioni.get('dividi', False)),
                on_phase=lambda fase, k=indice: bridge.verso_pagina('tracciaFase', k,
                                                             _DOPO.get(fase, fase)),
                on_progress=byte,
            )
            with serratura:
                fatte[0] += 1
                quote.pop(indice, None)
            bridge.verso_pagina('tracciaFinita', indice, esito.get('status', 'fail'),
                          esito.get('error', ''))
            riferisci(forza=True)
            return esito

        esiti: list[dict] = []
        with ThreadPoolExecutor(max_workers=int(opzioni.get('paralleli', 3))) as pool:
            lavori = {pool.submit(una, i): i for i in indici}
            for lavoro in as_completed(lavori):
                try:
                    esiti.append(lavoro.result())
                except Exception as exc:      # noqa: BLE001
                    indice = lavori[lavoro]
                    bridge.verso_pagina('tracciaFinita', indice, 'fail', str(exc))
                    esiti.append({'status': 'fail'})

        ok = sum(1 for e in esiti if e.get('status') == 'ok')
        falliti = sum(1 for e in esiti if e.get('status') == 'fail')
        bridge.verso_pagina('mostraRiepilogo', {
            'testo': i18n.t('done.summary', ok=ok, tot=len(esiti), falliti=falliti),
            'ok': falliti == 0,
        })

    # ── Masterizzazione ──────────────────────────────────────────────────────

    def burn_scansiona(self, cartella: str) -> dict:
        """Elenca i brani di una cartella nell'ordine in cui finirebbero sul CD.

        L'ordine non e' alfabetico: e' quello che decide BurnDex, che sa
        riconoscere la numerazione nei nomi e rispettarla. Mostrarne uno
        diverso qui vorrebbe dire mentire su cosa verra' inciso.
        """
        bridge.entra('burn')
        cartella = (cartella or '').strip().strip('"')
        if not os.path.isdir(cartella):
            return {'ok': False, 'errore': i18n.t('burn.no_folder')}

        bd = _burndex()
        percorsi, criterio = bd.ordina_tracce(cartella)
        if not percorsi:
            return {'ok': False, 'errore': i18n.t('burn.no_audio')}

        durate = [bd.durata_traccia(p) for p in percorsi]

        # Una traccia che ffprobe non sa leggere vale zero settori per
        # _settori_totali, e a quel punto la barra della capienza direbbe che
        # ci sta della roba che non ci sta - proprio nella schermata che serve
        # a decidere se incidere. Masterizzare si fermerebbe comunque (lo fa
        # gia' masterizza_cartella, con il nome del file), ma dopo aver detto
        # il contrario. Meglio dirlo qui, dove si sta ancora scegliendo.
        illeggibili = [os.path.basename(p) for p, d in zip(percorsi, durate) if not d]
        if illeggibili:
            return {'ok': False,
                    'errore': i18n.t('tracklist.unreadable',
                                   files=', '.join(illeggibili))}

        settori = bd.settori_totali(durate)
        minuti = bd.sectors_to_minutes(settori)
        return {
            'ok': True,
            'criterio': i18n.t(criterio) if criterio.startswith('order.') else criterio,
            'minuti': round(minuti, 1),
            'limite': bd.SAFE_MINUTES,
            'ci_sta': minuti <= bd.SAFE_MINUTES,
            'tracce': [{
                'percorso': p,
                'nome': os.path.basename(p),
                'durata': self._durata(d),
                'peso': round(os.path.getsize(p) / 1024 / 1024, 1),
            } for p, d in zip(percorsi, durate)],
        }

    def burn_unita(self) -> dict:
        """Elenca i masterizzatori collegati. Su sistemi non Windows dice perche' no."""
        bridge.entra('burn')
        if sys.platform != 'win32':
            return {'ok': False, 'errore': i18n.t('burn.only_windows'), 'unita': []}
        try:
            bd = _burndex()
            if not bd._HAS_PYWIN32:
                return {'ok': False, 'errore': i18n.t('burn.no_pywin32'), 'unita': []}
            import pythoncom
            # Ogni CoInitialize vuole il suo CoUninitialize: senza, il conteggio
            # di COM su questo thread - che e' quello della finestra, e vive
            # quanto il programma - cresce a ogni chiamata. E questa viene
            # chiamata a ogni apertura della sezione e a ogni cambio di lingua,
            # non una volta sola.
            pythoncom.CoInitialize()
            try:
                # I dizionari portano via solo stringhe e numeri: gli oggetti
                # COM non escono da qui, quindi si puo' chiudere subito dopo.
                unita = [{'indice': i, 'nome': bd.nome_unita(r)}
                         for i, r in enumerate(bd.elenca_unita())]
            finally:
                pythoncom.CoUninitialize()
            return {'ok': True, 'unita': unita,
                    'errore': '' if unita else i18n.t('burn.no_drive')}
        except Exception as exc:                       # noqa: BLE001
            return {'ok': False, 'errore': str(exc), 'unita': []}

    def burn_masterizza(self, opzioni: dict) -> dict:
        bridge.entra('burn')
        if not (opzioni.get('cartella') or '').strip():
            return {'ok': False, 'errore': i18n.t('burn.no_folder')}
        if not self._posto.occupa():
            return {'ok': False, 'errore': i18n.t('err.busy')}
        self._in_thread(self._burn_davvero, opzioni)
        return {'ok': True, 'avviato': True}

    def _burn_davvero(self, opzioni: dict) -> None:
        """Prepara l'ordine scelto e passa la palla a BurnDex.

        Se le tracce sono state riordinate, si costruisce una cartella
        temporanea di collegamenti numerati: BurnDex ordina per nome, quindi i
        prefissi impongono l'ordine voluto senza copiare un solo byte e senza
        toccare i file originali.
        """
        import shutil as _shutil
        import tempfile as _tempfile

        bd = _burndex()
        cartella = opzioni['cartella'].strip().strip('"')
        ordine = opzioni.get('ordine') or []

        temporanea = None
        da_incidere = cartella
        originali, _crit = bd.ordina_tracce(cartella)
        if ordine and ordine != [os.path.basename(p) for p in originali]:
            temporanea = _tempfile.mkdtemp(prefix='audiodexapp_burn_')
            cifre = max(2, len(str(len(ordine))))
            for i, nome in enumerate(ordine, 1):
                src = os.path.join(cartella, nome)
                dst = os.path.join(temporanea, f'{i:0{cifre}d} - {nome}')
                try:
                    os.link(src, dst)
                except OSError:
                    _shutil.copy2(src, dst)
            da_incidere = temporanea
            bridge.verso_pagina('nota', i18n.t('burn.reordered'))

        # BurnDex conta gia' tutto quello che serve - tracce misurate,
        # decodificate, scritte - per la barra che disegna a terminale: qui la
        # si ascolta e la si ripete alla pagina. Le fasi si succedono, e ogni
        # fase riparte da zero con il proprio totale: e' la verita', ed e'
        # anche cio' che ci si aspetta guardando masterizzare.
        bridge.verso_pagina('iniziaLavoro', 0)
        try:
            velocita = opzioni.get('velocita')
            unita = opzioni.get('unita')
            with _spia.ascolta(_riporta_avanzamento):
                from server.services.burn import masterizza_cartella
                masterizza_cartella(
                    da_incidere,
                    speed_x=int(velocita) if velocita not in (None, '', 'auto') else None,
                    dry_run=bool(opzioni.get('prova')),
                    auto_si=True,
                    espelli=not bool(opzioni.get('no_eject')),
                    indice_unita=int(unita) if unita not in (None, '', 'auto') else None,
                    livella=bool(opzioni.get('livella', True)),
                    rifila=bool(opzioni.get('rifila')),
                )
        finally:
            if temporanea:
                _shutil.rmtree(temporanea, ignore_errors=True)

    # ── Rimasterizzazione ────────────────────────────────────────────────────

    def pix_analizza(self, percorso: str) -> dict:
        """Diagnosi di un video piu' le risoluzioni possibili, ognuna col suo giudizio.

        Le opzioni non sono un elenco fisso: il fattore di ingrandimento e il
        commento dipendono da *questo* file. E' il punto in cui il programma e'
        piu' onesto - la stessa riga che offre il 4K dice, quando e' il caso,
        che da quella sorgente non aggiunge un solo dettaglio.
        """
        bridge.entra('pix')
        percorso = (percorso or '').strip().strip('"')
        if not os.path.isfile(percorso):
            return {'ok': False, 'errore': i18n.t('err.no_file')}

        px = _pixdex()
        info = px.probe(percorso)
        if not info or not px.e_un_filmato(info):
            return {'ok': False, 'errore': i18n.t('pix.unreadable')}

        problemi, consigliato = px.diagnosi(info)
        automatica = px.altezza_obiettivo(info, None, consigliato)

        def voce(chiave, altezza):
            fattore = px.fattore_ingrandimento(info, altezza)
            _colore, nota = px.giudizio_fattore(fattore)
            return {'chiave': chiave, 'altezza': altezza,
                    'etichetta': i18n.t(chiave), 'fattore': round(fattore, 2),
                    'nota': i18n.t(nota),
                    'livello': ('ok' if fattore <= px.FATTORE_BUONO
                                else 'molle' if fattore <= px.FATTORE_MOLLE else 'finto'),
                    'consigliata': chiave == 'quality.auto'}

        return {
            'ok': True,
            'nome': os.path.basename(percorso),
            'scheda': (f"{info['width']}×{info['height']}  ·  {info['fps']:.0f} fps"
                       f"  ·  {info['bitrate'] // 1000} kbit/s"
                       f"  ·  {self._durata(info['duration'])}"),
            'problemi': problemi,
            'preset': consigliato,
            'preset_nome': px.PRESETS[consigliato]['nome'](),
            'presets': [{'chiave': k, 'nome': px.PRESETS[k]['nome'](),
                         'desc': px.PRESETS[k]['desc']()}
                        for k in ('pulito', 'standard', 'forte', 'animazione', 'vecchio')],
            'risoluzioni': [voce('quality.auto', automatica),
                            voce('quality.none', info['height']),
                            voce('quality.hd', 1080),
                            voce('quality.2k', 1440),
                            voce('quality.4k', 2160)],
        }

    def pix_rimasterizza(self, opzioni: dict) -> dict:
        bridge.entra('pix')
        if not (opzioni.get('file') or '').strip():
            return {'ok': False, 'errore': i18n.t('err.no_file')}
        if not self._posto.occupa():
            return {'ok': False, 'errore': i18n.t('err.busy')}
        self._in_thread(self._pix_davvero, opzioni)
        return {'ok': True, 'avviato': True}

    def _pix_davvero(self, opzioni: dict) -> None:
        px = _pixdex()
        percorso = opzioni['file'].strip().strip('"')
        info = px.probe(percorso)
        if not info or not px.e_un_filmato(info):
            raise ErroreSpiegato(i18n.t('pix.unreadable'))

        preset = opzioni.get('preset') or px.diagnosi(info)[1]
        richiesta = opzioni.get('altezza')
        altezza = px.altezza_obiettivo(
            info, int(richiesta) if richiesta not in (None, '', 'auto') else None, preset)
        catena = px.catena_filtri(preset, info, altezza)
        dst = px.nome_uscita(percorso, altezza or info['height'], _rimasterizzati())

        totale = info['frames'] or 0
        bridge.verso_pagina('iniziaLavoro', totale)
        ultimo = [0.0]

        def avanzamento(n, tot, velocita):
            import time as _time
            adesso = _time.monotonic()
            if adesso - ultimo[0] < .4 and (not tot or n < tot):
                return
            ultimo[0] = adesso
            bridge.verso_pagina('avanzaLavoro', n, tot or totale or n or 1)

        ok = px.rimasterizza(info, dst, catena, bool(opzioni.get('gpu')),
                             px.CRF_DEFAULT, avanzamento=avanzamento)
        if not ok:
            bridge.verso_pagina('mostraRiepilogo', {'testo': i18n.t('pix.failed'), 'ok': False})
            return

        png = ''
        if opzioni.get('confronto', True):
            png = px.confronto(percorso, dst,
                               os.path.splitext(dst)[0] + ' [confronto].png',
                               max(info['duration'] / 3, 0.0)) or ''
        bridge.verso_pagina('pixFinito', {
            'file': os.path.basename(dst),
            'confronto': self._url_file(png) if png else '',
            'testo': i18n.t('pix.done', file=os.path.basename(dst)),
        })

    # ── Montaggio ────────────────────────────────────────────────────────────

    def clip_esegui(self, opzioni: dict) -> dict:
        bridge.entra('clip')
        # I controlli si fanno qui e non nel thread: rispondere 'avviato' per
        # poi aprire una finestra d'errore che dice che mancava il file lascia
        # il programma occupato per un istante senza motivo, e la risposta era
        # una bugia. Un rifiuto immediato torna come {'ok': False}, e la
        # pagina ne fa un avviso.
        sorgenti = [f.strip().strip('"') for f in (opzioni.get('file') or []) if f.strip()]
        if not sorgenti:
            return {'ok': False, 'errore': i18n.t('err.no_file')}
        if opzioni.get('azione') == 'unisci' and len(sorgenti) < 2:
            return {'ok': False, 'errore': i18n.t('clip.need_two')}
        mancanti = [f for f in sorgenti if not os.path.isfile(f)]
        if mancanti:
            return {'ok': False, 'errore': i18n.t('err.no_file')}
        if not self._posto.occupa():
            return {'ok': False, 'errore': i18n.t('err.busy')}
        self._in_thread(self._clip_davvero, opzioni)
        return {'ok': True, 'avviato': True}

    def _clip_davvero(self, opzioni: dict) -> None:
        cd = _clipdex()
        azione = opzioni.get('azione', 'taglia')
        sorgenti = [s.strip().strip('"') for s in (opzioni.get('file') or []) if s.strip()]
        if not sorgenti:
            raise ErroreSpiegato(i18n.t('err.no_file'))

        # ClipDex chiede a FFmpeg quanti fotogrammi ha gia' prodotto (l'opzione
        # -progress) e con quelli disegna la sua barra a terminale. Restando in
        # ascolto, gli stessi fotogrammi muovono anche questa.
        bridge.verso_pagina('iniziaLavoro', 0)
        primo = sorgenti[0]
        esito = False

        with _spia.ascolta(_riporta_avanzamento):
            if azione == 'unisci':
                if len(sorgenti) < 2:
                    raise ErroreSpiegato(i18n.t('clip.need_two'))
                dst = cd.nome_uscita(primo, 'ClipDex unito', '.mp4', cartella=_montaggi())
                esito = cd.unisci(sorgenti, dst,
                                  capitoli=bool(opzioni.get('capitoli', True)))
            elif azione == 'taglia':
                inizio = _leggi_tempo(opzioni.get('da')) or 0.0
                fine = _leggi_tempo(opzioni.get('a'))
                dst = cd.nome_uscita(primo, 'ClipDex taglio', cartella=_montaggi())
                esito = cd.taglia(primo, dst, inizio, fine,
                                  preciso=bool(opzioni.get('preciso')))
            elif azione in ('gif', 'webp'):
                dst = cd.nome_uscita(primo, f'ClipDex {azione}',
                                      '.gif' if azione == 'gif' else '.webp', cartella=_montaggi())
                funzione = cd.gif if azione == 'gif' else cd.webp
                esito = funzione(primo, dst, _leggi_tempo(opzioni.get('da')),
                                 _leggi_tempo(opzioni.get('durata')),
                                 int(opzioni.get('fps') or cd.GIF_FPS),
                                 int(opzioni.get('larghezza') or cd.GIF_LARGHEZZA))
            elif azione == 'provino':
                dst = cd.nome_uscita(primo, 'ClipDex provino', '.png', cartella=_montaggi())
                esito = cd.provino(primo, dst,
                                   int(opzioni.get('righe') or cd.PROVINO_RIGHE),
                                   int(opzioni.get('colonne') or cd.PROVINO_COLONNE))
            else:                                   # compat
                dst = cd.nome_uscita(primo, 'ClipDex compat', '.mp4', cartella=_montaggi())
                esito = cd.compat(primo, dst)

        # Il provino e' un'immagine: si mostra, invece di limitarsi a dire
        # dov'e' finita. E' tutto il senso di un provino.
        anteprima = (self._url_file(dst)
                     if esito and dst.lower().endswith(('.png', '.gif', '.webp')) else '')
        bridge.verso_pagina('clipFinito', {
            'ok': bool(esito),
            'file': os.path.basename(dst),
            'anteprima': anteprima,
            'testo': i18n.t('clip.done' if esito else 'clip.failed',
                            file=os.path.basename(dst)),
        })

    # ── Selettori di file ────────────────────────────────────────────────────

    def scegli_file(self, multi: bool = False) -> dict:
        """Apre il selettore di file del sistema, per uno o piu' video."""
        try:
            # L'elenco delle estensioni sta negli attrezzi condivisi, quindi
            # aprire il selettore non fa piu' caricare il motore di montaggio
            # per intero - con dentro Rich - solo per sapere come si chiamano i
            # file video.
            tipi = ('Video (' + ' '.join(f'*{e}' for e in sorted(_VIDEO_EXTS)) + ')',
                    'Audio (*.m4a;*.mp3;*.opus;*.wav;*.flac)', 'Tutti (*.*)')
            scelti = bridge.attuale().create_file_dialog(
                _DLG_APRI, allow_multiple=bool(multi), file_types=tipi)
        except Exception as exc:                # noqa: BLE001
            return {'ok': False, 'errore': str(exc), 'file': []}
        return {'ok': True, 'file': list(scelti) if scelti else []}

    @staticmethod
    def _url_file(percorso: str) -> str:
        """Trasforma un percorso di Windows in un indirizzo che la pagina apre.

        Il cancelletto va protetto perche' in un indirizzo separa l'ancora:
        un file che ne contiene uno nel nome verrebbe troncato li'.
        """
        if not percorso:
            return ''
        pieno = os.path.abspath(percorso).replace('\\', '/')
        return 'file:///' + pieno.replace('#', '%23').replace('?', '%3F')

    # ── Utilita' interne ─────────────────────────────────────────────────────

    def _in_thread(self, funzione, *argomenti) -> None:
        """Fa girare il lavoro fuori dal thread della finestra.

        Il posto e' gia' stato preso da ``_occupa()`` prima di arrivare qui, e
        qui lo si rende: prenderlo dentro al thread lo lascerebbe libero per
        tutto il tempo fra la risposta alla pagina e la partenza del thread, che
        e' esattamente la fessura che ``_occupa()`` serve a chiudere.

        L'output dei moduli viene dirottato al log solo per la durata del
        lavoro: farlo per sempre catturerebbe anche i messaggi di pywebview,
        che nel diario di un download non c'entrano niente.

        Il thread eredita l'indirizzo di sezione con ``bridge.entra()``: quello del
        chiamante non arriva qui da solo, e senza, ogni riferimento di questo
        lavoro finirebbe nella sezione Audio per ripiego.
        """
        dove = bridge.qui()

        def guscio():
            bridge.entra(dove)
            bridge.verso_pagina('cambiaStato', 'working')
            diario = Diario(dove)
            vecchio_out, vecchio_err = sys.stdout, sys.stderr
            sys.stdout = sys.stderr = diario
            try:
                funzione(*argomenti)
                bridge.verso_pagina('cambiaStato', 'done')
            except Exception as exc:
                bridge.verso_pagina('erroreLavoro', self._scheda_errore(exc))
                bridge.verso_pagina('cambiaStato', 'error')
            finally:
                diario.flush()
                sys.stdout, sys.stderr = vecchio_out, vecchio_err
                self._posto.libera()

        threading.Thread(target=guscio, daemon=True).start()

    @staticmethod
    def _scheda_errore(exc: Exception) -> dict:
        """Prepara cio' che la finestra dell'errore deve mostrare.

        Due forme, e la differenza conta. Un ``ErroreSpiegato`` e' una
        richiesta che non si poteva soddisfare e che il programma sa gia'
        raccontare: si mostra la sua frase e basta, perche' il traceback sotto
        direbbe solo in che riga di Python e' scritta. Tutto il resto e' un
        guasto: la causa la indovina ``classifica_errore`` leggendo il testo
        tecnico, e il testo tecnico resta allegato, perche' e' quello che si
        copia per cercarlo in rete.

        Il traceback intero viene anche scritto nel log del lavoro: la
        finestra si chiude, il file no.
        """
        if isinstance(exc, ErroreSpiegato):
            return {'titolo': i18n.t('err.title'), 'causa': str(exc), 'dettaglio': ''}

        tecnico = traceback.format_exc()
        logging.getLogger(_LOG_DI.get(bridge.qui(), 'mediadex')).error(tecnico)
        return {
            'titolo': i18n.t('err.title'),
            # Si classifica sul traceback intero e non sul solo str(exc):
            # la parola che dice di che famiglia si tratta - il nome del
            # modulo mancante, l'HRESULT, il codice HTTP - sta spesso in una
            # riga di mezzo, e l'ultima riga da sola la perderebbe.
            'causa': classifica_errore(f'{exc}\n{tecnico}'),
            'dettaglio': tecnico.strip(),
        }

    @staticmethod
    def _miniatura(video_id) -> str:
        """Indirizzo della miniatura, ricavato dall'identificativo del video.

        YouTube le serve a un indirizzo prevedibile, quindi non serve nessuna
        chiamata in piu': l'identificativo sta gia' dentro la entry che il
        motore produce, e il motore non va toccato per averla.
        """
        return f'https://i.ytimg.com/vi/{video_id}/mqdefault.jpg' if video_id else ''

    @staticmethod
    def _viste(numero) -> str:
        """Abbrevia il numero di visualizzazioni: 1.243.905 diventa 1,2 Mln."""
        try:
            n = int(numero or 0)
        except (TypeError, ValueError):
            return ''
        if n >= 1_000_000_000:
            return f'{n / 1_000_000_000:.1f}'.replace('.', ',') + ' Mrd'
        if n >= 1_000_000:
            return f'{n / 1_000_000:.1f}'.replace('.', ',') + ' Mln'
        if n >= 1_000:
            return f'{n / 1_000:.0f} K'
        return str(n) if n else ''

    @staticmethod
    def _durata(secondi) -> str:
        try:
            s = int(secondi or 0)
        except (TypeError, ValueError):
            return ''
        if not s:
            return ''
        ore, resto = divmod(s, 3600)
        minuti, sec = divmod(resto, 60)
        return f'{ore}:{minuti:02d}:{sec:02d}' if ore else f'{minuti}:{sec:02d}'
