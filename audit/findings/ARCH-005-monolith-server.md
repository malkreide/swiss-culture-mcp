# ARCH-005 — Monolithisches `server.py` (1259 Zeilen)

- **Severity:** LOW
- **Kategorie:** ARCH
- **Status:** open

## Befund

Sämtliche 10 Tools, 3 Resources, Pydantic-Modelle, Hilfsfunktionen und Konstanten leben in einer einzigen Datei. Bei künftiger Erweiterung (Synergien mit anderen MCP-Servern, neue BAK-Quellen) wird die Datei unhandlich.

## Evidenz

```bash
$ wc -l src/swiss_culture_mcp/server.py
1259 src/swiss_culture_mcp/server.py
```

## Empfehlung

Splitting nach Datenquelle, z. B.:

```
src/swiss_culture_mcp/
├── __init__.py
├── server.py             # FastMCP-Instanz + main()
├── http_client.py        # _get, _get_text, _handle_error
├── isos/
│   ├── models.py
│   └── tools.py          # 5 ISOS-Tools
├── news.py               # bak_get_news, bak_get_kulturpreise
├── opendata.py
└── traditions.py
```

Kein Funktionsverlust, klare Owner pro Datenquelle, einfachere Tests.
