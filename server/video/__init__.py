"""Cosa si fa a un filmato: leggerlo, rimasterizzarlo, tagliarlo, convertirlo.

Due mestieri vicini che condividono lo stesso attrezzo. PixDex rifa' un video
per migliorarlo, ClipDex lo taglia e lo trasforma senza pretendere di
migliorarlo: entrambi passano da FFmpeg, ed entrambi partono dalla stessa
lettura di cosa c'e' dentro al file - ``probe.py``, che prima era scritta due
volte.

Cosa c'e' qui sotto
    ``probe``     leggere il file e dire cosa non va.
    ``presets``   decidere come sistemarlo: i cinque trattamenti, e fin dove
                  ha senso ingrandire.
    ``remaster``  eseguire quella decisione.
    ``edit``      le sei operazioni di montaggio, che non decidono niente.

L'elenco qui sotto e' l'API pubblica dello strato
    E' anche il punto della ristrutturazione che serviva di piu'. Prima
    l'interfaccia grafica arrivava dentro PixDex a prendersi ``px._fattore`` e
    ``px._giudizio_fattore``: due nomi che l'underscore dichiarava privati e
    che erano invece, di fatto, il contratto fra il motore e la finestra.
    Nessuno poteva cambiarli sapendo cosa stava rompendo.

    Adesso quello che sta scritto qui e' quello su cui si puo' contare, e
    tutto il resto e' davvero affar nostro.
"""

from server.video.probe import (          # noqa: F401
    diagnosi,
    e_un_filmato,
    probe,
)
from server.video.presets import (        # noqa: F401
    CRF_DEFAULT,
    FATTORE_BUONO,
    FATTORE_MOLLE,
    PRESETS,
    altezza_obiettivo,
    catena_filtri,
    fattore_ingrandimento,
    giudizio_fattore,
    risolvi_altezza,
)
from server.video.remaster import (       # noqa: F401
    confronto,
    nome_uscita,
    rimasterizza,
)
