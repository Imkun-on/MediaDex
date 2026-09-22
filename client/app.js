/* Nucleo della pagina: testi, sezioni, avanzamento, avvisi, avvio.
 *
 * Regola unica, valida anche per i quattro file di features/: qui non si
 * decide niente di importante. La pagina raccoglie cio' che si scrive, lo
 * passa a Python, e mostra cio' che Python risponde. Ogni scelta vera - se un
 * URL sia una playlist, quale risoluzione abbia senso, se un ordine di tracce
 * ci stia su un CD - sta gia' nei moduli, ed e' li' che deve restare:
 * duplicarla qui significherebbe due risposte diverse alla stessa domanda.
 *
 * Dove finisce quello che va storto
 *     In due posti, e la divisione e' netta.
 *
 *     Un rifiuto immediato - cartella vuota, link non valido, nessuna traccia
 *     spuntata - e' un AVVISO in basso a destra: si legge in un secondo, non
 *     interrompe niente, e chi lo ha provocato sa gia' cosa ha fatto.
 *
 *     Un lavoro che cade DOPO essere partito e' una FINESTRA. Un avviso che
 *     sparisce in sette secondi non si fa in tempo a leggerlo, e soprattutto
 *     non si fa in tempo a copiarne il testo tecnico. Prima quel testo stava
 *     nella scheda del diario, sepolto sotto duecento righe di Rich; adesso
 *     arriva da solo, accanto alla sua causa in italiano.
 */

let TESTI = {};
let SEZIONE = 'audio';

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

/* La frase dietro una chiave.
 *
 * Il catalogo arriva da Python gia' piatto - 'chiave': 'frase' - e in
 * italiano, che e' l'unica lingua da quando il menu per cambiarla non c'e'
 * piu'. La stessa funzione, con lo stesso ripiego, esiste anche di la':
 * server/config/i18n.py.
 *
 * Una chiave che non esiste torna com'e' scritta, visibile a schermo: un
 * errore di battitura si vede subito invece di far saltare qualcosa. */
function t(chiave, valori) {
  let testo = TESTI[chiave];
  if (testo === undefined) testo = chiave;
  if (valori) {
    for (const [k, v] of Object.entries(valori)) testo = testo.split('{' + k + '}').join(v);
  }
  // I testi del catalogo portano il markup di Rich, che a schermo non serve.
  return testo.replace(/\[\/?[a-z_]+\]/g, '');
}

/* ── Le quattro stanze ────────────────────────────────────────────────────── */

/* Di ogni sezione si tiene qui cio' che Python deve poter raggiungere: la sua
 * barra, la sua spia, la sua parola di stato. Sono cercati per classe dentro
 * la sezione e non per identificatore, cosi' le quattro copie non hanno
 * bisogno di quattro nomi diversi e non si possono scambiare per sbaglio. */
const SEZIONI = {};

/* Quello che ogni sezione registra di se': come rimettere a posto i bottoni
 * quando un lavoro finisce, come riempirsi di testo al primo disegno, cosa fa
 * Ctrl+Invio. Erano tre catene di "if (window.traduciBurn)": un elenco e' piu'
 * corto e non si dimentica il quarto. */
const RIABILITA = {};
const TRADUCI = {};
const SCORCIATOIE = {};

function registraSezione(nome, parti) {
  if (parti.riabilita) RIABILITA[nome] = parti.riabilita;
  if (parti.traduci) TRADUCI[nome] = parti.traduci;
  if (parti.scorciatoia) SCORCIATOIE[nome] = parti.scorciatoia;
}

function censisciSezioni() {
  $$('.sezione[data-sez]').forEach((radice) => {
    SEZIONI[radice.dataset.sez] = {
      nome: radice.dataset.sez,
      radice,
      stato: 'idle',
      avanzamento: radice.querySelector('.avanzamento'),
      barra: radice.querySelector('.avanzamento .cursa'),
      testo: radice.querySelector('.avanzamento-testo'),
      spia: radice.querySelector('.titolo-pannello .spia'),
      parola: radice.querySelector('.titolo-pannello .stato'),
    };
  });
}

function traduciPagina() {
  $$('[data-t]').forEach((el) => { el.textContent = t(el.dataset.t); });
  Object.values(SEZIONI).forEach((s) => {
    if (s.parola) s.parola.textContent = t('status.' + s.stato);
  });
  Object.values(TRADUCI).forEach((fn) => fn());
  aggiornaVoci();
}

/* ── Cambio sezione ───────────────────────────────────────────────────────── */

function cambiaSezione(nome, immediato) {
  if (nome === SEZIONE && !immediato) return;
  const uscente = document.querySelector('.sezione.attiva');
  SEZIONE = nome;
  $$('.voce').forEach((v) => v.classList.toggle('attiva', v.dataset.va === nome));

  // Prima la sezione che se ne va sfuma e arretra, poi entra la nuova
  // dall'altro lato: si capisce di essersi spostati, invece di ritrovarsi
  // altrove senza sapere come. Il ritardo e' quello dell'animazione di
  // uscita, non un numero scelto a caso.
  const entra = () => {
    $$('.sezione').forEach((s) => {
      s.classList.remove('uscita');
      s.classList.toggle('attiva', s.dataset.sez === nome);
    });
  };

  if (uscente && uscente.dataset.sez !== nome && !immediato) {
    uscente.classList.add('uscita');
    uscente.classList.remove('attiva');
    setTimeout(entra, 200);
  } else {
    entra();
  }
}

/* La targhetta accanto alla voce del menu.
 *
 * E' cio' che ha preso il posto della spia unica del diario. Un lavoro alla
 * volta puo' essere partito in una stanza in cui adesso non si sta: senza
 * questa, per sapere dove sta girando bisognerebbe entrare in tutte e quattro
 * a controllare. */
function aggiornaVoci() {
  const TONO = { working: 'attesa', error: 'guasto' };
  const TESTO = { working: 'targhetta.lavora', error: 'targhetta.guasto' };
  $$('[data-targhetta]').forEach((tg) => {
    const s = SEZIONI[tg.dataset.targhetta];
    const stato = s ? s.stato : 'idle';
    tg.className = 'targhetta-menu ' + (TONO[stato] || 'spenta');
    tg.textContent = TESTO[stato] ? t(TESTO[stato]) : '';
  });
}

/* ── La porta da cui entra tutto quello che dice Python ───────────────────── */

/* Un ingresso solo, e l'indirizzo per primo.
 *
 * Prima Python chiamava direttamente window.iniziaLavoro(...) e simili: undici
 * nomi globali, e nessuno di loro sapeva a quale sezione si riferisse. Finche'
 * la barra era una sola andava bene. Adesso che ogni stanza ha la sua, il
 * messaggio deve dire a chi e' diretto, e lo dice qui - prima del resto, come
 * l'indirizzo su una busta.
 *
 * Un evento sconosciuto viene lasciato cadere senza rumore: e' il caso di una
 * versione di Python piu' nuova della pagina, che non deve far saltare niente. */
const EVENTI = {};

function ascolta(nome, funzione) { EVENTI[nome] = funzione; }

window.__instrada = (dove, nome, argomenti) => {
  const s = SEZIONI[dove];
  const funzione = EVENTI[nome];
  if (!s || !funzione) return;
  funzione.apply(null, [s].concat(argomenti || []));
};

ascolta('cambiaStato', (s, stato) => {
  s.stato = stato;
  if (s.spia) s.spia.className = 'spia ' + (stato === 'idle' ? '' : stato);
  if (s.parola) s.parola.textContent = t('status.' + stato);
  aggiornaVoci();

  // Un lavoro alla volta in tutto il programma, quindi mentre gira si spengono
  // i comandi di tutte le sezioni, non solo di quella che lavora. I bottoni
  // della finestra restano accesi: e' dentro .corpo che si comanda, e una
  // finestra che non si lascia chiudere sarebbe una trappola.
  const inCorso = stato === 'working';
  $$('.corpo .bottone.pieno, .corpo .bottone.contorno').forEach((b) => { b.disabled = inCorso; });
  if (!inCorso) Object.values(RIABILITA).forEach((fn) => fn());

  s.avanzamento.classList.toggle('visibile', inCorso);
  if (inCorso) {
    // La barra riparte da zero, non da un valore finto: il primo numero vero
    // arriva dal motore entro una frazione di secondo.
    s.barra.style.width = '0%';
    s.barra.classList.remove('attesa');
    s.testo.textContent = t('status.working') + '…';
  }
});

ascolta('iniziaLavoro', (s, totale) => {
  s.avanzamento.classList.add('visibile');
  // 'attesa' e' il caso in cui il motore non ha ancora detto quanto sia il
  // lavoro: la barra non finge un avanzamento, resta una striscia spenta
  // finche' non arriva il primo conteggio.
  s.barra.classList.toggle('attesa', !totale);
  s.barra.style.width = totale ? '0%' : '';
  s.testo.textContent = totale
    ? t('lavoro.avanzo', { fatte: 0, totale }) : t('status.working') + '…';
  if (window.audioPreparaSchede) window.audioPreparaSchede(s);
});

/* L'avanzamento vero.
 *
 *   fatte, totale   le unita' del motore: tracce, fotogrammi, brani incisi.
 *   frazione        opzionale, da 0 a 1: il riempimento reale della barra
 *                   quando e' piu' fine del conteggio a unita' intere - i
 *                   byte di un download stanno dentro una traccia sola.
 *                   Se e' null il motore non sa quanto manca, e la barra
 *                   resta ferma invece di inventare.
 *   testo           opzionale: cosa sta lavorando in questo momento.
 */
ascolta('avanzaLavoro', (s, fatte, totale, frazione, testo) => {
  const noto = frazione !== null && frazione !== undefined;
  s.barra.classList.toggle('attesa', !noto && !totale);
  if (noto) {
    s.barra.style.width = (Math.max(0, Math.min(1, frazione)) * 100).toFixed(1) + '%';
  } else if (totale) {
    s.barra.style.width = Math.round((fatte / totale) * 100) + '%';
  }
  const conteggio = totale ? t('lavoro.avanzo', { fatte, totale }) : '';
  s.testo.textContent =
    [testo || '', conteggio].filter(Boolean).join('  ·  ') || t('status.working') + '…';
});

ascolta('mostraRiepilogo', (s, dati) => {
  s.testo.textContent = dati.testo;
  s.barra.classList.remove('attesa');
  s.barra.style.width = '100%';
  avvisa(dati.testo, dati.ok ? 'ok' : 'fail');
});

/* Una nota di servizio durante il lavoro: niente e' andato storto, e' successo
 * qualcosa che vale la pena sapere - le tracce sono state riordinate, il CD e'
 * stato espulso. Avviso neutro, senza barra colorata. */
ascolta('nota', (s, testo) => avvisa(testo));

/* Il lavoro e' caduto. Questa finestra e' l'intero sostituto della scheda dei
 * log: sopra la causa in italiano, sotto il testo tecnico com'e' arrivato. */
ascolta('erroreLavoro', (s, e) => {
  const corpo = [];
  if (e.file) corpo.push(riquadroPercorso(t('err.file'), e.file));
  corpo.push(paragrafo(e.causa || t('err.unknown')));
  if (e.dettaglio) corpo.push(riquadroDettaglio(t('err.detail'), e.dettaglio));
  finestra({
    icona: 'errore', tono: 'errore', titolo: e.titolo || t('err.title'),
    corpo,
    azioni: [{ testo: t('comune.chiudi'), tono: 'pieno', icona: 'spunta' }],
  });
});

/* ── Avvisi a comparsa ────────────────────────────────────────────────────── */

function avvisa(testo, tipo) {
  const box = el('div', 'avviso ' + (tipo || ''));
  box.appendChild(el('div', '', testo));
  $('#avvisi').appendChild(box);
  // Gli errori restano piu' a lungo: si vuole avere il tempo di leggerli.
  setTimeout(() => {
    box.classList.add('uscita');
    setTimeout(() => box.remove(), 300);
  }, tipo === 'fail' ? 7000 : 4000);
}

/* Il rifiuto immediato di una sezione: non e' un lavoro caduto, e' una
 * richiesta che non e' nemmeno partita. Avviso, e la spia torna rossa. */
function errore(messaggio, dove) {
  avvisa(messaggio, 'fail');
  window.__instrada(dove || SEZIONE, 'cambiaStato', ['error']);
}

/* ── Stati vuoti ──────────────────────────────────────────────────────────── */

function statoVuoto(testo) {
  const box = el('div', 'vuoto');
  box.appendChild(icona('i-vuoto'));
  box.appendChild(el('div', '', testo));
  return box;
}

// Cio' che i file di features/ usano.
window.statoVuoto = statoVuoto;
window.avvisa = avvisa;
window.errore = errore;
window.t = t;
window.$ = $;
window.registraSezione = registraSezione;
window.ascolta = ascolta;
// Si esporta la funzione, non un involucro che la chiama.
//
// Qui c'era `window.cambiaSezione = (nome) => cambiaSezione(nome)`, e sembrava
// innocuo. Non lo era: in uno script classico una `function` dichiarata in cima
// E' gia' una proprieta' di window, quindi quella riga la sostituiva con
// l'involucro - e il `cambiaSezione` dentro l'involucro, risolvendosi di nuovo
// su window, chiamava l'involucro. Ricorsione infinita alla prima chiamata.
//
// Il guasto non si vedeva dove ci si aspetterebbe. La prima a chiamarla era
// `avvia()`, quindi saltava tutto quello che veniva dopo: i clic sulle voci del
// menu non venivano mai collegati, e il velo di avvio se ne andava solo per la
// rete di sicurezza dei dodici secondi. La finestra sembrava a posto e non
// rispondeva al menu.
window.cambiaSezione = cambiaSezione;

/* ── Avvio ────────────────────────────────────────────────────────────────── */

const T_AVVIO = performance.now();

/* I passi dell'avvio, contati.
 *
 * Sono i pezzi che vanno messi insieme prima che l'interfaccia sia usabile,
 * ed e' un elenco chiuso e noto: per questo la barra puo' dire un numero vero
 * invece di scorrere avanti e indietro. Ogni chiamata a passoAvvio() e' un
 * pezzo davvero finito, non un'attesa a tempo. */
const PASSI_AVVIO = 7;
let passiFatti = 0;

/* ── Come si muove la barra ───────────────────────────────────────────────── */
/*
 * Tre numeri, e servono tutti e tre.
 *
 *   quotaVera      quanti dei sette passi sono finiti davvero.
 *   quotaTetto     fin dove la barra ha il permesso di arrivare aspettando il
 *                  passo successivo. Scivola in avanti piano per conto suo.
 *   quotaMostrata  quello che si vede, che a ogni fotogramma si avvicina al
 *                  tetto di una frazione della distanza che manca.
 *
 * Perche' non basta scrivere la quota vera e lasciar fare a una transizione
 * CSS. Perche' i sette passi non sono distribuiti nel tempo: i primi tre
 * arrivano uno dietro l'altro in mezzo secondo, poi c'e' un buco di diversi
 * secondi mentre Python prepara la risposta, e gli ultimi quattro arrivano
 * tutti insieme alla fine. Una barra che salta al 40% e poi resta immobile per
 * sei secondi si legge come «piantata», non come «sta caricando».
 *
 * Cosa promette, e cosa no
 *     Non torna MAI indietro, e non arriva in fondo prima che il lavoro sia
 *     finito: il tetto puo' consumare al massimo l'85% della distanza che
 *     manca, quindi finche' c'e' un passo da fare la barra non puo' toccare la
 *     fine. Quello che non promette e' che la posizione sia una percentuale
 *     esatta di lavoro svolto: mentre aspetta si muove per dire che sta
 *     aspettando. E' il compromesso onesto fra una barra che mente e una barra
 *     che sembra rotta - l'alternativa peggiore e' quella che scorre avanti e
 *     indietro a vuoto, che non dice niente e lo dice con enfasi.
 */
const TETTO_MAX = 0.85;     // quanta della distanza che manca si puo' consumare aspettando
const SCIVOLO = 0.004;      // quanto avanza il tetto a ogni fotogramma
const RINCORSA = 0.035;     // quanto si avvicina al tetto quello che si vede

let quotaVera = 0;
let quotaTetto = 0;
let quotaMostrata = 0;

function traguardo(q) {
  if (q <= quotaVera) return;          // mai indietro
  quotaVera = Math.min(q, 1);
  // Il tetto non si riabbassa: se lo scivolamento lo aveva gia' portato piu'
  // avanti del passo appena concluso, resta dov'e' e la barra non arretra.
  quotaTetto = Math.max(quotaTetto, quotaVera);
}

function animaBarra() {
  const tettoMax = quotaVera + (1 - quotaVera) * TETTO_MAX;
  quotaTetto = Math.min(tettoMax, quotaTetto + (tettoMax - quotaTetto) * SCIVOLO);
  quotaMostrata += (quotaTetto - quotaMostrata) * RINCORSA;

  const b = document.querySelector('.avvio-barra span');
  if (b) b.style.width = (quotaMostrata * 100).toFixed(2) + '%';
  if (quotaMostrata < 0.999) requestAnimationFrame(animaBarra);
}

function passoAvvio() {
  passiFatti = Math.min(passiFatti + 1, PASSI_AVVIO);
  traguardo(passiFatti / PASSI_AVVIO);
}

/* Toglie il velo di caricamento. Si puo' chiamare quante volte si vuole.
 *
 * L'elemento non viene rimosso subito ma dopo la dissolvenza, altrimenti
 * sparirebbe di scatto; e viene rimosso davvero, non solo nascosto, perche'
 * un rettangolo a tutto schermo che resta nell'albero e' un rischio inutile
 * per i clic.
 *
 * I 500 ms minimi non sono un'attesa finta: su una macchina veloce la pagina
 * e' pronta in un attimo, e un velo che appare e sparisce in cinquanta
 * millesimi si vede come uno sfarfallio, non come un caricamento. */
function togliVelo() {
  const v = document.getElementById('velo-avvio');
  if (!v || v.dataset.uscita) return;
  v.dataset.uscita = '1';
  const resta = Math.max(0, 500 - (performance.now() - T_AVVIO));
  setTimeout(() => {
    /* La barra si chiude a mano prima che il velo se ne vada.
     *
     * Non e' una bugia: a questo punto il caricamento E' finito davvero, e
     * l'unica ragione per cui la barra non era ancora in fondo e' che ci
     * stava arrivando piano. Senza questa riga l'ultima cosa che si vede
     * mentre il velo sfuma e' una barra a tre quarti, che si legge come un
     * lavoro lasciato a meta' proprio nell'istante in cui e' completo. */
    const b = document.querySelector('.avvio-barra span');
    if (b) b.style.width = '100%';

    v.classList.add('via');
    setTimeout(() => v.remove(), 600);
  }, resta);
}

function avvia() {
  /* La barra comincia a muoversi subito, prima ancora che ci sia qualcosa da
   * raccontare. Il primo traguardo e' minuscolo di proposito: serve solo a
   * dare al tetto un valore diverso da zero, perche' con tetto a zero la barra
   * resterebbe immobile e il primo fotogramma del velo sarebbe fermo. */
  traguardo(0.03);
  requestAnimationFrame(animaBarra);

  /* Se l'apertura si inceppa - un errore nel motore, una chiamata che non
   * torna - il velo deve comunque andarsene: meglio un'interfaccia a meta',
   * che si vede e si puo' chiudere, che una schermata di caricamento
   * perpetua. E' una rete di sicurezza, non una scadenza: deve scattare solo
   * quando qualcosa si e' rotto davvero, e al primo avvio dopo l'installazione
   * Windows legge dal disco un centinaio di megabyte prima di arrivare qui. */
  setTimeout(togliVelo, 60000);
  censisciSezioni();
  passoAvvio();                       // 1. la pagina e i suoi script ci sono

  window.addEventListener('pywebviewready', async () => {
    passoAvvio();                     // 2. il ponte con Python risponde
    const dati = await window.pywebview.api.avvio();
    passoAvvio();                     // 3. testi e cartelle sono arrivati
    TESTI = dati.testi;

    // Il video di sfondo, se il file e' sul disco. Si aggiunge solo dopo che
    // il primo fotogramma e' pronto: senza, si vedrebbe un rettangolo nero
    // coprire i gradienti per il tempo del caricamento.
    if (dati.sfondo) {
      const v = $('#video-sfondo');
      v.addEventListener('loadeddata', () => v.classList.add('acceso'), { once: true });
      v.src = dati.sfondo;
    }

    window.initAudio();
    passoAvvio();                     // 4. la sezione Audio e' pronta
    window.initBurn(dati.cartella);
    window.initPix();
    window.initClip();
    passoAvvio();                     // 5. e anche le altre tre
    traduciPagina();
    if (window.potenziaTendine) window.potenziaTendine();
    passoAvvio();                     // 6. tutto e' nella lingua giusta
    cambiaSezione('audio', true);

    $$('.voce[data-va]').forEach((v) =>
      v.addEventListener('click', () => cambiaSezione(v.dataset.va)));

    $('#apri-risultati').addEventListener('click', async () => {
      const esito = await window.pywebview.api.apri_risultati();
      if (!esito.ok) avvisa(esito.errore, 'fail');
    });

    // Ctrl+Invio avvia l'operazione della sezione aperta: chi ha appena
    // riempito il modulo ha le mani sulla tastiera, non sul mouse. Se c'e' una
    // finestra aperta non vale: li' Invio ha gia' il suo significato.
    document.addEventListener('keydown', (e) => {
      if (e.key !== 'Enter' || !(e.ctrlKey || e.metaKey)) return;
      if (finestraAperta()) return;
      e.preventDefault();
      const fn = SCORCIATOIE[SEZIONE];
      if (fn) fn();
    });

    // Trascinare un link dal browser dentro la finestra: e' il gesto naturale,
    // e senza questo resterebbe l'unica cosa che ci si aspetta e non funziona.
    let dentro = 0;
    const velo = $('#velo-trascina');
    window.addEventListener('dragenter', (e) => {
      e.preventDefault(); dentro++; velo.classList.add('visibile');
    });
    window.addEventListener('dragover', (e) => e.preventDefault());
    window.addEventListener('dragleave', () => {
      if (--dentro <= 0) { dentro = 0; velo.classList.remove('visibile'); }
    });
    window.addEventListener('drop', (e) => {
      e.preventDefault(); dentro = 0; velo.classList.remove('visibile');
      const testo = (e.dataTransfer.getData('text/uri-list')
                  || e.dataTransfer.getData('text/plain') || '').trim();
      if (!testo) return;
      cambiaSezione('audio');
      window.audioAccettaLink(testo);
    });

    // Ultima riga: da qui l'interfaccia e' disegnata, tradotta e reattiva.
    // Toglierlo prima avrebbe scoperto un'interfaccia che non risponde ancora
    // ai clic, che e' peggio di un attimo di attesa in piu'.
    passoAvvio();                     // 7. risponde ai comandi: si puo' usare
    togliVelo();
  });
}
