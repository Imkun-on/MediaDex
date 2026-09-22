/* Sezione Audio: cerca, sceglie, scarica.
 *
 * L'unica delle quattro che lavora su molte cose insieme, e da li' viene tutto
 * quello che ha di diverso: le schede spuntabili, il filo di avanzamento sotto
 * ciascuna, la pastiglia che dice a che punto e' quella traccia. La barra
 * grande in cima dice a che punto e' l'insieme; queste dicono a che punto e'
 * ognuno, ed e' l'unico modo di capire, su una playlist da cinquanta brani,
 * quale sia quello rimasto indietro.
 */

/* Quali tracce sono spuntate. Vive qui e non nel documento perche' deve
 * sopravvivere al ridisegno delle schede quando si cambia lingua. */
let SCELTI = new Set();
let SCHEDE = [];

const FORMATI = { audio: ['m4a', 'mp3', 'opus'], video: ['mp4', 'mkv'] };

function initAudio() {
  const $ = window.$;
  aggiornaFormati();

  $('#modo').addEventListener('change', aggiornaEtichettaIngresso);
  $('#media').addEventListener('change', aggiornaFormati);
  $('#analizza').addEventListener('click', analizza);
  $('#scarica').addEventListener('click', scarica);
  $('#ingresso').addEventListener('keydown', (e) => { if (e.key === 'Enter') analizza(); });
  $('#tutti').addEventListener('click', () => {
    SCHEDE.forEach((_, i) => SCELTI.add(i)); aggiornaSelezione();
  });
  $('#nessuno').addEventListener('click', () => { SCELTI.clear(); aggiornaSelezione(); });

  svuotaRisultati();

  window.registraSezione('audio', {
    riabilita: aggiornaSelezione,
    scorciatoia: scarica,
    traduci: () => {
      aggiornaEtichettaIngresso();
      if (!window.$('#risultati').dataset.pieno) svuotaRisultati();
    },
  });
}

function aggiornaEtichettaIngresso() {
  const modo = window.$('#modo').value;
  window.$('#etichetta-input').textContent =
    window.t(modo === 'search' ? 'audio.input.search' : 'audio.input.url');
  window.$('#ingresso').placeholder =
    modo === 'search' ? 'Pink Floyd - Time' : 'https://www.youtube.com/watch?v=…';
}

function aggiornaFormati() {
  const media = window.$('#media').value;
  const sel = window.$('#formato');
  const prima = sel.value;
  sel.innerHTML = '';
  FORMATI[media].forEach((f) => {
    const o = document.createElement('option');
    o.value = f; o.textContent = f.toUpperCase();
    sel.appendChild(o);
  });
  if (FORMATI[media].includes(prima)) sel.value = prima;
}

async function analizza() {
  const esito = await window.pywebview.api.analizza(
    window.$('#ingresso').value, window.$('#modo').value);
  if (!esito.ok) window.errore(esito.errore, 'audio');
}

async function scarica() {
  const esito = await window.pywebview.api.scarica({
    scelti:    Array.from(SCELTI).sort((a, b) => a - b),
    formato:   window.$('#formato').value,
    media:     window.$('#media').value,
    paralleli: window.$('#paralleli').value,
    testi:     window.$('#testi').checked,
    dividi:    window.$('#dividi').checked,
  });
  if (!esito.ok) window.errore(esito.errore, 'audio');
}

/* ── Le schede dei risultati ──────────────────────────────────────────────── */

window.ascolta('mostraRisultati', (s, dati) => {
  const elenco = window.$('#risultati');
  elenco.innerHTML = '';
  elenco.dataset.pieno = '1';
  SCELTI.clear(); SCHEDE = [];
  if (!dati.voci || !dati.voci.length) { svuotaRisultati(); return; }

  dati.voci.forEach((v, i) => {
    const scheda = document.createElement('div');
    scheda.className = 'scheda';
    // A cascata invece che tutte insieme: su venti risultati e' la differenza
    // fra "e' apparso un muro" e "si sta popolando".
    scheda.style.animationDelay = Math.min(i * 22, 420) + 'ms';
    scheda.innerHTML =
      '<div class="casella"></div>' +
      '<div class="miniatura">' +
        '<div class="numero">' + String(i + 1).padStart(2, '0') + '</div>' +
        (v.durata ? '<div class="durata-sopra"></div>' : '') +
      '</div>' +
      '<div class="scheda-testo"><div class="scheda-titolo"></div>' +
        '<div class="scheda-sotto"></div></div>' +
      '<div class="pastiglia"></div><div class="filo"></div>';

    // I titoli arrivano da YouTube: si scrivono come testo, mai come HTML.
    scheda.querySelector('.scheda-titolo').textContent = v.titolo || '';
    if (v.durata) scheda.querySelector('.durata-sopra').textContent = v.durata;

    const sotto = scheda.querySelector('.scheda-sotto');
    [v.canale, v.viste ? v.viste + ' ▶' : ''].filter(Boolean).forEach((testo, k) => {
      if (k) {
        const punto = document.createElement('span');
        punto.className = 'punto'; punto.textContent = '·';
        sotto.appendChild(punto);
      }
      const span = document.createElement('span');
      span.textContent = testo;
      sotto.appendChild(span);
    });

    // La miniatura si aggiunge solo se arriva: un riquadro con l'icona rotta
    // sarebbe peggio del riquadro vuoto.
    if (v.miniatura) {
      const img = new Image();
      img.loading = 'lazy'; img.alt = '';
      img.onload = () => scheda.querySelector('.miniatura').prepend(img);
      img.src = v.miniatura;
    }

    scheda.addEventListener('click', () => commuta(i));
    SCHEDE[i] = scheda;
    SCELTI.add(i);
    elenco.appendChild(scheda);
  });
  aggiornaSelezione();
});

/* All'inizio di un lavoro le schede si azzerano: pastiglia in attesa per
 * quelle spuntate, niente per le altre. Lo chiama il nucleo, perche' e' lui a
 * sapere quando un lavoro comincia. */
window.audioPreparaSchede = (s) => {
  if (s.nome !== 'audio') return;
  SCHEDE.forEach((scheda, i) => {
    if (!scheda) return;
    scheda.classList.remove('in-corso', 'finita', 'fallita');
    const filo = scheda.querySelector('.filo');
    if (filo) filo.style.width = '0%';
    const p = scheda.querySelector('.pastiglia');
    p.className = 'pastiglia';
    p.textContent = SCELTI.has(i) ? window.t('fase.attesa') : '';
  });
};

/* Quanto e' scaricata *questa* traccia, in byte: il filo sotto la scheda. */
window.ascolta('tracciaAvanza', (s, i, frazione) => {
  const scheda = SCHEDE[i];
  if (!scheda) return;
  const filo = scheda.querySelector('.filo');
  if (filo) filo.style.width = (Math.max(0, Math.min(1, frazione)) * 100).toFixed(1) + '%';
});

window.ascolta('tracciaFase', (s, i, fase) => {
  const scheda = SCHEDE[i];
  if (!scheda) return;
  scheda.classList.add('in-corso');
  const p = scheda.querySelector('.pastiglia');
  p.className = 'pastiglia lavora';
  p.textContent = window.t('fase.' + fase);
  // La traccia che lavora si porta sotto gli occhi da sola: su una playlist da
  // cinquanta brani, cercarla a mano sarebbe assurdo.
  scheda.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
});

window.ascolta('tracciaFinita', (s, i, esito, errore) => {
  const scheda = SCHEDE[i];
  if (!scheda) return;
  scheda.classList.remove('in-corso');
  scheda.classList.add('finita');
  if (esito === 'fail') scheda.classList.add('fallita');
  const cl = esito === 'ok' ? 'ok' : esito === 'skip' ? 'skip' : 'fail';
  const p = scheda.querySelector('.pastiglia');
  p.className = 'pastiglia ' + cl;
  p.textContent = window.t('fase.' + cl);
  // Una traccia caduta in mezzo a quarantanove riuscite non merita di fermare
  // tutto con una finestra: la scheda e' gia' rossa e resta li' da vedere.
  // L'avviso serve a farsene accorgere adesso, se si sta guardando altro.
  if (esito === 'fail' && errore) {
    window.avvisa(scheda.querySelector('.scheda-titolo').textContent + ' — ' + errore, 'fail');
  }
});

function commuta(i) {
  if (SCELTI.has(i)) SCELTI.delete(i); else SCELTI.add(i);
  aggiornaSelezione();
}

function aggiornaSelezione() {
  SCHEDE.forEach((s, i) => { if (s) s.classList.toggle('spenta', !SCELTI.has(i)); });
  const n = SCELTI.size;
  window.$('#conteggio').textContent = n ? window.t('sel.count', { n }) : '';
  window.$('#scarica').disabled = n === 0;
}

function svuotaRisultati() {
  const e = window.$('#risultati');
  SCELTI.clear(); SCHEDE = [];
  window.$('#scarica').disabled = true;
  e.dataset.pieno = ''; e.innerHTML = '';
  e.appendChild(window.statoVuoto(window.t('audio.results.empty')));
  window.$('#conteggio').textContent = '';
}

/* Un link lasciato cadere sulla finestra: il nucleo ha gia' portato qui, a
 * questa sezione tocca sistemare il modulo e partire. */
window.audioAccettaLink = (testo) => {
  window.$('#modo').value = 'url';
  aggiornaEtichettaIngresso();
  window.$('#ingresso').value = testo;
  analizza();
};

window.initAudio = initAudio;
