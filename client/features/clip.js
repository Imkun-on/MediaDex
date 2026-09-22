/* Sezione Montaggio.
 *
 * Sei operazioni con parametri diversi. Invece di mostrarli tutti e
 * disabilitare quelli che non servono - che riempie la schermata di campi
 * spenti - il modulo si ricostruisce a ogni cambio di operazione: si vede
 * solo cio' che riguarda quello che si sta facendo.
 */

const C_AZIONI = ['taglia', 'unisci', 'gif', 'webp', 'provino', 'compat'];
let C_FILE = [];

/* Quali campi servono a ciascuna operazione. Tenerlo come dato invece che
 * come una catena di if rende evidente, leggendo, cosa chiede ognuna. */
const C_CAMPI = {
  taglia:  { param: ['da', 'a'], flag: ['preciso'], multi: false },
  unisci:  { param: [],          flag: ['capitoli'], multi: true },
  gif:     { param: ['da', 'durata', 'fps', 'larghezza'], flag: [], multi: false },
  webp:    { param: ['da', 'durata', 'fps', 'larghezza'], flag: [], multi: false },
  provino: { param: ['griglia'], flag: [], multi: false },
  compat:  { param: [],          flag: [], multi: false },
};

function initClip() {
  const $ = window.$;
  const sel = $('#c-azione');
  sel.innerHTML = '';
  C_AZIONI.forEach((a) => {
    const o = document.createElement('option');
    o.value = a; o.textContent = window.t('clip.op.' + a);
    sel.appendChild(o);
  });
  sel.addEventListener('change', disegnaModulo);
  $('#c-avvia').addEventListener('click', esegui);
  $('#c-sfoglia').addEventListener('click', async () => {
    const multi = C_CAMPI[sel.value].multi;
    const e = await window.pywebview.api.scegli_file(multi);
    if (!e.ok || !e.file.length) return;
    C_FILE = e.file;
    $('#c-file').value = C_FILE.join(' | ');
  });
  $('#c-file').addEventListener('input', () => {
    C_FILE = $('#c-file').value.split('|').map((s) => s.trim()).filter(Boolean);
  });
  disegnaModulo();
  svuotaRisultatoClip();

  window.registraSezione('clip', {
    scorciatoia: esegui,
    traduci: () => {
      const scelta = sel.value;
      Array.from(sel.options).forEach((o) => { o.textContent = window.t('clip.op.' + o.value); });
      sel.value = scelta;
      disegnaModulo();
      if (!$('#c-risultato').querySelector('img')) svuotaRisultatoClip();
    },
  });
}

function disegnaModulo() {
  const azione = window.$('#c-azione').value;
  const conf = C_CAMPI[azione];
  window.$('#c-etichetta-file').textContent =
    window.t(conf.multi ? 'clip.files' : 'clip.file');

  const ETICHETTE = {
    da: 'clip.from', a: 'clip.to', durata: 'clip.duration',
    fps: 'audio.workers', larghezza: 'audio.format', griglia: 'clip.grid',
  };
  const SEGNAPOSTO = {
    da: '1:20', a: '3:45', durata: '5', fps: '15', larghezza: '480', griglia: '4x4',
  };

  const riga = window.$('#c-parametri');
  riga.innerHTML = '';
  conf.param.forEach((campo) => {
    const g = document.createElement('div');
    g.className = 'gruppo mini';
    const l = document.createElement('label');
    l.textContent = campo === 'fps' ? 'FPS'
                  : campo === 'larghezza' ? 'PX'
                  : window.t(ETICHETTE[campo]);
    const i = document.createElement('input');
    i.className = 'campo'; i.id = 'c-' + campo; i.type = 'text';
    i.placeholder = SEGNAPOSTO[campo] || '';
    g.appendChild(l); g.appendChild(i);
    riga.appendChild(g);
  });

  const flag = window.$('#c-interruttori');
  flag.innerHTML = '';
  conf.flag.forEach((nome) => {
    const l = document.createElement('label');
    l.className = 'interruttore';
    l.innerHTML = '<input type="checkbox" id="c-' + nome + '"' +
                  (nome === 'capitoli' ? ' checked' : '') + '>' +
                  '<span class="cursore"></span><span></span>';
    l.querySelector('span:last-child').textContent = window.t('clip.' + nome);
    flag.appendChild(l);
  });
}

function svuotaRisultatoClip() {
  const e = window.$('#c-risultato');
  e.innerHTML = '';
  e.appendChild(window.statoVuoto(window.t('clip.result.empty')));
}

async function esegui() {
  const azione = window.$('#c-azione').value;
  const conf = C_CAMPI[azione];
  const opzioni = { azione, file: C_FILE };

  conf.param.forEach((campo) => {
    const el = window.$('#c-' + campo);
    if (!el || !el.value.trim()) return;
    if (campo === 'griglia') {
      const m = el.value.trim().match(/^(\d+)\s*[x×]\s*(\d+)$/);
      if (m) { opzioni.colonne = +m[1]; opzioni.righe = +m[2]; }
    } else {
      opzioni[campo] = el.value.trim();
    }
  });
  conf.flag.forEach((nome) => {
    const el = window.$('#c-' + nome);
    if (el) opzioni[nome] = el.checked;
  });

  const esito = await window.pywebview.api.clip_esegui(opzioni);
  if (!esito.ok) window.errore(esito.errore, 'clip');
}

window.ascolta('clipFinito', (s, dati) => {
  window.avvisa(dati.testo, dati.ok ? 'ok' : 'fail');
  const box = window.$('#c-risultato');
  if (!dati.anteprima) {
    // Un video prodotto non si puo' mostrare qui in modo utile: si dice dov'e'.
    box.innerHTML = '';
    box.appendChild(window.statoVuoto(dati.file));
    return;
  }
  box.innerHTML = '';
  const img = new Image();
  img.alt = ''; img.className = 'immagine-piena';
  // Prima il ripiego, poi l'indirizzo: dare src fa partire il caricamento
  // all'istante, e un errore immediato scivolerebbe via prima che ci sia
  // qualcuno ad ascoltarlo.
  img.onerror = () => svuotaRisultatoClip();
  img.src = dati.anteprima + '?v=' + Date.now();
  box.appendChild(img);
});

window.initClip = initClip;
