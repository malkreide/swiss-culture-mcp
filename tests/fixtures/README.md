# HTML-Fixtures für Regression-Tests (SEC-019)

Diese Dateien sind eingefrorene Schnappschüsse der relevanten Seitenstruktur
von **lebendige-traditionen.ch**. Sie dienen als Regression-Schutz für die
Regex-basierten HTML-Parser in `swiss_culture_mcp.server`:

| Fixture | Parser | Erwartete Felder |
|---|---|---|
| `tradition_alphorn.html` | `bak_get_tradition_detail` | `<title>`, `<meta name="description">`, `<p>`-Text, Kantons-Erwähnungen |
| `tradition_list.html` | `bak_list_traditions` | `<a href="/tradition/.../<slug>.html">` |

## Wartung

Wenn lebendige-traditionen.ch seine DOM-Struktur ändert:

1. Aktuellen Stand fetchen, neue Fixture(s) anlegen.
2. `tests/test_server.py::TestHtmlFixtures` updaten.
3. Bei strukturellen Brüchen: Parser-Regex in `server.py` anpassen oder auf
   `selectolax`/`beautifulsoup4` migrieren.
