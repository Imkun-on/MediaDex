"""Fa funzionare ``python -m cli``: delega tutto allo smistatore."""
from cli.main import main

raise SystemExit(main())
