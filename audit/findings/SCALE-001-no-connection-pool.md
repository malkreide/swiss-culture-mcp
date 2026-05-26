# SCALE-001 — Kein HTTP-Connection-Pool

- **Severity:** MEDIUM
- **Kategorie:** SCALE
- **Status:** open

## Befund

`_get` und `_get_text` erzeugen pro Aufruf einen neuen `httpx.AsyncClient`. Jeder Tool-Call zahlt erneut TCP/TLS-Setup. Bei Tools wie `bak_isos_statistics`, die mehrere Calls bündeln, vervielfacht sich der Effekt.

## Evidenz

`src/swiss_culture_mcp/server.py:103-122`

```python
async def _get(url: str, params: dict | None = None) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
        ...

async def _get_text(url: str, params: dict | None = None) -> str:
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
        ...
```

## Risiko

- Latenz: jeder Tool-Call +50–200 ms unnötig.
- Ressourcen: bei vielen Concurrent-Calls schnelleres Filedescriptor-Leak-Risiko.
- Upstream-Rate-Limiting trifft eher zu, weil Per-Request-Connection nicht ge-pool't wird.

## Empfehlung

Einen modulweit gehaltenen `httpx.AsyncClient` über `FastMCP`-Lifespan (oder lazy Singleton) verwenden.

```python
_client: httpx.AsyncClient | None = None
async def _client_for() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True,
                                    headers={"User-Agent": "swiss-culture-mcp/1.0"})
    return _client
```

Cleanup über FastMCP-Shutdown-Hook.
