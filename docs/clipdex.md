# ClipDex — tagliare, unire, convertire

Sei operazioni, e una scelta che le governa tutte: se si puo' copiare il flusso
invece di ricodificarlo, si copia. Copiare e' istantaneo e non perde un bit.

> Torna al [README](../README.md).

---

## ✂ ClipDex: tagliare, unire, convertire

**ClipDex** è il banco di montaggio: le operazioni che servono davvero dopo un download, senza aprire un programma di editing. Sei operazioni, un sottocomando ciascuna.

```bash
python -m cli clip                                        # procedura guidata
python -m cli clip taglia -i v.mp4 --da 1:20 --a 3:45
python -m cli clip unisci -d "risultati/musica/Album"
python -m cli clip gif -i v.mp4 --da 0:30 --durata 4
python -m cli clip provino -i v.mp4 --griglia 5x3
python -m cli clip compat -i v.mp4
```

### Copia o ricodifica: è la scelta che governa tutto

| | Copia | Ricodifica |
|---|---|---|
| Cosa fa | sposta i pacchetti già compressi da un contenitore all'altro | li decodifica e li ricomprime |
| Tempo | **secondi** | minuti |
| Qualità | **identica, non perde un bit** | una generazione in meno |
| Vincoli | i tagli si agganciano ai fotogrammi chiave; i file da unire devono essere omogenei | nessuno |

ClipDex sceglie da solo la copia quando può, e **dice sempre quale delle due sta usando**.

### `taglia`: estrarre uno spezzone

I tempi si scrivono come vengono: `90`, `1:30`, `01:02:03.5`.

In copia il taglio è istantaneo, ma l'inizio si aggancia al fotogramma chiave precedente: i fotogrammi compressi insieme non si spezzano a metà. Su un video con i keyframe distanziati lo scostamento si nota, quindi ClipDex **lo misura e te lo dice**:

```
chiesti 4.0 s, ottenuti 7.0: 3.0 s in più. In copia l'inizio si aggancia al
fotogramma chiave precedente, e in questo file sono distanziati. Con --preciso
il taglio cade dove hai detto, al prezzo di una ricodifica
```

Con `--preciso` il taglio cade al fotogramma esatto, verificato: 4,0 s richiesti, 4,0 s ottenuti.

### `unisci`: mettere in fila più file

Prima di unire, ClipDex confronta codec, risoluzione, formato dei pixel, frequenza e caratteristiche audio di tutti i file:

- **omogenei** → li incolla in copia, in un istante;
- **diversi** → li porta tutti alla misura del primo e ricodifica, perché non c'è altro modo: i pacchetti di due codifiche diverse non si possono accostare.

Un file di proporzioni diverse viene **incorniciato, non stirato**, e a un file muto in mezzo viene messo sotto il silenzio della stessa durata: senza, tutto il montaggio audio successivo si sfaserebbe.

Di default aggiunge **un capitolo per ogni file unito**, così il risultato resta navigabile come un DVD. Con `--no-capitoli` si disattiva.

### `gif` e `webp`: ricavare un'animazione

Una GIF ha **256 colori e basta**. La palette generica di FFmpeg su un video con sfumature produce una poltiglia di puntini; calcolarla sui fotogrammi veri costa un passaggio in più. Misurato su tre secondi di video reale, contro gli stessi fotogrammi non ridotti a palette:

| | Fedeltà | Peso |
|---|---|---|
| Un passaggio, palette generica | 24,85 dB | 1414 KB |
| **Due passaggi, palette su misura** | **26,57 dB** | 2479 KB |
| Due passaggi, dither `sierra2_4a` | 26,56 dB | 3133 KB |
| **WebP animato** | - | **283 KB** |

Da qui i default: due passaggi (**+1,72 dB**, si vede), dither ordinato di Bayer, il `sierra2_4a` costa un quarto di peso in più senza dare nulla in cambio, e la spinta verso il **WebP**, che non essendo vincolato ai 256 colori pesa **quasi nove volte meno**. Lo leggono tutti i browser dell'ultimo decennio; se la destinazione è un forum di vent'anni fa, allora serve la GIF.

Le tre leve che contano: `--fps` (sopra 15 il peso raddoppia senza guadagno visibile), `--larghezza` (il fattore che pesa di più) e la durata. Senza indicazioni parte da **un terzo** del video, perché l'inizio è quasi sempre una sigla o una schermata nera.

### `provino`: capire cosa c'è dentro

Una griglia di fotogrammi presi a intervalli regolari su tutta la durata. Per capire cosa contiene un file è più utile di un'anteprima animata: sedici istanti dicono in un colpo d'occhio se è il video giusto, dove cambiano le scene e se ci sono parti nere.

L'intervallo è calcolato perché la griglia copra **tutta** la durata: campionare a intervallo fisso lascerebbe fuori la seconda metà dei video lunghi. La casella ha misura fissa, così la griglia resta regolare anche se il filmato cambia formato a metà.

### `compat`: farlo leggere agli apparecchi datati

Tre vincoli, tutti necessari e tutti spesso violati dai file scaricati:

| Vincolo | Perché |
|---|---|
| Profilo **baseline** | niente fotogrammi B, che i decodificatori più semplici non sanno gestire |
| Colore **yuv420p** | molti file YouTube sono yuv444 o a 10 bit, che una TV del 2012 non decodifica |
| **Indice in testa** al file | senza, un lettore da chiavetta USB deve leggere fino in fondo prima di partire |

Verificato sul file prodotto: `Constrained Baseline`, `yuv420p`, `level 30`, indice nei primi 4 KB.

---
