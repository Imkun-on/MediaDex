"""Rifare il video: il comando, la barra, il confronto prima/dopo.

Qui si esegue e basta. COSA eseguire - quali filtri, a che altezza, con che
qualita' - lo ha gia' deciso ``presets.py``; questo modulo prende la catena
gia' scritta, ci attacca l'encoder e l'audio, lancia FFmpeg e conta i
fotogrammi che escono.

La separazione ha un motivo pratico: la parte che decide e' tutta aritmetica e
si puo' leggere e correggere senza toccare un processo esterno, mentre la
parte che esegue e' tutta processo esterno e non contiene una sola decisione.
"""
from __future__ import annotations

import os
import subprocess
import tempfile

from rich.markup import escape
from rich.progress import (
    Progress, SpinnerColumn, BarColumn, TextColumn,
    TaskProgressColumn, TimeElapsedColumn, TimeRemainingColumn,
)
from rich.table import Column

from server.config import i18n
from server.utils.console import console, setup_logger

t = i18n.t

log = setup_logger('pixdex', 'pixdex.log')


def _progress() -> Progress:
    """Barra di avanzamento della rimasterizzazione.

    Tiene il tempo rimanente oltre a quello trascorso: una codifica lunga
    senza stima e' indistinguibile da una bloccata, e la differenza conta
    quando si tratta di ore.
    """
    return Progress(
        SpinnerColumn(style='bright_blue'),
        TextColumn('{task.description}', table_column=Column(
            width=26, no_wrap=True, overflow='ellipsis')),
        BarColumn(bar_width=None, style='grey37',
                  complete_style='bright_blue', finished_style='bright_green'),
        TaskProgressColumn(),
        TextColumn('{task.fields[extra]}', style='dim'),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    )


def _comando_encoder(gpu: bool, crf: int) -> list[str]:
    """Restituisce gli argomenti del codificatore video.

    Il codificatore hardware AMD e' molto piu' veloce ma, a parita' di peso,
    restituisce un'immagine meno pulita: su una rimasterizzazione, dove il
    punto e' proprio la qualita', il software resta il default e l'hardware
    e' una scelta consapevole per i file lunghi.
    """
    if gpu:
        # I valori sono molto piu' generosi di quelli che verrebbero spontanei,
        # e c'e' un motivo misurato. Con cqp 20/22 il codificatore AMD rimette
        # i quadretti che i filtri hanno appena tolto: sullo stesso spezzone,
        # da 1.169 dopo i filtri a 2.184 dopo la codifica - peggio del non
        # aver fatto niente, visto che il solo ingrandimento sta a 1.618.
        #
        #     dopo i filtri, senza codifica    1.169
        #     libx264 CRF 18                   1.150
        #     amf cqp 12/14                    1.223
        #     amf cqp 16/18                    1.632
        #     amf cqp 20/22                    2.184
        #
        # A 12/14 la pulizia sopravvive, al prezzo di un file circa tre volte
        # e mezzo piu' pesante. E' un baratto accettabile solo perche' su una
        # rimasterizzazione il punto e' togliere i difetti: risparmiare spazio
        # rimettendoli dentro non ha senso.
        return ['-c:v', 'h264_amf', '-quality', 'quality',
                '-rc', 'cqp', '-qp_i', '12', '-qp_p', '14', '-qp_b', '16']
    return ['-c:v', 'libx264', '-preset', 'medium', '-crf', str(crf)]


# Codec audio che il contenitore MP4 sa ospitare. L'elenco e' volutamente
# corto e conservativo: ci stanno quelli che arrivano davvero dai file che si
# rimasterizzano, e per tutto il resto si ricodifica. Sbagliare per eccesso di
# prudenza costa una ricodifica dell'audio; sbagliare nell'altro verso non
# produce niente.
_AUDIO_DA_MP4 = frozenset({'aac', 'mp3', 'ac3', 'eac3', 'alac', 'opus', 'mp2'})


def _comando_audio(info: dict) -> list[str]:
    """Come trattare la traccia audio: copiarla, o ricodificarla in AAC.

    L'uscita e' sempre un .mp4 (vedi ``nome_uscita``), ma l'ingresso puo'
    essere un .wmv, un .avi, un .flv: contenitori che ospitano codec che
    l'MP4 non sa scrivere. Copiare la traccia cosi' com'e' faceva fallire
    FFmpeg con "Could not find tag for codec wmav2 in stream #1", e cio' che
    restava sul disco era un .mp4 da zero byte. Un intero formato di
    partenza - tutti i .wmv - non si poteva rimasterizzare.

    Copiare resta il caso normale, ed e' quello che conta: sulla stragrande
    maggioranza dei file l'audio e' gia' AAC e attraversa il programma senza
    essere toccato. La ricodifica scatta solo quando l'alternativa sarebbe
    non produrre nulla.

    Un file senza audio non ha bisogno di niente: senza flusso da mappare,
    ``-c:a`` e' un'opzione che non si applica a nessuno.
    """
    codec = (info.get('audio_codec') or '').lower()
    if not codec:
        return []
    if codec in _AUDIO_DA_MP4:
        return ['-c:a', 'copy']
    log.info("Audio '%s' non ospitabile in MP4: si ricodifica in AAC", codec)
    return ['-c:a', 'aac', '-b:a', '192k']


def _scorri_progresso(proc, su_fotogramma, su_velocita) -> bool:
    """Legge l'avanzamento di FFmpeg e lo inoltra a due callback.

    L'avanzamento arriva da ``-progress pipe:1``, che stampa coppie
    chiave=valore a intervalli regolari: e' l'unico modo affidabile di sapere
    a che fotogramma e' arrivato, perche' l'output normale di FFmpeg usa
    ritorni a capo che non si leggono riga per riga.

    Restituisce False se l'utente ha interrotto: separare la lettura dal modo
    in cui l'avanzamento viene mostrato e' quello che permette alla stessa
    funzione di alimentare tanto la barra Rich del terminale quanto quella
    della finestra grafica.
    """
    try:
        for riga in proc.stdout:
            riga = riga.strip()
            if riga.startswith('frame='):
                try:
                    su_fotogramma(int(riga.split('=', 1)[1]))
                except ValueError:
                    continue
            elif riga.startswith('speed='):
                su_velocita(riga.split('=', 1)[1].strip())
    except KeyboardInterrupt:
        proc.terminate()
        return False
    finally:
        proc.stdout.close()
    return True


def rimasterizza(info: dict, dst: str, catena: str, gpu: bool, crf: int,
                  avanzamento=None) -> bool:
    """Esegue FFmpeg mostrando l'avanzamento, restituisce True se ha funzionato.

    Con ``avanzamento`` valorizzato — e' il caso della GUI — le notifiche
    vanno a quella funzione, che riceve ``(fotogramma, totale, velocita)``, e
    a terminale non si stampa nulla. Senza, si disegna la solita barra Rich.
    """
    totale = info['frames'] or 0

    cmd = ['ffmpeg', '-hide_banner', '-v', 'error', '-y',
           '-i', info['path'],
           '-vf', catena,
           *_comando_encoder(gpu, crf),
           *_comando_audio(info),
           '-movflags', '+faststart',
           '-progress', 'pipe:1', '-nostats',
           dst]
    log.info('Comando FFmpeg: %s', ' '.join(cmd))

    # Lo standard error finisce su file: se restasse in una pipe non letta,
    # una diagnostica lunga riempirebbe il buffer del sistema operativo e
    # bloccherebbe FFmpeg a meta' lavoro, senza alcun messaggio.
    with tempfile.TemporaryFile(mode='w+', encoding='utf-8',
                                errors='replace') as err:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=err,
                                text=True, encoding='utf-8', errors='replace',
                                bufsize=1)

        if avanzamento is not None:
            velocita = ['']

            def _frame(n: int) -> None:
                avanzamento(n, totale, velocita[0])

            def _speed(v: str) -> None:
                velocita[0] = v

            completato = _scorri_progresso(proc, _frame, _speed)
        else:
            with _progress() as prog:
                task = prog.add_task(t('run.working'),
                                     total=totale or None, extra='')
                completato = _scorri_progresso(
                    proc,
                    lambda n: prog.update(
                        task, completed=min(n, totale) if totale else n),
                    lambda v: prog.update(task, extra=v),
                )

        if not completato:
            console.print(t('run.interrupted'))
            return False

        codice = proc.wait()
        if codice != 0:
            err.seek(0)
            dettaglio = err.read().strip().splitlines()
            ultima = dettaglio[-1] if dettaglio else f'exit {codice}'
            log.error('FFmpeg fallito (%s): %s', codice, ultima)
            console.print(t('run.failed', reason=escape(ultima)))
            return False

    return True


def confronto(src: str, dst: str, destinazione: str,
               istante: float) -> str | None:
    """Salva un PNG con lo stesso fotogramma prima e dopo, affiancati.

    E' l'unico modo onesto di giudicare il risultato: i numeri di bitrate non
    dicono nulla sull'aspetto, e il confronto a memoria fra due riproduzioni
    successive inganna sempre in favore della seconda. I due fotogrammi sono
    portati alla stessa altezza perche' altrimenti l'ingrandimento renderebbe
    il secondo automaticamente piu' grande, e quindi piu' convincente a
    prescindere dal merito.
    """
    filtro = ('[0:v]scale=-2:540:flags=lanczos,setsar=1[a];'
              '[1:v]scale=-2:540:flags=lanczos,setsar=1[b];'
              '[a][b]hstack=inputs=2')
    cmd = ['ffmpeg', '-hide_banner', '-v', 'error', '-y',
           '-ss', str(istante), '-i', src,
           '-ss', str(istante), '-i', dst,
           '-filter_complex', filtro, '-frames:v', '1', destinazione]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except (subprocess.CalledProcessError, OSError) as exc:
        log.warning('Confronto non riuscito: %s', exc)
        return None
    return destinazione if os.path.exists(destinazione) else None


def nome_uscita(src: str, altezza: int, cartella: str | None) -> str:
    """Costruisce il nome del file rimasterizzato accanto all'originale.

    Il suffisso porta la risoluzione perche' e' l'unica cosa che si vuole
    sapere guardando la cartella mesi dopo, e l'originale non viene mai
    sovrascritto: una rimasterizzazione e' un'interpretazione, non una
    correzione, e la si rifa' volentieri con parametri diversi.
    """
    radice, _ext = os.path.splitext(src)
    if cartella:
        radice = os.path.join(cartella, os.path.basename(radice))
    return f'{radice} [PixDex {altezza}p].mp4'
