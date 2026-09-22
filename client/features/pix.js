/* Sezione Rimasterizza.
 *
 * La parte che conta e' la tabella delle risoluzioni: non e' un elenco fisso,
 * ma il risultato calcolato su *quel* file. La stessa riga che offre il 4K
 * dice, quando e' il caso, che da quella sorgente non aggiunge un solo
 * dettaglio vero. E' il punto in cui il programma e' piu' onesto, e sarebbe
 * un peccato nasconderlo dietro un menu a tendina.
 */

let P_DIAGNOSI = null;
let P_ALTEZZA = 'auto';

function initPix() {
  const $ = window.$;
  $('#p-analizza').addEventListener('click', analizzaVideo);
  $('#p-avvia').addEventListener('click', rimasterizza);
  $('#p-sfoglia').addEventListener('click', async () => {
    const e = await window.pywebview.api.scegli_file(false);
    if (e.ok && e.file.length) { $('#p-file').value = e.file[0]; analizzaVideo(); }
  });
  svuotaDiagnosi();
  svuotaAnteprima();

  window.registraSezione('pix', {
    riabilita: () => { $('#p-avvia').disabled = !P_DIAGNOSI; },
    scorciatoia: rimasterizza,
    traduci: () => { if (!P_DIAGNOSI) { svuotaDiagnosi(); svuotaAnteprima(); } },
  });
}

function svuotaDiagnosi() {
  const e = window.$('#p-diagnosi');
  P_DIAGNOSI = null;
  e.innerHTML = '';
  e.appendChild(window.statoVuoto(window.t('pix.empty')));
  window.$('#p-risoluzioni').innerHTML = '';
  window.$('#p-preset').innerHTML = '';
  window.$('#p-avvia').disabled = true;
}

function svuotaAnteprima() {
  const e = window.$('#p-anteprima');
  e.innerHTML = '';
  e.appendChild(window.statoVuoto(window.t('pix.preview.empty')));
}

async function analizzaVideo() {
  const esito = await window.pywebview.api.pix_analizza(window.$('#p-file').value);
  if (!esito.ok) { svuotaDiagnosi(); window.errore(esito.errore, 'pix'); return; }
  P_DIAGNOSI = esito;

  // Diagnosi: la scheda del file, poi i difetti trovati.
  const box = window.$('#p-diagnosi');
  box.innerHTML = '';
  const scheda = document.createElement('div');
  scheda.className = 'riga-diagnosi capo';
  scheda.textContent = esito.nome + '  ·  ' + esito.scheda;
  box.appendChild(scheda);
  esito.problemi.forEach((p) => {
    const r = document.createElement('div');
    r.className = 'riga-diagnosi';
    r.textContent = p.replace(/\[\/?[a-z_]+\]/g, '');
    box.appendChild(r);
  });

  // Trattamenti: quello consigliato e' marcato, ma si puo' cambiare.
  const sel = window.$('#p-preset');
  sel.innerHTML = '';
  esito.presets.forEach((p) => {
    const o = document.createElement('option');
    o.value = p.chiave;
    o.textContent = p.nome + (p.chiave === esito.preset
      ? '  (' + window.t('pix.suggested') + ')' : '');
    o.title = p.desc;
    sel.appendChild(o);
  });
  sel.value = esito.preset;

  disegnaRisoluzioni(esito.risoluzioni);
  window.$('#p-avvia').disabled = false;
}

function disegnaRisoluzioni(voci) {
  const box = window.$('#p-risoluzioni');
  box.innerHTML = '';
  P_ALTEZZA = 'auto';
  voci.forEach((v, i) => {
    const b = document.createElement('button');
    b.className = 'scelta livello-' + v.livello + (v.consigliata && i === 0 ? ' scelta-attiva' : '');
    b.type = 'button';
    b.innerHTML =
      '<div class="scelta-nome"></div>' +
      '<div class="scelta-fattore"></div>' +
      '<div class="scelta-nota"></div>';
    b.querySelector('.scelta-nome').textContent = v.etichetta.replace(/\s+/g, ' ');
    b.querySelector('.scelta-fattore').textContent = v.fattore.toFixed(2) + '×';
    b.querySelector('.scelta-nota').textContent = v.nota;
    b.addEventListener('click', () => {
      Array.from(box.children).forEach((c) => c.classList.remove('scelta-attiva'));
      b.classList.add('scelta-attiva');
      // La prima voce e' l'automatica: si manda 'auto' perche' sia il motore
      // a ricalcolarla, invece di congelarne qui il valore.
      P_ALTEZZA = i === 0 ? 'auto' : v.altezza;
    });
    box.appendChild(b);
  });
}

async function rimasterizza() {
  const esito = await window.pywebview.api.pix_rimasterizza({
    file:      window.$('#p-file').value,
    preset:    window.$('#p-preset').value,
    altezza:   P_ALTEZZA,
    gpu:       window.$('#p-gpu').checked,
    confronto: window.$('#p-confronto').checked,
  });
  if (!esito.ok) window.errore(esito.errore, 'pix');
}

window.ascolta('pixFinito', (s, dati) => {
  window.avvisa(dati.testo, 'ok');
  const box = window.$('#p-anteprima');
  if (!dati.confronto) { svuotaAnteprima(); return; }
  box.innerHTML = '';
  const img = new Image();
  img.alt = '';
  img.className = 'immagine-piena';
  // Il ripiego si aggancia prima di dare l'indirizzo: assegnare src fa partire
  // il caricamento subito, e un file gia' in cache o gia' sparito puo' fallire
  // prima che la riga dopo abbia messo il gestore, lasciando un riquadro rotto.
  img.onerror = () => svuotaAnteprima();
  // Un parametro finto in coda costringe il WebView a rileggere il file: senza,
  // dopo la seconda rimasterizzazione mostrerebbe ancora la prima immagine.
  img.src = dati.confronto + '?v=' + Date.now();
  box.appendChild(img);
});

window.initPix = initPix;
