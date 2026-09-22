/* Sezione Masterizzazione.
 *
 * La cosa che la distingue dalle altre: qui non si torna indietro. Un CD-R
 * scritto e' consumato comunque, anche se qualcosa va storto a meta'. Per
 * questo la prova a vuoto nasce accesa, la scaletta si vede prima di
 * premere, e la barra di capienza dice a colpo d'occhio se ci sta.
 */

let B_TRACCE = [];

/* Se il computer non ha un masterizzatore, questa sezione non puo' fare
 * niente. Il motivo si tiene da parte invece di gridarlo con un avviso
 * all'avvio: chi ha aperto il programma per tagliare un video non ha nessun
 * bisogno di sapere, prima ancora di aver visto l'interfaccia, che gli manca
 * un'unita' che non intendeva usare. Sta scritto qui dentro, dove si va a
 * cercarlo, e la targhetta nel menu lo dice appena si entra. */
let B_GUASTO = '';

function initBurn(cartella) {
  const $ = window.$;
  $('#b-cartella').value = cartella;
  $('#b-leggi').addEventListener('click', leggiCartella);
  $('#b-avvia').addEventListener('click', masterizza);
  $('#b-sfoglia').addEventListener('click', async () => {
    const e = await window.pywebview.api.scegli_cartella();
    if (e.ok && e.cartella) { $('#b-cartella').value = e.cartella; leggiCartella(); }
  });
  caricaUnita();
  svuotaTracce();

  window.registraSezione('burn', {
    // Dopo un lavoro il bottone torna disponibile solo se la scaletta ci sta.
    riabilita: () => {
      $('#b-avvia').disabled = B_TRACCE.length === 0
        || $('#b-barra-cd').classList.contains('troppo');
    },
    scorciatoia: masterizza,
    traduci: () => {
      if (!B_TRACCE.length) svuotaTracce();
      const sel = $('#b-unita');
      if (sel.options.length) sel.options[0].textContent = window.t('burn.drive.auto');
    },
  });
}

function svuotaTracce() {
  const e = window.$('#b-tracce');
  B_TRACCE = [];
  e.dataset.pieno = ''; e.innerHTML = '';
  e.appendChild(window.statoVuoto(B_GUASTO || window.t('burn.empty')));
  window.$('#b-capienza').textContent = '';
  window.$('#b-criterio').textContent = '';
  window.$('#b-barra-cd').style.width = '0%';
  window.$('#b-avvia').disabled = true;
}

async function caricaUnita() {
  const sel = window.$('#b-unita');
  sel.innerHTML = '';
  const auto = document.createElement('option');
  auto.value = 'auto'; auto.textContent = window.t('burn.drive.auto');
  sel.appendChild(auto);

  const esito = await window.pywebview.api.burn_unita();
  (esito.unita || []).forEach((u) => {
    const o = document.createElement('option');
    o.value = u.indice; o.textContent = u.nome;
    sel.appendChild(o);
  });
  // Se manca il masterizzatore lo si dice subito nel riquadro delle tracce,
  // non dopo aver preparato tutto: e' l'unica cosa che rende inutile il resto
  // della schermata, e vederlo scritto dove ci si aspettano le tracce e' piu'
  // chiaro di un avviso che passa.
  //
  // Qui NON si tocca lo stato della sezione. Ci provava, e sbagliava due
  // volte: uno, un masterizzatore assente non e' un lavoro fallito - e' una
  // condizione, e la spia rossa raccontava un guasto che non c'era stato;
  // due, questa risposta arriva quando arriva, e se arrivava a lavoro gia'
  // avviato ne spegneva la barra a meta'.
  if (esito.errore) {
    B_GUASTO = esito.errore;
    svuotaTracce();
  }
}

async function leggiCartella() {
  const esito = await window.pywebview.api.burn_scansiona(window.$('#b-cartella').value);
  if (!esito.ok) { svuotaTracce(); window.errore(esito.errore, 'burn'); return; }

  B_TRACCE = esito.tracce;
  const elenco = window.$('#b-tracce');
  elenco.innerHTML = ''; elenco.dataset.pieno = '1';
  disegnaTracce();

  window.$('#b-criterio').textContent = window.t('burn.order', { criterio: esito.criterio });
  window.$('#b-capienza').textContent =
    window.t('burn.capacity', { minuti: esito.minuti, limite: esito.limite });
  const quota = Math.min(esito.minuti / esito.limite, 1) * 100;
  const barra = window.$('#b-barra-cd');
  barra.style.width = quota + '%';
  barra.classList.toggle('troppo', !esito.ci_sta);
  window.$('#b-avvia').disabled = !esito.ci_sta;
  if (!esito.ci_sta) window.avvisa(window.t('burn.over'), 'fail');
}

function disegnaTracce() {
  const elenco = window.$('#b-tracce');
  elenco.innerHTML = '';
  B_TRACCE.forEach((tr, i) => {
    const riga = document.createElement('div');
    riga.className = 'scheda traccia';
    riga.draggable = true;
    riga.dataset.i = i;
    riga.innerHTML =
      '<svg class="maniglia" viewBox="0 0 24 24"><use href="#i-maniglia"/></svg>' +
      '<div class="numero-tondo">' + String(i + 1).padStart(2, '0') + '</div>' +
      '<div class="scheda-testo"><div class="scheda-titolo"></div>' +
        '<div class="scheda-sotto"></div></div>' +
      '<div class="voce-durata"></div>';
    riga.querySelector('.scheda-titolo').textContent = tr.nome;
    riga.querySelector('.scheda-sotto').textContent = tr.peso + ' MB';
    riga.querySelector('.voce-durata').textContent = tr.durata;

    // Trascinare per riordinare: l'ordine dei nomi non e' sempre quello con
    // cui si vuole ascoltare, e su un CD non si puo' correggere dopo.
    riga.addEventListener('dragstart', (e) => {
      e.dataTransfer.setData('text/plain', String(i));
      riga.classList.add('in-volo');
    });
    riga.addEventListener('dragend', () => riga.classList.remove('in-volo'));
    riga.addEventListener('dragover', (e) => { e.preventDefault(); riga.classList.add('bersaglio'); });
    riga.addEventListener('dragleave', () => riga.classList.remove('bersaglio'));
    riga.addEventListener('drop', (e) => {
      e.preventDefault(); e.stopPropagation();
      riga.classList.remove('bersaglio');
      const da = parseInt(e.dataTransfer.getData('text/plain'), 10);
      if (Number.isNaN(da) || da === i) return;
      const [presa] = B_TRACCE.splice(da, 1);
      B_TRACCE.splice(i, 0, presa);
      disegnaTracce();
    });
    elenco.appendChild(riga);
  });
}

async function masterizza() {
  const esito = await window.pywebview.api.burn_masterizza({
    cartella: window.$('#b-cartella').value,
    ordine:   B_TRACCE.map((t) => t.nome),
    velocita: window.$('#b-velocita').value,
    unita:    window.$('#b-unita').value,
    prova:    window.$('#b-prova').checked,
    no_eject: window.$('#b-noeject').checked,
    livella:  window.$('#b-livella').checked,
    rifila:   window.$('#b-rifila').checked,
  });
  if (!esito.ok) window.errore(esito.errore, 'burn');
}

window.initBurn = initBurn;
