"""HTTP-Client, Host-Allowlist und einheitliches Error-Handling.

Logger-Setup lebt hier, weil alle Sicherheits-relevanten Events (geblockte
Hosts, Upstream-Fehler) in diesem Modul entstehen.
"""

import asyncio
import logging
import os
import sys

import httpx

from . import __version__
from .constants import PROJECT_URL, TIMEOUT

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger("swiss_culture_mcp")

if not logger.handlers:
    _handler = logging.StreamHandler(sys.stderr)
    _handler.setFormatter(
        logging.Formatter(
            '{"ts":"%(asctime)s","lvl":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}'
        )
    )
    logger.addHandler(_handler)
    logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
    logger.propagate = False

# ---------------------------------------------------------------------------
# Host-Allowlist + Pool
# ---------------------------------------------------------------------------

USER_AGENT = f"swiss-culture-mcp/{__version__} ({PROJECT_URL})"

# Whitelist erlaubter Upstream-Hosts. Nach Redirect-Auflösung wird gegen diese
# Liste geprüft, um SSRF via Open-Redirect (z. B. wenn ein Upstream auf einen
# internen Host umlenkt) zu verhindern.
ALLOWED_HOSTS = frozenset(
    {
        "api3.geo.admin.ch",
        "opendata.swiss",
        # opendata.swiss beantwortet die CKAN-Aufrufe mit 302 auf diesen Host
        # (`{"help": "https://ckan.opendata.swiss/api/3/action/help_show..."}`).
        # Ohne ihn scheiterte JEDER `bak_get_opendata`-Aufruf an der Pruefung
        # unten — produktiv, waehrend die Unit-Tests gruen blieben. Gefunden hat
        # das der erste Live-Lauf, den es je gab (16.8.2026).
        # `test_umleitungsziele.py` haelt fest, dass das Ziel, auf dem wir
        # tatsaechlich landen, in dieser Liste steht.
        "ckan.opendata.swiss",
        "www.newsd.admin.ch",
        "www.lebendige-traditionen.ch",
        "www.gisos.bak.admin.ch",
    }
)

# Modulweiter HTTP-Client (Connection-Pooling). Lazy initialisiert beim ersten
# Tool-Call; in async-Loops via MCPServer-Stdio/HTTP-Lifespan wiederverwendet.
_http_client: httpx.AsyncClient | None = None


def _get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            timeout=TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
    return _http_client


def _assert_host_allowed(url: httpx.URL) -> None:
    if url.host not in ALLOWED_HOSTS:
        logger.warning("blocked_host_after_redirect host=%s url=%s", url.host, url)
        raise httpx.RequestError(f"Host nicht erlaubt: {url.host}")


# ---------------------------------------------------------------------------
# Ein zweiter Versuch bei voruebergehenden Stoerungen
# ---------------------------------------------------------------------------
#
# Gemessen am 3.11.2026: `api3.geo.admin.ch` antwortet meist unter einer
# Sekunde, hat aber Ausreisser — AG 30,5 s, TI 7,9 s, mit und ohne
# Zwischenspeicher. Nach `TIMEOUT` (20 s) gibt der Client auf, und das Werkzeug
# meldet «Zeitueberschreitung», obwohl eine zweite Anfrage gleich danach in
# unter einer Sekunde antwortet. Der Live-Test lief bei 26 Anfragen je Lauf in
# 2 von rund 20 Laeufen genau da hinein.
#
# Wiederholt wird **einmal**, und nur, was eine Stoerung ist: Zeitueberschreitung,
# Netzwerkfehler, eine Gegenseite, die die Verbindung ohne Antwort schliesst,
# und HTTP 502/503/504. Eine Antwort wird nie wiederholt — 4xx, 500, ein
# verbotener Zielhost (`_assert_host_allowed`), eine Umleitungsschleife: Sie
# kaeme beim zweiten Mal gleich zurueck, und ein zweiter Versuch taete so, als
# waere sie eine Stoerung. Alle Aufrufe sind GET, wiederholen ist also folgenlos.
#
# Der Preis: Haengen beide Versuche, wartet ein Werkzeug hoechstens
# 2 x TIMEOUT + PAUSE (41 s) statt 20 s. Bei einem Ausreisser wie dem gemessenen
# sind es gut 21 s — und eine Antwort statt einer Fehlermeldung.

VERSUCHE = 2
PAUSE_S = 1.0
_VORUEBERGEHENDE_FEHLER = (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError)
_VORUEBERGEHENDE_STATUS = frozenset({502, 503, 504})
# Modul-Alias: Tests ersetzen diese Pause, nicht `asyncio.sleep` selbst — das
# wuerde die Mechanik im ganzen Prozess entschaerfen (CLAUDE.md, «Tests»).
_pause = asyncio.sleep


async def _abrufen(url: str, params: dict | None) -> httpx.Response:
    """GET mit Host-Allowlist und genau einem zweiten Versuch bei einer Stoerung."""
    client = _get_http_client()
    for versuch in range(1, VERSUCHE + 1):
        letzter = versuch == VERSUCHE
        try:
            response = await client.get(url, params=params)
        except _VORUEBERGEHENDE_FEHLER as e:
            if letzter:
                raise
            grund = type(e).__name__
        else:
            # Ausserhalb des `try`: Ein verbotener Host ist eine Antwort, keine
            # Stoerung, und wird nicht wiederholt.
            _assert_host_allowed(response.url)
            if letzter or response.status_code not in _VORUEBERGEHENDE_STATUS:
                response.raise_for_status()
                return response
            grund = f"HTTP {response.status_code}"
        logger.warning("upstream_retry versuch=%d grund=%s url=%s", versuch, grund, url)
        await _pause(PAUSE_S)
    raise AssertionError("unerreichbar")  # pragma: no cover


async def _get(url: str, params: dict | None = None) -> dict:
    """HTTP GET mit einheitlichem Error-Handling und Host-Allowlist."""
    return (await _abrufen(url, params)).json()


async def _get_text(url: str, params: dict | None = None) -> str:
    """HTTP GET, gibt rohen Text zurück (für HTML/XML)."""
    return (await _abrufen(url, params)).text


def _handle_error(e: Exception) -> str:
    """Einheitliche, handlungsorientierte Fehlermeldungen auf Deutsch.

    Upstream-Response-Bodies werden NICHT an den LLM zurückgegeben
    (Information-Disclosure-Schutz). Volle Diagnose landet im Log.
    """
    if isinstance(e, httpx.HTTPStatusError):
        code = e.response.status_code
        url = str(e.response.request.url) if e.response.request else "?"
        logger.warning(
            "upstream_http_error code=%s url=%s body=%r", code, url, e.response.text[:500]
        )
        if code == 404:
            return "Fehler: Ressource nicht gefunden. Bitte Suchbegriff oder ID prüfen."
        if code == 403:
            return "Fehler: Zugriff verweigert. Die Ressource ist möglicherweise nicht öffentlich."
        if code == 429:
            return "Fehler: Anfragelimit überschritten. Bitte etwas warten und erneut versuchen."
        if code >= 500:
            return f"Fehler: Server-Fehler (HTTP {code}). Die API ist möglicherweise vorübergehend nicht verfügbar."
        return f"Fehler: HTTP {code} (Upstream gemeldet)."
    if isinstance(e, httpx.TimeoutException):
        logger.warning("upstream_timeout: %s", e)
        return "Fehler: Zeitüberschreitung. Die API antwortet nicht. Bitte später erneut versuchen."
    if isinstance(e, httpx.ConnectError):
        logger.warning("upstream_connect_error: %s", e)
        return "Fehler: Verbindung fehlgeschlagen. Bitte Netzwerkverbindung prüfen."
    logger.exception("unhandled_tool_error: %s", type(e).__name__)
    return f"Fehler: {type(e).__name__}."
