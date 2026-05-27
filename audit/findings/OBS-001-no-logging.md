# OBS-001 — Kein Logging im Server

> **✅ CLOSED in Run-2** — behoben durch PR #2 (commit 391e093). Strukturierte JSON-Logs auf stderr, konfigurierbar via `LOG_LEVEL`. Logger lebt in `src/swiss_culture_mcp/http_client.py:18-30`.

- **Severity:** HIGH (für Production-Deployment), MEDIUM (für reines stdio-Demo)
- **Kategorie:** OBS
- **Status:** open

## Befund

Der Server enthält keinerlei `logging`-Setup, keinen Logger-Aufruf, keine strukturierten Logs. Fehler werden via `_handle_error` ausschliesslich als String an den Client/LLM zurückgegeben, aber nirgendwo persistiert.

## Evidenz

```bash
$ grep -n "import logging\|logger\|log\." src/swiss_culture_mcp/server.py
# (keine Treffer)
```

`src/swiss_culture_mcp/server.py:125-142` — `_handle_error` schreibt nicht in Log:

```python
def _handle_error(e: Exception) -> str:
    if isinstance(e, httpx.HTTPStatusError):
        ...
        return f"Fehler: HTTP {code} – {e.response.text[:200]}"
    ...
    return f"Fehler: {type(e).__name__} – {str(e)[:200]}"
```

## Risiko

- Blind im Betrieb: keine Anomalie-Erkennung möglich, kein Missbrauchs-Forensik-Trail.
- Keine Korrelation zwischen Tool-Aufruf, Upstream-Fehler und Client.
- 5xx-Spikes von geo.admin.ch unsichtbar.

## Empfehlung

1. `logging` mit JSON-Formatter und `LOG_LEVEL`-Env-Var einführen.
2. In jedem Tool-Handler einen Logger-Call mit Tool-Name, ausgewählten Parametern (nicht den vollen Query — Datensparsamkeit), Latenz und Outcome.
3. `_handle_error` soll Exception inkl. URL/Status loggen (WARNING/ERROR), bevor sie geschluckt wird.
4. Bei HTTP-Deployment: Access-Log via Uvicorn / Mittelschicht aktivieren.

## Minimal-Beispiel

```python
import logging, time
logger = logging.getLogger("swiss_culture_mcp")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"),
                    format='{"ts":"%(asctime)s","lvl":"%(levelname)s","msg":%(message)s}')
```
