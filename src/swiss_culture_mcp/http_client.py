"""HTTP-Client, Host-Allowlist und einheitliches Error-Handling.

Logger-Setup lebt hier, weil alle Sicherheits-relevanten Events (geblockte
Hosts, Upstream-Fehler) in diesem Modul entstehen.
"""

import logging
import os
import sys

import httpx

from .constants import TIMEOUT

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

USER_AGENT = "swiss-culture-mcp/1.0 (https://github.com/malkreide/swiss-culture-mcp)"

# Whitelist erlaubter Upstream-Hosts. Nach Redirect-Auflösung wird gegen diese
# Liste geprüft, um SSRF via Open-Redirect (z. B. wenn ein Upstream auf einen
# internen Host umlenkt) zu verhindern.
ALLOWED_HOSTS = frozenset(
    {
        "api3.geo.admin.ch",
        "opendata.swiss",
        "www.newsd.admin.ch",
        "www.lebendige-traditionen.ch",
        "www.gisos.bak.admin.ch",
    }
)

# Modulweiter HTTP-Client (Connection-Pooling). Lazy initialisiert beim ersten
# Tool-Call; in async-Loops via FastMCP-Stdio/HTTP-Lifespan wiederverwendet.
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


async def _get(url: str, params: dict | None = None) -> dict:
    """HTTP GET mit einheitlichem Error-Handling und Host-Allowlist."""
    client = _get_http_client()
    response = await client.get(url, params=params)
    _assert_host_allowed(response.url)
    response.raise_for_status()
    return response.json()


async def _get_text(url: str, params: dict | None = None) -> str:
    """HTTP GET, gibt rohen Text zurück (für HTML/XML)."""
    client = _get_http_client()
    response = await client.get(url, params=params)
    _assert_host_allowed(response.url)
    response.raise_for_status()
    return response.text


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
