"""Lo smistatore: ``python -m cli <mestiere> [argomenti]``.

    python -m cli audio          cerca e scarica da YouTube
    python -m cli burn           masterizza un CD audio
    python -m cli pix            rimasterizza un video
    python -m cli clip           taglia, unisce, converte

Perche' esiste, visto che i quattro si lanciano gia' da soli
    Perche' ``python -m cli.pix`` costringe a sapere che PixDex sta in un file
    che si chiama ``pix``. Questo permette di scriverlo come si pensa, e
    soprattutto di scoprire quali siano i quattro senza aprire la cartella:
    ``python -m cli`` senza argomenti li elenca.

Cosa NON fa
    Non interpreta gli argomenti dei mestieri. Li passa cosi' come sono, e
    ciascuno ha il proprio ``argparse`` con le proprie opzioni e il proprio
    ``--help``: raccoglierli qui in un unico parser vorrebbe dire un elenco di
    sessanta opzioni di cui tre quarti non valgono per il comando che si sta
    scrivendo.
"""
from __future__ import annotations

import sys

MESTIERI = {
    'audio': ('cli.audio', 'cerca e scarica da YouTube'),
    'burn':  ('cli.burn',  'masterizza un CD audio'),
    'pix':   ('cli.pix',   'rimasterizza un video'),
    'clip':  ('cli.clip',  'taglia, unisce, converte'),
}


def main(argomenti: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argomenti is None else argomenti)

    if not argv or argv[0] in ('-h', '--help'):
        print(__doc__.split('Perche\'')[0].rstrip())
        print('Mestieri disponibili:')
        for nome, (_, che_fa) in MESTIERI.items():
            print(f'  {nome:8} {che_fa}')
        print("\nPer le opzioni di uno: python -m cli <mestiere> --help")
        return 0

    scelto = argv[0]
    if scelto not in MESTIERI:
        print(f"Non conosco '{scelto}'. I mestieri sono: "
              f"{', '.join(MESTIERI)}", file=sys.stderr)
        return 2

    modulo_nome = MESTIERI[scelto][0]

    # Si importa solo quello che serve: ciascuno si porta dietro Rich e, nel
    # caso di audio, yt-dlp. Importarli tutti e quattro per lanciarne uno
    # sarebbe un secondo buttato a ogni comando.
    import importlib
    modulo = importlib.import_module(modulo_nome)

    # argparse legge sys.argv: gli si toglie di mezzo il nome del mestiere,
    # altrimenti lo troverebbe come primo argomento posizionale e si
    # lamenterebbe di qualcosa che ha gia' fatto il suo lavoro.
    sys.argv = [f'python -m cli {scelto}'] + argv[1:]
    return modulo.main() or 0


if __name__ == '__main__':
    raise SystemExit(main())
