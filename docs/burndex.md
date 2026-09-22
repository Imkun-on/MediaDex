# BurnDex — masterizzare un CD audio

Un CD audio non e' una cartella di file, ed e' l'unica cosa che MediaDex fa
che non si puo' rifare: un CD-R scritto male e' consumato comunque. Questa
pagina spiega cosa succede prima che il disco cominci a girare.

> Torna al [README](../README.md).

---

## 💿 BurnDex: masterizzare un CD audio

**BurnDex** è lo strumento gemello di AudioDex: legge direttamente le raccolte scaricate da AudioDex, trasformandole in un **CD audio** vero.

### A cosa serve e perché un CD audio

Un file `.m4a` non si può "mettere su un CD" e sperare che l'autoradio lo suoni. Ci sono due modi diversi di scrivere un disco, e uno solo funziona ovunque:

| | Cosa contiene | Dove si sente |
|---|---|---|
| **CD audio** (CD-DA) | Tracce PCM grezze, nessun file, nessun metadato | 🚗 Qualsiasi lettore CD, autoradio, impianti anni '90 |
| **CD dati** | I file `.m4a`/`.mp3` copiati così com'è | Solo lettori recenti che sanno decodificare quei codec |

BurnDex produce **CD audio**, cioè lo standard **Red Book (CD-DA)**: PCM 44.1 kHz, 16 bit, stereo, massimo ~80 minuti. È l'unico formato che nel 2026 legge ancora praticamente qualunque apparecchio.

> ⚠️ **Il CD audio non ha metadati.** Titoli e artisti non esistono nel formato CD-DA: quello che a volte vedi sul display dell'autoradio arriva da un database online. È il prezzo della compatibilità universale.

### Requisiti aggiuntivi

| Requisito | Note |
|---|---|
| **Windows** | La masterizzazione usa **IMAPI2**, l'API COM nativa di Windows. AudioDex resta multipiattaforma; solo BurnDex è vincolato |
| **pywin32** | Già in `requirements.txt`. Serve solo a BurnDex: senza, `--dry-run` funziona lo stesso e la masterizzazione si ferma con un messaggio chiaro |
| **FFmpeg** | Lo stesso di AudioDex, per decodificare l'audio in PCM |
| **Un masterizzatore** | Interno o USB esterno: BurnDex distingue i due casi, vedi [Riconoscimento del sistema](#riconoscimento-del-sistema) |

Nessun programma di masterizzazione esterno: niente Nero, ImgBurn o CDBurnerXP.

### Il flusso in quattro passi

Lanciando `python -m cli burn` senza argomenti parte una procedura guidata a **quattro passi numerati**, ognuno annullabile:

```
 Passo 1/4   RACCOLTA   ────────────────────────────────────────────

┌────┬────────────────────────────────────────┬────────┬───────────┐
│  # │ Raccolta                               │ Tracce │    Durata │
├────┼────────────────────────────────────────┼────────┼───────────┤
│  1 │ Molchat Doma - Etazhi                  │      9 │  33.6 min │
└────┴────────────────────────────────────────┴────────┴───────────┘

💿 Quale raccolta? (numero, invio per uscire) > 1
```

**1. Raccolta.** Elenca le cartelle di `risultati/musica/` con numero di tracce e **durata complessiva**, in giallo se sfora il limite del disco: scegli sapendo già cosa ci sta.

```
 Passo 2/4   SCALETTA   ────────────────────────────────────────────

                       Molchat Doma - Etazhi
┌────┬─────────────────────────────────────────────────┬───────────┐
│  # │ Traccia                                         │    Durata │
├────┼─────────────────────────────────────────────────┼───────────┤
│  1 │ 01 - На Дне.m4a                                 │      4:07 │
│  2 │ 02 - Танцевать.m4a                              │      3:22 │
│  …                                                                │
├────┼─────────────────────────────────────────────────┼───────────┤
│    │ 9 tracce                                        │  33.6 min │
└────┴─────────────────────────────────────────────────┴───────────┘
██████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░  33.6 / 80 min
Ordine: numero di traccia nel nome  ·  stacchi da 2 s inclusi nel totale
```

**2. Scaletta.** La sequenza esatta che finirà sul disco, con riga di totale e **barra di capienza** (verde fino all'85%, gialla oltre, rossa oltre i 79 minuti). Sotto è sempre dichiarato **con quale criterio** è stato deciso l'ordine. Puoi selezionare un sottoinsieme con la stessa sintassi di AudioDex (`3`, `1-5`, `1,3,7`, invio per tutte) e la scaletta viene **ristampata** con la nuova numerazione.

**3. Disco e velocità.** Scheda dell'unità e del disco inserito, poi la scelta della velocità di scrittura costruita sui **valori reali** che il masterizzatore dichiara:

```
┌─────┬────────────┬───────────────────────────────────────────────┐
│   # │ Velocita'  │ Resa                                          │
├─────┼────────────┼───────────────────────────────────────────────┤
│   1 │ 8x ★       │ consigliata — incisione piu' netta, la piu'    │
│     │            │ sicura per autoradio e stereo datati          │
│   2 │ 24x        │ la piu' rapida, ma qualche lettore vecchio     │
│     │            │ puo' faticare                                 │
└─────┴────────────┴───────────────────────────────────────────────┘
```

> 💡 **La velocità non cambia la qualità audio.** A 8x e a 24x sul disco finiscono gli stessi identici bit. Cambia la **precisione fisica** dell'incisione: andando piano i bordi delle depressioni sono più netti e i lettori usurati sbagliano meno. Il risultato non è "suono peggiore", è tutto-o-niente, il disco si legge o inciampa.

**4. Masterizzazione.** Decodifica di tutte le tracce, scheda di conferma finale, scrittura.

```
╔═══════════════════ 💿  Pronto a masterizzare ════════════════════╗
║   Unita'            MATSHITA DVD+-RW UJ8E2                       ║
║   Disco             CD-R vuoto                                   ║
║   Velocita'         8x                                           ║
║   Tracce            9                                            ║
║   Durata            33.6 min  (46.4 min liberi dopo)             ║
║       ███████████████░░░░░░░░░░░░░░░░░░░░░  33.6 / 80 min        ║
╚═════════════ la scrittura su CD-R e' irreversibile ══════════════╝
```

> 🛡️ **La decodifica avviene tutta prima di `PrepareMedia()`**, non al volo durante la scrittura. Una volta che il laser incide, un FFmpeg lento o un file corrotto brucerebbero il disco a metà: così l'unico errore possibile in scrittura è un guasto hardware.

### Opzioni della riga di comando (BurnDex)

| Opzione | Descrizione |
|---|---|
| `--dir`, `-d` | Cartella da masterizzare. Se omessa, la scegli dall'elenco |
| `--base`, `-b` | Cartella delle raccolte (default: `risultati/musica`) |
| `--speed`, `-s` | Velocità in "x". Se omessa viene chiesta; con `--yes` usa 8x |
| `--drive` | Indice del masterizzatore da usare (vedi `--info`) |
| `--dry-run`, `-n` | 🧪 **Prova a vuoto**: mostra la scaletta, verifica disco e capienza, **non tocca il disco** |
| `--info`, `-i` | Sistema, masterizzatori e disco inserito, poi esce |
| `--yes`, `-y` | Nessuna domanda: tutte le tracce, velocità predefinita, nessuna conferma |
| `--no-eject` | Non espellere il disco a fine masterizzazione |
| `--no-level` | Non livellare il volume fra le tracce: lascia ogni brano al volume con cui è stato caricato |
| `--trim` | Rifila i silenzi a inizio e fine traccia |

Esempi (sono **alternative**, da eseguire una alla volta). Prima i due innocui:

```bash
python -m cli burn --info                                        # ricognizione
python -m cli burn -d "risultati/musica/Molchat Doma - Etazhi" -n  # prova a vuoto
```

Poi quelli che **scrivono davvero sul disco** (non incollarli insieme ai precedenti):

```bash
python -m cli burn -d "risultati/musica/Molchat Doma - Etazhi"     # masterizza
python -m cli burn -d "..." --speed 24 --yes --no-eject          # automatico
```

> 🧪 **Usa `--dry-run` la prima volta.** Esegue tutti i controlli (scaletta, ordine, tipo di disco, capienza, velocità disponibili) senza scrivere nulla. Un CD-R sbagliato è irrecuperabile, una prova a vuoto costa due secondi.

### Cosa succede all'audio prima di incidere

Un CD audio è 44.1 kHz, 16 bit, stereo, e basta: qualunque cosa tu scarichi (un opus a 48 kHz, un m4a a 44.1, un vecchio caricamento mono) va portata lì. **Il come non è indifferente.**

Scendere a 16 bit **troncando** i valori genera una distorsione *correlata al segnale*: sui passaggi deboli, code di riverbero e dissolvenze, l'orecchio la riconosce come suono sporco. Il **dither** la sostituisce con rumore casuale, che invece si ignora. Misurato su un tono a −70 dBFS, l'energia sulle armoniche passa da **+46,9 dB a +31,1 dB** rispetto alla fondamentale: quasi 16 dB di sporcizia in meno. Da oggi il dither c'è sempre, non si disattiva.

> 🔬 **Il ricampionatore invece è rimasto quello predefinito.** `soxr` è considerato migliore e la build Gyan ce l'ha, ma non sono riuscito a misurare un vantaggio reale nel passaggio 48 → 44.1, e chiederlo su una build compilata senza `libsoxr` farebbe fallire la masterizzazione a metà. Non vale il rischio per un guadagno che non so dimostrare.

**`--level`, livella il volume fra le tracce.** Una playlist YouTube ha salti di 9-10 LU fra un brano e l'altro: la mano che corre alla manopola a ogni cambio. L'opzione misura ogni traccia secondo lo standard EBU R128 e la porta a −16 LUFS, senza mai superare −1 dBTP di picco reale, spingere oltre toserebbe la forma d'onda, e su un CD-R non si torna indietro.

Misurato su tre brani a −7, −14 e −21 dB:

| | Scarto fra la più forte e la più debole |
|---|---|
| Senza `--level` | **14,0 dB** |
| Con `--level` | **0,59 dB** |

La misura si fa con `ebur128` e non con la prima passata di `loudnorm`: danno gli stessi identici numeri, verificato su uno stesso file, −35,8 LUFS e −31,6 dBFS contro −35,78 e −31,56, ma il primo impiega **2,3 secondi contro 11,6**. Su un CD da venti tracce sono ottanta secondi invece di sette minuti, ed è il motivo per cui il livellamento è diventato il **comportamento normale**: si spegne con `--no-level`.

**`--trim`, rifila i silenzi.** I caricamenti YouTube hanno spesso uno o due secondi di nulla in testa e in coda, che si **sommano** ai 2 secondi di stacco che IMAPI2 inserisce comunque fra una traccia e l'altra: il risultato sono pause di quattro o cinque secondi in mezzo a un album. Sulla raccolta di prova ha tolto 3,4 secondi per traccia.

La coda si toglie girando il flusso, tagliando l'inizio e rigirandolo: `silenceremove` sa lavorare solo in testa.

### L'ordine delle tracce sul disco

Su un CD-R la scaletta si decide **una volta sola**: non esiste modo di riordinare, aggiungere o togliere brani dopo. BurnDex usa tre criteri, in ordine di precedenza:

1. **`ordine.txt`** nella cartella: un nome file per riga, righe vuote e `#` ignorate. Comando manuale assoluto
2. **Prefisso numerico nel nome** (`01 - Brano.m4a`), è esattamente come AudioDex salva le playlist, quindi di norma scatta questo e l'ordine dell'album è già quello giusto. Vale **solo se ce l'hanno tutti i file**: con anche un solo file senza numero l'ordinamento diventerebbe arbitrario proprio dove conta
3. **Data di creazione**, ripiego per cartelle messe insieme a mano. Attenzione: se hai **copiato** i file, la data di creazione è quella della copia

Il criterio effettivamente usato è **sempre stampato** sotto la scaletta, prima della conferma.

```txt
# ordine.txt — un nome file per riga, l'ordine è quello che leggi
03 - Фильмы.m4a
01 - На Дне.m4a
09 - Клетка.m4a
```

### Tipologie di disco riconosciute

BurnDex classifica il disco inserito e spiega **cosa fare** in ciascun caso, invece di limitarsi a "vuoto sì/no":

| Disco | Esito | Motivo e rimedio |
|---|---|---|
| 💿 **CD-R vuoto** | ✅ masterizza | Il caso ideale per l'auto |
| 💿 **CD-RW vuoto** | ✅ masterizza, con avviso | Riflette meno luce: molte autoradio e stereo datati non lo leggono |
| 🔒 **CD-R già scritto** | ❌ | La scrittura è definitiva: serve un disco nuovo |
| ♻️ **CD-RW già scritto** | ❌ | Ma è cancellabile: Esplora risorse → tasto destro sull'unità → *Cancella questo disco* |
| 📀 **CD-ROM** | ❌ | Stampato in fabbrica, sola lettura |
| 📀 **DVD±R / DVD±RW / DVD-RAM / BD-R / BD-RE** | ❌ | **Il Red Book non esiste su DVD e Blu-ray.** Per quanto capienti, non c'è un formato audio che un lettore da auto sappia interpretare |
| ❓ **Non riconosciuto** | ❌ | Disco graffiato, inserito male, o tipo non gestito dall'unità |

> 🐛 Il caso **DVD** era il buco più insidioso: un DVD vergine risulta "vuoto e scrivibile", quindi la versione precedente sarebbe partita per poi schiantarsi su un errore IMAPI incomprensibile a metà procedura.

### Riconoscimento del sistema

`--info` apre con una ricognizione della macchina, letta da **WMI**:

```
┌───────────────────────── Il tuo sistema ─────────────────────────┐
│  Computer        PC portatile  Aspire A315-23                    │
│  Unita' D:       MATSHITA DVD+-RW UJ8E2 USB Device               │
│                  collegata in USB (esterna)                      │
└──────────────────────────────────────────────────────────────────┘
L'unita' e' esterna e si alimenta dalla porta USB.
In scrittura il laser assorbe molto piu' che in lettura, e una porta al limite
fa riavviare l'unita' a meta' masterizzazione. Se una scrittura fallisce:
  1. collega entrambi gli spinotti, se il cavo ne ha due
  2. usa una porta diretta sul PC, mai un hub non alimentato
```

Cosa rileva e come:

- 💻 **Portatile o fisso**: da `Win32_SystemEnclosure.ChassisTypes` (8-12, 14, 18, 21, 30-32 = trasportabile; 3-7, 13, 15-17, 23, 24 = fisso) e dal modello in `Win32_ComputerSystem`
- 🔌 **Unità interna o esterna**, dal ramo dell'albero PnP in `Win32_CDROMDrive.PNPDeviceID`: le USB stanno sotto `USBSTOR\`, le interne sotto `SCSI\` o `IDE\`
- 🚫 **Nessun lettore**, su un portatile recente è la norma: BurnDex lo dice esplicitamente e spiega che serve un masterizzatore esterno USB

L'avviso sull'alimentazione compare **solo sulle unità esterne** e **prima** di masterizzare, non come diagnosi a disastro avvenuto. Su un'unità interna sarebbe rumore inutile a ogni avvio.

> ⚠️ **Un fallimento di WMI non è bloccante**: si perde il consiglio, non la masterizzazione.

### Come funziona la scrittura (IMAPI2)

Cinque passaggi, tutti attraverso l'API COM nativa di Windows:

1. **Enumerazione**: `IMAPI2.MsftDiscMaster2` restituisce un ID univoco per ogni unità
2. **Inizializzazione**: `MsftDiscRecorder2.InitializeDiscRecorder(id)`, da cui lettera, marca e modello
3. **Interrogazione del supporto**: tipo, stato, capienza e velocità supportate
4. **Decodifica**: FFmpeg produce PCM grezzo 44.1 kHz / 16 bit / stereo
5. **Scrittura Track-At-Once**: `PrepareMedia()` → un `AddAudioTrack()` per traccia → `ReleaseMedia()`, che chiude e finalizza

Tre dettagli non ovvi, tutti scoperti sul campo:

- 🔍 **Il supporto si interroga con un altro oggetto.** `FreeSectorsOnMedia` e `NumberOfExistingTracks` sul writer Track-At-Once rispondono **solo dopo `PrepareMedia()`**, che però ha già aperto la sessione di scrittura: troppo tardi per decidere se il disco va bene. BurnDex usa `MsftDiscFormat2Data` come **sonda di sola lettura**, risponde appena gli si assegna il recorder, e tiene il Track-At-Once per la scrittura vera
- 📏 **IMAPI2 è schizzinoso sul PCM.** Vuole l'audio **nudo, senza header WAV**, allineato a multipli esatti di **2352 byte** (la dimensione di un settore audio Red Book) e lungo **almeno 4 secondi**. Se sgarra di un byte, `AddAudioTrack` fallisce. BurnDex riempie di silenzio quel tanto che basta a soddisfare entrambi i vincoli
- ⚡ **Le velocità non sono una scala continua.** Ogni unità espone pochi gradini discreti (`SupportedWriteSpeeds`, in settori/secondo: es. 599 e 1800, cioè 8x e 24x). Chiedere 4x non rallenta, fa **fallire** `SetWriteSpeed`. BurnDex sceglie il gradino disponibile più vicino senza superare il richiesto, e passa il valore **grezzo** (599, non 600) perché è l'unico che l'unità accetta senza discutere

### I limiti del CD audio

| Limite | Valore | Perché |
|---|---|---|
| ⏱️ **Durata** | ~80 min (BurnDex ne usa **79**) | Il bordo esterno è la zona che i lettori usurati sbagliano più spesso |
| 🎚️ **Campionamento** | 44.1 kHz / 16 bit / stereo, fisso | Lo impone il Red Book: qualsiasi sorgente viene riportata a questo |
| 🏷️ **Metadati** | Nessuno | Il CD-DA non ha campi per titolo o artista |
| 🔇 **Stacchi** | 2 s prima di ogni traccia | Inseriti dal masterizzatore, **inclusi nel conteggio** dei minuti |
| 🚫 **Cancellazione** | Impossibile su CD-R | Il laser brucia fisicamente uno strato di colorante: è un cambiamento di stato della materia |
| 💾 **Spazio temporaneo** | ~10 MB al minuto (~850 MB per un CD pieno) | Il PCM grezzo occupa molto più dei file compressi di partenza |

> ℹ️ **I 700 MB del CD non c'entrano nulla con la dimensione dei tuoi file.** Conta solo la durata: 3 GB di MP4 che durano 75 minuti ci stanno, perché in masterizzazione vengono riconvertiti in PCM.

### Diagnosi degli errori

Gli errori IMAPI arrivano come codici COM incomprensibili. BurnDex riconosce quelli ricorrenti e li traduce in una diagnosi con il rimedio:

| Errore | Diagnosi |
|---|---|
| `0xC0AA020D` *(command timeout)* | L'unità non ha risposto al comando di scrittura. Sui masterizzatori USB è quasi sempre **alimentazione insufficiente**: quando il laser passa in potenza di scrittura l'assorbimento sale di colpo e l'unità si riavvia. Rimedi in ordine: entrambi gli spinotti del cavo, porta diretta sul PC, hub alimentato |

Il riepilogo finale dice **quante tracce sono state scritte davvero**, non quante erano in coda:

```
╔═══════════════════ ✗  Masterizzazione fallita ═══════════════════╗
║   Tracce scritte    0 su 9                                       ║
║   Esito             ✗ interrotto                                 ║
║   Disco             nessun dato audio scritto: e' ancora buono   ║
╚══════════════════════════════════════════════════════════════════╝
```

La distinzione conta: con `0 su 9` il disco è **ancora vergine e riutilizzabile**, con `4 su 9` è scritto a metà e da buttare.

Altre reti di sicurezza:

- 🔓 **`ReleaseMedia()` viene tentata anche in caso di errore**, altrimenti l'unità resta bloccata in accesso esclusivo. È a sua volta protetta: se è stata proprio l'unità a sparire, il fallimento della chiusura non deve coprire l'errore vero
- 📝 Log completo in `logs/burndex.log`, con lo stack trace dell'eccezione COM
- 🛑 **Ctrl+C** durante la scrittura non ferma il laser, il disco è perso comunque, ma l'unità viene rilasciata correttamente

---
