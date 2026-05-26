# SEC-003 — Streamable HTTP bindet 0.0.0.0 ohne Auth

- **Severity:** HIGH
- **Kategorie:** SEC
- **Status:** open
- **Applicability:** Nur HTTP-Deployment (Render.com / Docker). stdio-Deployment unbetroffen.

## Befund

Im HTTP-Modus startet der Server unbedingt auf `0.0.0.0`, ohne Auth-Schicht, ohne IP-Allowlist, ohne Token-Validierung. Wer den Endpoint erreicht, kann alle 10 Tools aufrufen.

## Evidenz

`src/swiss_culture_mcp/server.py:1247-1255`

```python
def main() -> None:
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    port = int(os.getenv("MCP_PORT", "8000"))

    if transport == "streamable_http":
        mcp.run(transport="streamable_http", host="0.0.0.0", port=port)
    else:
        mcp.run(transport="stdio")
```

README (Zeile 142–153) bewirbt Render.com-Deployment, ohne einen Auth-Reverse-Proxy oder Cloudflare-Access-Layer vor das Service zu setzen.

## Risiko

- Abuse-Vektor: Open Proxy für geo.admin.ch / opendata.swiss / news.admin.ch — könnte Rate-Limits verbrennen, IP-Reputation des Bundes-Account verschlechtern.
- DoS-Verstärker: Per-Request neuer `AsyncClient` (siehe SCALE-001) + sequenzielle 7-Kanton-Calls in `bak_isos_statistics` ⇒ einfache Amplifikation.
- Reputationsrisiko: Server agiert offiziell unter Bundesdaten-Logo, ohne Zugriffskontrolle.

Offene Daten mildern Schaden, eliminieren ihn nicht.

## Empfehlung

1. Default-Bind auf `127.0.0.1` ändern; öffentliches Binding nur via expliziter Env-Var `MCP_HOST` mit Default `127.0.0.1`.
2. Auth-Mode erzwingen: Token-Header oder OAuth-2.1 (FastMCP unterstützt `auth=`) für `streamable_http`-Pfad.
3. README mit Hinweis ergänzen: Cloud-Deployment ZWINGEND hinter Auth-Gateway (z. B. Cloudflare Access, oauth2-proxy).
4. Optional: Per-IP-Rate-Limit-Middleware.

## Vorgeschlagener Fix (Minimum)

```python
host = os.getenv("MCP_HOST", "127.0.0.1")
require_auth = os.getenv("MCP_REQUIRE_AUTH", "true").lower() == "true"
if transport == "streamable_http" and host == "0.0.0.0" and not require_auth:
    raise SystemExit("Refusing to bind 0.0.0.0 without auth. Set MCP_REQUIRE_AUTH=false to override.")
```
