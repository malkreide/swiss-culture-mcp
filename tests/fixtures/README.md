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

## VISOS-Aufnahmen (Sollwerte des ISOS-Live-Tests)

| Fixture | Leser | Inhalt |
|---|---|---|
| `visos_fassungen.json` | `visos_anhang.parse_fassungen` | Alle Fassungen der VISOS (SR 451.12) aus der SPARQL-Schnittstelle von Fedlex |
| `visos_anhang1_<JJJJMMTT>.html.gz` | `visos_anhang.parse_anhang1` | Deutsche HTML-Ausgabe der gueltigen Fassung, unveraendert, gzip |

Erzeugt von `scripts/record_visos.py`, Herkunft in `PROVENANCE_VISOS.md` —
nicht von Hand pflegen. Nach einer neuen Aufnahme gehoeren die Zahlen in
`tests/test_visos_anhang.py` mit einer unabhaengigen Auszaehlung nachgefuehrt.
