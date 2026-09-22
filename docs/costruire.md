# Costruire l'installatore

Da sorgenti a `MediaDex-Setup.exe`, e da lì a una Release su GitHub.

> Torna al [README](../README.md).

---

## In un comando

```powershell
.\costruisci.ps1 -Versione 2.0
```

Alla fine stampa dove è finito, quanto pesa e la sua impronta SHA256:

```
    C:\...\MediaDex\installer\output\MediaDex-Setup.exe
    58,3 MB
    SHA256  9F2C...
```

### Le altre due forme

```powershell
.\costruisci.ps1 -SoloInstallatore     # riusa dist\, salta PyInstaller
.\costruisci.ps1 -Forza                # nessuna domanda: serve alla CI
```

`-SoloInstallatore` è quello che si usa lavorando sull'installatore: la parte
lunga è PyInstaller, e se non hai toccato il codice Python non c'è ragione di
rifarla.

---

## Cosa serve, una volta sola

```powershell
winget install JRSoftware.InnoSetup
winget install Gyan.FFmpeg
```

Inno Setup è **obbligatorio**: senza, lo script si ferma al passo 0 con
l'indirizzo per scaricarlo. FFmpeg no — il pacchetto si costruisce lo stesso —
ma senza non puoi provare il risultato.

PyInstaller invece non devi installarlo: se manca, `costruisci.ps1` lo mette da
sé.

---

## I due passaggi, e perché sono due

**PyInstaller** trasforma il programma in una cartella che si esegue senza
avere Python. **Inno Setup** prende quella cartella e ne fa un installatore: un
`.exe` solo, che mette le cose al loro posto, crea le scorciatoie, si registra
in «Installazione applicazioni» e sa disinstallarsi.

Sono strumenti diversi perché risolvono problemi diversi, e nessuno dei due sa
fare il lavoro dell'altro.

### A cartella, non a file unico

Fino alla versione precedente MediaDex era un `.exe` solo da 64 MB. Sembrava
più elegante ed era peggio: il file unico **si riestrae in una cartella
temporanea a ogni avvio**, cioè sessanta megabyte da scompattare ogni volta che
si apre il programma, otto secondi buoni prima che parta una riga di Python.

A cartella non si scompatta niente. E l'aggiornamento diventa pulito: Inno
spazza `{app}\_internal` prima di ricopiare, perché senza, le librerie di due
versioni diverse si accumulerebbero nella stessa cartella e Python ne
caricherebbe un misto — guasti che non somigliano a niente e che spariscono
disinstallando e reinstallando.

### Quanto ci mette ad aprirsi

Misurato su questa macchina, appena costruito:

| | Quando compare la finestra |
|---|---|
| Eseguibile, **prima** apertura | 6,0 s |
| Eseguibile, dalla seconda | **~3 s** |

Da lì in poi la finestra c'è, massimizzata, con la schermata di caricamento
sopra: l'interfaccia finisce di montarsi qualche secondo più tardi, e nel
frattempo la barra racconta a che punto è.

Le prime aperture dopo un'installazione sono più lente di così, anche molto:
è **Windows Defender** che scansiona per la prima volta ottanta megabyte di
file nuovi e non firmati. Non è un difetto da correggere — è quello che
Defender deve fare, e lo fa una volta sola — ma è la prima cosa che chi
installa vede, ed è anche la prima che scambierebbe per un programma rotto.

Prima di questa versione erano 23–30 secondi alla prima apertura e 9,7 alle
successive, e per tutto quel tempo non c'era una finestra: c'era un rettangolo
di quattrocento pixel disegnato da PyInstaller. Il tempo totale non è cambiato
di molto; quello che è cambiato è che adesso qualcosa di grande compare dopo
tre secondi invece che dopo dieci.

### Cosa entra e cosa no

Entra tutto il programma: gli strati di `server/`, la pagina di `client/`, e
l'interprete Python. Chi riceve l'installatore fa doppio clic e basta: non
installa Python, non vede un file `.py`, non sa nemmeno che c'è dentro.

**Non entra FFmpeg.** Adesso sarebbe possibile — a cartella non c'è più il
costo di riestrarlo a ogni avvio — ma sono 400 MB che triplicherebbero il peso
dell'installatore per una cosa che si installa una volta sola con un comando.
Il programma se ne accorge da solo se manca e dice esattamente cosa digitare.

> Se un domani lo si volesse dentro, il punto in cui aggiungerlo è `binaries`
> in `MediaDex.spec`, risolvendolo con `shutil.which` al momento della
> costruzione.

---

## Il passo che non si può saltare

Il passo 2 di `costruisci.ps1` cancella da `dist\` questi quattro nomi:

```
risultati    logs    Database_Globale
```

Non è pulizia formale. **MediaDex scrive accanto a sé stesso**, e chi
costruisce di solito ha appena provato l'eseguibile proprio da `dist\`: lì
dentro sono rimasti i suoi brani scaricati, i suoi log, il suo database.
Inno li spedirebbe dentro l'installatore senza chiedere niente a nessuno.

Lo script chiede conferma prima di cancellarli, e se rispondi di no si ferma:
con quei file dentro, l'installatore spedirebbe i tuoi dati.

La stessa lista compare in altri due posti — `Excludes` nella sezione
`[Files]` di `installer/MediaDex.iss` e `.gitignore` — ed è voluto. Una rete
sola su «non pubblicare i propri dati» è poca.

---

## Dove installa, e perché lì

In `%LOCALAPPDATA%\Programs\MediaDex`, senza chiedere permessi di
amministratore.

Non è una scorciatoia per evitare la finestra dell'UAC: è l'unica collocazione
in cui MediaDex funziona. Il programma scrive accanto a sé stesso —
`risultati\`, `logs\`, `Database_Globale\` — e dentro
«Programmi» un utente normale non ha permesso di scrivere. Installato lì, il
primo download fallirebbe con un errore di permessi che nessuno saprebbe
interpretare.

## WebView2

L'interfaccia è una pagina web, e a disegnarla è WebView2. C'è già da Windows
10 in poi, ma non su tutte le macchine: l'installatore controlla tre chiavi di
registro e, se manca, lo scarica da Microsoft prima di copiare i file.

Se il download fallisce — niente rete, un proxy aziendale — l'installazione
**prosegue lo stesso** e avvisa. Fermare tutto per un componente che magari
l'utente ha già sarebbe sproporzionato.

---

## Pubblicare una versione

```bash
git tag v2.0
git push --tags
```

Il resto lo fa `.github/workflows/pacchetti.yml`: prende una macchina Windows,
si procura FFmpeg e Inno Setup, installa le dipendenze e lancia **lo stesso
`costruisci.ps1`** che lanci tu. Poi crea la Release, ci allega
`MediaDex-Setup.exe` e scrive nelle note il peso, l'impronta SHA256 e le
istruzioni per SmartScreen.

Che sia lo stesso script e non una copia dei suoi comandi non è un dettaglio: è
il motivo per cui la CI non può divergere da quello che succede sulla tua
macchina.

Per provare senza pubblicare niente c'è «Run workflow» da GitHub: costruisce e
lascia il risultato come artefatto, per trenta giorni.

### Il nome del file non ha la versione

Di proposito. Così questo indirizzo resta valido per sempre e si può mettere
nel README senza doverlo aggiornare a ogni pubblicazione:

```
https://github.com/Imkun-on/MediaDex/releases/latest/download/MediaDex-Setup.exe
```

---

## Il GUID dell'installatore

```
{6779E9EE-5B17-4F90-ACC5-F1949A9874D5}
```

È `AppId` in `installer/MediaDex.iss`, e identifica MediaDex per sempre: è
quello che permette a una versione nuova di riconoscere e sostituire la
vecchia invece di installarsi accanto.

**Non va mai cambiato**, e non va mai copiato da un altro programma: due
installatori con lo stesso `AppId` si disinstallano a vicenda.

---

## La schermata di caricamento

È dentro la pagina, non fuori. La finestra nasce **massimizzata** e visibile
subito, e il velo la copre tutta finché l'interfaccia non è pronta: marchio,
nome, e una barra che scorre.

Ce n'erano due, ed erano una di troppo. PyInstaller sa mostrare un'immagine
mentre il programma parte, e per un po' MediaDex l'ha usata: compariva subito,
ma era un rettangolo di quattrocento pixel al centro dello schermo, e appena la
finestra si apriva bisognava far sparire l'una e comparire l'altra al momento
esatto, o si vedeva un buco. Due schermate di caricamento per un caricamento
solo, con in mezzo un incastro da azzeccare.

Adesso ce n'è una. Il prezzo è dichiarato: fra il doppio clic e la comparsa
della finestra passano i secondi che servono a importare Rich e il ponte con
WebView2, e in quei secondi sullo schermo non c'è niente. Non si può fare di
meglio senza rimetterne due, perché la finestra non può esistere prima di aver
importato la libreria che la crea.

Il guadagno, oltre alla semplicità: **tkinter esce dal pacchetto**. La
schermata di PyInstaller è disegnata da Tcl/Tk, ed era l'unica ragione per cui
una decina di megabyte di libreria grafica viaggiavano dentro un programma che
non ne esegue una riga.

### Come si muove la barra

Non scatta di passo in passo e non scorre avanti e indietro a vuoto. Tre numeri
in `client/app.js`:

| | |
|---|---|
| `quotaVera` | quanto è stato caricato davvero — non torna mai indietro |
| `quotaTetto` | un quarto più avanti della vera: dove la barra può arrivare mentre aspetta |
| `quotaMostrata` | quello che si vede, che a ogni fotogramma si avvicina al tetto |

Serve perché i sette passi non sono distribuiti nel tempo: i primi tre arrivano
in mezzo secondo, poi c'è un buco di diversi secondi mentre Python risponde. Una
barra che salta e poi resta immobile per sei secondi si legge come «piantata».
Col tetto poco più avanti continua a muoversi piano per tutto il buco, e quando
il passo arriva riparte da dove era, senza scatti.

E ogni punto in cui arriva corrisponde a qualcosa di davvero caricato: non è
un'animazione che gira a vuoto per tenere compagnia.

Per questo `.avvio-barra span` in `styles/style.css` **non ha nessuna
transizione**: la larghezza la scrive il codice a ogni fotogramma, e una
transizione sopra sarebbero due animazioni che si inseguono.
