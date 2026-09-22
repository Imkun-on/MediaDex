/* La finestra modale, una sola, riempita di volta in volta.
 *
 * Perche' esiste
 *     Qui dentro non c'e' piu' una scheda dei log. Finche' c'era, un errore
 *     era una riga rossa in mezzo ad altre duecento: si perdeva, e su un
 *     download da cinquanta brani si perdeva davvero. Adesso un lavoro che
 *     cade apre questa, e per andarsene bisogna guardarla.
 *
 * Perche' una sola
 *     I momenti in cui il programma deve fermarsi sono pochi e si assomigliano
 *     tutti: un errore con la sua causa, un riepilogo, una conferma. Averne
 *     una struttura per caso vorrebbe dire tre posti in cui allineare la
 *     stessa animazione, lo stesso bordo, lo stesso tasto Esc.
 *
 * Cosa NON fa
 *     Non decide niente. Riceve un titolo, dei pezzi di contenuto e un elenco
 *     di bottoni, e li mette al loro posto. Il significato - quando un guaio
 *     merita la finestra e quando basta un avviso - sta in app.js e nelle
 *     sezioni, che e' dove si capisce leggendo.
 *
 * Le briciole di costruzione (el, paragrafo, riquadro…) stanno qui e non in
 * app.js perche' servono soprattutto a riempire questa finestra, e tenerle
 * accanto a chi le usa risparmia un viaggio fra i file.
 */

/* Costruttore minimo di elementi: tag, classe, testo. Il testo passa SEMPRE per
 * textContent, mai per innerHTML. Non e' zelo: qui dentro finiscono titoli di
 * video presi da YouTube, nomi di file scelti da chi usa il programma e
 * messaggi d'errore di FFmpeg. Nessuno dei tre deve poter diventare markup. */
function el(tag, classe, testo) {
  const nodo = document.createElement(tag);
  if (classe) nodo.className = classe;
  if (testo !== undefined && testo !== null) nodo.textContent = testo;
  return nodo;
}

function icona(nome, classe) {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('class', classe || 'icona');
  const uso = document.createElementNS('http://www.w3.org/2000/svg', 'use');
  uso.setAttribute('href', '#' + nome);
  svg.appendChild(uso);
  return svg;
}

function paragrafo(testo) {
  return el('p', '', testo);
}

/* Il riquadro con un percorso dentro: su quale file si stava lavorando, dove
 * sono finiti i brani. Resta selezionabile perche' la prima cosa che se ne fa
 * e' copiarlo. */
function riquadroPercorso(etichetta, percorso) {
  const box = el('div', 'riquadro-cartella');
  if (etichetta) box.appendChild(el('div', 'etichetta-piccola', etichetta));
  box.appendChild(el('div', 'percorso', percorso));
  return box;
}

/* Il testo tecnico di un errore, cosi' com'e' arrivato.
 *
 * Sta in un riquadro a parte, con un'etichetta sopra, per una ragione precisa:
 * chi legge deve capire al primo sguardo che quella non e' la spiegazione ma
 * la citazione. Messo in mezzo alla prosa sembrerebbe una frase del programma,
 * e invece e' una frase di qualcun altro - FFmpeg, yt-dlp, Windows - spesso in
 * inglese e spesso oscura.
 *
 * Resta selezionabile e va a capo dove capita, perche' la prima cosa che se ne
 * fa e' copiarlo per cercarlo in rete. E' quello che prima si andava a pescare
 * nel diario: adesso arriva da solo, gia' accanto alla sua causa. */
function riquadroDettaglio(etichetta, testo) {
  const box = el('div', 'riquadro-dettaglio');
  if (etichetta) box.appendChild(el('div', 'etichetta-piccola', etichetta));
  box.appendChild(el('div', 'dettaglio-tecnico', testo));
  return box;
}

/* ── La finestra ──────────────────────────────────────────────────────────── */

let _suChiusura = null;

function finestra(opzioni) {
  const velo = document.getElementById('velo-finestra');
  const riquadro = document.getElementById('finestra');
  const corpo = document.getElementById('finestra-corpo');
  const azioni = document.getElementById('finestra-azioni');

  /* Se una finestra era gia' aperta la si chiude PRIMA di svuotare il corpo,
   * cosi' la sua chiusura viene eseguita invece di essere saltata. Capita
   * davvero: due lavori che finiscono male a pochi istanti l'uno dall'altro
   * chiamano questa funzione due volte di fila. */
  if (velo.classList.contains('visibile')) chiudiFinestra();

  riquadro.className = 'finestra' + (opzioni.tono ? ' ' + opzioni.tono : '');
  document.getElementById('finestra-titolo').textContent = opzioni.titolo || '';
  riquadro.querySelector('.finestra-testa .icona use')
    .setAttribute('href', '#i-' + (opzioni.icona || 'avviso'));

  corpo.innerHTML = '';
  (opzioni.corpo || []).forEach((pezzo) => {
    if (pezzo === null || pezzo === undefined) return;
    corpo.appendChild(typeof pezzo === 'string' ? paragrafo(pezzo) : pezzo);
  });

  azioni.innerHTML = '';
  (opzioni.azioni || []).forEach((a) => {
    const bottone = el('button', 'bottone ' + (a.tono || 'contorno'));
    if (a.icona) bottone.appendChild(icona('i-' + a.icona));
    bottone.appendChild(el('span', '', a.testo));
    bottone.addEventListener('click', () => {
      // Chi non chiude esplicitamente resta aperto: serve al bottone «Apri la
      // cartella», che si preme e poi si torna a guardare quello che c'e'.
      if (a.chiudi !== false) chiudiFinestra();
      if (a.azione) a.azione();
    });
    azioni.appendChild(bottone);
  });

  _suChiusura = opzioni.suChiusura || null;
  velo.classList.add('visibile');
  corpo.scrollTop = 0;
  // Il primo bottone prende il fuoco: chi ha appena letto ha le mani sulla
  // tastiera, e Invio deve fare la cosa piu' probabile.
  const primo = azioni.querySelector('.bottone.pieno') || azioni.querySelector('.bottone');
  if (primo) primo.focus();
}

function chiudiFinestra() {
  const velo = document.getElementById('velo-finestra');
  if (!velo.classList.contains('visibile')) return;
  velo.classList.remove('visibile');
  const chiusura = _suChiusura;
  _suChiusura = null;
  if (chiusura) chiusura();
}

function finestraAperta() {
  return document.getElementById('velo-finestra').classList.contains('visibile');
}

// Esc chiude, ed e' l'unico modo di uscire senza premere un bottone: cliccare
// fuori no, perche' su un errore che si e' appena aperto un clic distratto a
// lato lo farebbe sparire prima di averlo letto - cioe' esattamente il difetto
// del diario, ricreato daccapo.
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') chiudiFinestra();
});

window.el = el;
window.icona = icona;
window.paragrafo = paragrafo;
window.riquadroPercorso = riquadroPercorso;
window.riquadroDettaglio = riquadroDettaglio;
window.finestra = finestra;
window.chiudiFinestra = chiudiFinestra;
window.finestraAperta = finestraAperta;
