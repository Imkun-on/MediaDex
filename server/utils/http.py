"""Client HTTP condiviso da tutti gli scraper.

Raccoglie in un punto solo gli accorgimenti comuni: User-Agent realistici,
header coerenti per i vari tipi di richiesta, ritardo tra le richieste,
calcolo del backoff per i retry e rilevamento dei challenge Cloudflare.
"""
from __future__ import annotations

import random
import time
from typing import Any

import requests

# ── Pool di User-Agent ────────────────────────────────────────
# User-Agent di browser reali e recenti, tra cui scegliere a caso: una
# richiesta con l'UA di default di requests/httpx viene spesso bloccata.
UA_POOL: list[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
]


def retry_delay(attempt: int, *, base: float = 2.0, jitter: tuple[float, float] = (0.5, 2.0)) -> float:
    """Calcola l'attesa prima del prossimo tentativo dopo un errore.

    Backoff esponenziale: l'attesa raddoppia a ogni tentativo, più un
    jitter casuale che evita retry sincronizzati tra thread. Il tetto di
    120 secondi impedisce attese assurde dopo molti fallimenti.
    """
    delay = base * (2 ** attempt) + random.uniform(*jitter)
    return min(delay, 120.0)


def is_cloudflare_response(response: requests.Response) -> bool:
    """Rileva se la risposta è una pagina di challenge Cloudflare.

    Cloudflare risponde 403/503 con una pagina di verifica browser al posto
    del contenuto: riconoscerla permette allo scraper di reagire (cambiare
    backend, attendere, segnalare) invece di interpretare l'HTML come dati.
    """
    if response.status_code in (403, 503):
        server = response.headers.get('Server', '').lower()
        if 'cloudflare' in server:
            return True
        body = response.text[:2000].lower()
        if any(marker in body for marker in ('cf-browser-verification', 'cf_chl_opt', 'challenge-platform')):
            return True
    return False


class ScraperHTTPClient:
    """Sessione HTTP con scelta del backend e accorgimenti anti-bot.

    Backend disponibili: 'requests' (default, eventualmente potenziato da
    cloudscraper per aggirare Cloudflare) e 'httpx'. Se la libreria
    richiesta non è installata si ripiega in silenzio su requests, così
    gli scraper funzionano comunque con le sole dipendenze di base.
    """

    def __init__(
        self,
        name: str = 'scraper',
        backend: str = 'requests',
        antibot: str | None = None,
        timeout: int = 30,
        request_delay: tuple[float, float] = (0.1, 0.3),
    ) -> None:
        self.name = name
        self.backend = backend
        self.antibot = antibot
        self.timeout = timeout
        self.request_delay = request_delay
        self.ua: str = random.choice(UA_POOL)

        # Crea sessione in base al backend
        if backend == 'requests':
            if antibot == 'cloudscraper':
                try:
                    import cloudscraper
                    self.session = cloudscraper.create_scraper(
                        browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True},
                    )
                except ImportError:
                    self.session = requests.Session()
            else:
                self.session = requests.Session()
        elif backend == 'httpx':
            try:
                import httpx
                self.session = httpx.Client(timeout=timeout, follow_redirects=True)
            except ImportError:
                self.session = requests.Session()
        else:
            self.session = requests.Session()

        # Imposta UA nella sessione requests
        if hasattr(self.session, 'headers'):
            self.session.headers.update({'User-Agent': self.ua})

    def rotate_ua(self) -> str:
        """Cambia User-Agent (utile se il server inizia a rifiutare le richieste)."""
        self.ua = random.choice(UA_POOL)
        if hasattr(self.session, 'headers'):
            self.session.headers['User-Agent'] = self.ua
        return self.ua

    def browsing_headers(self) -> dict[str, str]:
        """Header di una normale navigazione browser (per richiedere pagine HTML)."""
        return {
            'User-Agent': self.ua,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

    def api_headers(self, *, xhr: bool = False) -> dict[str, str]:
        """Header per chiamate API JSON; con xhr=True simula una richiesta AJAX."""
        h = {
            'User-Agent': self.ua,
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
        }
        if xhr:
            h['X-Requested-With'] = 'XMLHttpRequest'
        return h

    def embed_headers(self, referer: str) -> dict[str, str]:
        """Header per i player incorporati in iframe.

        Molti player verificano il Referer e gli header Sec-Fetch-* per
        accettare solo richieste che sembrano provenire dalla pagina che
        li ospita.
        """
        h = self.browsing_headers()
        h['Referer'] = referer
        h['Sec-Fetch-Dest'] = 'iframe'
        h['Sec-Fetch-Mode'] = 'navigate'
        h['Sec-Fetch-Site'] = 'cross-site'
        return h

    def download_headers(self, referer: str) -> dict[str, str]:
        """Header per il download di file binari.

        'Accept-Encoding: identity' chiede il file non compresso: per i
        contenuti multimediali la compressione è inutile e nasconderebbe la
        dimensione reale (Content-Length) utile alle barre di avanzamento.
        """
        h = {
            'User-Agent': self.ua,
            'Accept': '*/*',
            'Accept-Encoding': 'identity;q=1, *;q=0',
            'Referer': referer,
            'Connection': 'keep-alive',
        }
        return h

    def get(self, url: str, **kwargs: Any) -> requests.Response:
        """GET con un piccolo ritardo casuale prima, per non martellare il server."""
        if self.request_delay:
            time.sleep(random.uniform(*self.request_delay))
        kwargs.setdefault('timeout', self.timeout)
        return self.session.get(url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> requests.Response:
        """POST con un piccolo ritardo casuale prima, per non martellare il server."""
        if self.request_delay:
            time.sleep(random.uniform(*self.request_delay))
        kwargs.setdefault('timeout', self.timeout)
        return self.session.post(url, **kwargs)
