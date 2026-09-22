# PixDex — rimasterizzare un video

Cosa puo' fare davvero, e soprattutto cosa non puo'. Nessun filtro ricostruisce
dettaglio che nel file non c'e': la parte piu' onesta di questa pagina e'
quella che dice quando ingrandire non serve a niente.

> Torna al [README](../README.md).

---

## 🎞 PixDex: rimasterizzare un video

### A cosa serve, e soprattutto cosa non fa

**PixDex** prende un video di qualità scarsa e lo ripulisce: toglie i difetti lasciati dalla compressione, appiana le sfumature a scalini e lo porta a una risoluzione più alta con un ingrandimento fatto bene.

Va detto subito, perché è la cosa che genera più aspettative sbagliate: **PixDex non inventa dettaglio che nel file non c'è.** Un ingrandimento, per quanto curato, non può ricostruire quello che la compressione ha buttato via. Quello lo fanno i modelli di intelligenza artificiale, che ricostruiscono un dettaglio *plausibile*, ma inventato, e che a schermo intero spesso tradisce.

PixDex lavora **in sottrazione**: toglie il disturbo, non aggiunge finta incisione.

### Perché funziona lo stesso

Su materiale YouTube i difetti che l'occhio nota davvero sono tre, e sono tutti rimovibili:

| Difetto | Dove si vede | Come si toglie |
|---|---|---|
| 🧱 **Quadretti** (blocking) | scene scure, movimenti rapidi | `deblock`, riduzione del disturbo temporale |
| 🪜 **Bande a scalini** | cieli, dissolvenze, sfumature | `deband`, svolta a 10 bit |
| 👻 **Aloni sui contorni** | intorno a testi e bordi netti | riduzione del disturbo, poi nitidezza adattiva |

Tolti quelli, **la stessa identica quantità di dettaglio si legge molto meglio**. È il 70% del miglioramento percepito, a una frazione del costo dell'AI.

### L'ordine dei filtri non è negoziabile

È la parte che quasi tutte le guide sbagliano, e da sola separa un buon risultato da un pasticcio:

1. **Deinterlacciamento**, se serve: lavorare su semiquadri falsa tutto il resto
2. **Sblocco e riduzione del disturbo**, *prima* di ogni nitidezza: altrimenti si incide il disturbo e lo si rende permanente
3. **Sbandatura, svolta a 10 bit**, a 8 bit il rimedio genera bande nuove: appianare un gradino richiede valori intermedi che a 8 bit non esistono
4. **Ingrandimento**, su un fotogramma ormai pulito
5. **Nitidezza adattiva**, per ultima: applicarla prima di ingrandire butta via metà del lavoro nella riscalatura

### I cinque preset

| Preset | Per cosa | Cosa fa di diverso |
|---|---|---|
| 🧼 **Pulito** | sorgente già discreta | toglie quadretti e bande, **non ingrandisce**. Il più veloce |
| ⚖️ **Standard** | il normale video YouTube | pulizia misurata più ingrandimento |
| 🔨 **Forte** | sorgente molto rovinata | accetta di perdere micro-dettaglio pur di togliere il disturbo |
| 🎨 **Animazione** | cartoni e anime | mano leggerissima sul disturbo (mangia le linee, che nell'animazione *sono* il disegno), mano pesante sulle bande |
| 📼 **Vecchio** | materiale televisivo o da nastro | separa prima i semiquadri, poi pulisce a fondo |

Senza indicazioni, il preset lo sceglie la **diagnosi**.

### Come è tarata la sbandatura

`deband` **non appiattisce i gradini: li dissolve in rumore**, esattamente come fa il dithering. È il modo giusto di togliere una banda vera, un contorno visibile viene barattato con una granulosità che l'occhio non nota. Ma il filtro lavora su tutto il fotogramma, comprese le zone piatte dove banda non ce n'è: lì non c'è niente da barattare e resta solo il rumore.

Misurato su un video molto compresso (AV1 a 305 kbit/s, da 720p a 1440p), nella stessa parete scura uniforme:

| Taratura | Granulosità | Quadretti |
|---|---|---|
| solo ingrandimento, nessun filtro | 0,805 | 1,618 |
| soglia 0,035 · raggio 24 · nitidezza 0,55 | 2,686 | 1,204 |
| **soglia 0,010 · raggio 16 · nitidezza 0,35** | **1,581** | **1,166** |

La taratura prudente vince su **entrambi** i fronti: meno rumore *e* anche meno quadretti. Quella aggressiva non comprava niente, sporcava e basta, e il file finiva per pesare il triplo perché l'encoder spendeva bit per descrivere quel puntinato.

Da qui le soglie basse dei preset. L'unica eccezione è **Animazione**, che resta la più decisa: le grandi campiture di colore piatto dei cartoni bandano davvero, e lì il baratto conviene.

### La diagnosi

Prima di toccare qualsiasi cosa, PixDex legge il file con `ffprobe` e guarda tre grandezze:

- la **risoluzione**, che dice se ha senso ingrandire;
- i **bit per pixel**, bitrate diviso per pixel e fotogrammi al secondo, che dicono quanto la compressione ha infierito. Sotto **0,05 bpp** i quadretti si vedono; sotto **0,025** si vedono anche in movimento;
- l'**ordine dei campi**, che dice se il materiale è televisivo.

Nessuna delle tre richiede di decodificare il video, quindi il consiglio arriva **istantaneo** anche su un file da un'ora.

```bash
python -m cli pix -i video.mp4 --info      # analizza e consiglia, non scrive nulla
```

### Fin dove ingrandisce, e come sceglierlo

**Al terzo passo PixDex ti fa scegliere**, mostrando per ogni modalità il risultato su *quel* file, non l'etichetta commerciale:

```
┌────┬────────────────┬───────────────────────┬────────────────────┐
│  # │ Come           │             Risultato │ Quanto vale        │
├────┼────────────────┼───────────────────────┼────────────────────┤
│  1 │ ★ Automatica   │    360p → 720p  2.00× │ credibile          │
│  2 │ Solo pulizia   │           360p  1.00× │ originale          │
│  3 │ HD  1080p      │   360p → 1080p  3.00× │ si ammorbidisce    │
│  4 │ 2K  1440p      │   360p → 1440p  4.00× │ solo più pesante   │
│  5 │ 4K  2160p      │   360p → 2160p  6.00× │ solo più pesante   │
│  6 │ Altra altezza… │                       │                    │
└────┴────────────────┴───────────────────────┴────────────────────┘
```

È il punto in cui il programma è più onesto: **la stessa tabella che ti offre il 4K ti dice, sulla stessa riga, che da un 360p quel 4K non aggiunge un solo dettaglio vero**, solo un file più pesante. Le soglie sono queste:

| Fattore | Giudizio | Cosa succede davvero |
|---|---|---|
| **fino a 2×** | 🟢 credibile | l'interpolazione ha abbastanza pixel veri da cui partire |
| **fino a 3×** | 🟡 si ammorbidisce | regge, ma l'immagine perde mordente |
| **oltre 3×** | 🔴 solo più pesante | si sta solo scrivendo un numero più grande nei metadati |

**Puoi scegliere il 4K comunque.** PixDex ti avvisa una volta, nel piano di lavoro, e poi fa quello che gli hai chiesto senza rimproverarti a ogni lancio.

L'**automatica** (★) si ferma al doppio e sale al gradino successivo della scala standard: un 360p arriva a 720p, un 540p a 1080p. È l'unico valore difendibile senza aver visto il file, ed è quello che vale con `--yes`.

Da riga di comando la stessa scelta si fissa con `--height`:

```bash
python -m cli pix -i video.mp4 --height auto   # fino al doppio (default)
python -m cli pix -i video.mp4 --height none   # solo pulizia, risoluzione originale
python -m cli pix -i video.mp4 --height hd     # 1080p
python -m cli pix -i video.mp4 --height 2k     # 1440p
python -m cli pix -i video.mp4 --height 4k     # 2160p
python -m cli pix -i video.mp4 --height 900    # altezza esatta in pixel
```

### Il confronto prima/dopo

A fine lavoro PixDex salva un PNG con **lo stesso fotogramma prima e dopo, affiancati**. È l'unico modo onesto di giudicare: i numeri di bitrate non dicono nulla sull'aspetto, e il confronto a memoria fra due riproduzioni successive inganna sempre a favore della seconda.

I due fotogrammi vengono portati **alla stessa altezza**: altrimenti l'ingrandimento renderebbe il secondo automaticamente più grande, e quindi più convincente a prescindere dal merito. Il fotogramma si prende a **un terzo** del video, perché l'inizio è quasi sempre una sigla o una schermata nera.

### Codifica: software o GPU

| | `libx264` (default) | `--gpu` (`h264_amf`) |
|---|---|---|
| Velocità | lenta | **2,4× più veloce** (misurato su Ryzen 5 3500U + Vega 8) |
| Qualità a parità di peso | **migliore** | un filo meno pulita |
| Quando | il caso normale | file lunghi, quando il tempo conta più della resa |

L'**audio non viene mai ricodificato**: viene copiato identico dal file di partenza, quindi non perde niente.

### Opzioni della riga di comando (PixDex)

| Opzione | Breve | Default | Cosa fa |
|---|---|---|---|
| `--input` | `-i` | *(elenco)* | Video da rimasterizzare. Senza, elenca quelli scaricati e li fa scegliere |
| `--output` | `-o` | *accanto all'originale* | File di destinazione. L'originale non viene **mai** sovrascritto |
| `--base` | `-b` | `risultati/musica` | Cartella in cui cercare i video |
| `--preset` | `-p` | *(dalla diagnosi)* | `pulito`, `standard`, `forte`, `animazione`, `vecchio` |
| `--height` | | `auto` | `auto` (fino al doppio), `none` (solo pulizia), `hd`, `2k`, `4k`, o un'altezza in pixel. Senza, la si sceglie a schermo |
| `--crf` | | `18` | Qualità di libx264: più basso = migliore e più pesante |
| `--gpu` | | *spento* | Codifica sulla GPU AMD |
| `--no-compare` | | *spento* | Non salvare l'immagine di confronto |
| `--info` | | *spento* | Analizza e mostra la diagnosi, senza rimasterizzare |
| `--yes` | `-y` | *spento* | Nessuna domanda: usa il preset consigliato e parte |

### Esempi

```bash
python -m cli pix                                  # procedura guidata
python -m cli pix -i video.mp4 --info              # solo analisi, non scrive
python -m cli pix -i video.mp4 -p animazione       # preset esplicito
python -m cli pix -i video.mp4 --height 1080 --gpu # 1080p, codifica su GPU
python -m cli pix -i video.mp4 -y                  # nessuna domanda
```

### Nella GUI

`MediaDex.py` ha la sezione **Rimasterizza**: si sceglie il file, si preme **Analizza** e la diagnosi compare in un pannello (cosa non va, e quale preset lo affronta) *prima* di impegnare minuti od ore di lavorazione. A fine lavoro il confronto prima/dopo si vede direttamente nella finestra, accanto alla diagnosi.

> ⏱ **Quanto ci mette.** Dipende dal processore: la rimasterizzazione è l'operazione più pesante di tutto il progetto. Durante la lavorazione la barra mostra fotogrammi elaborati e velocità in tempo reale (`1.2x` significa che va più veloce della durata del video, `0.5x` il doppio del tempo). Con `--gpu` si va molto più veloci.

---
