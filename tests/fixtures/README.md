# Fixtures

Alle Dateien hier sind **aufgezeichnete Antworten der Quellen**, nicht von Hand
geschrieben. Herkunft, Datum und Prüfsumme stehen in `PROVENANCE.md` (erzeugt von
`scripts/record_fixtures.py`) und `PROVENANCE_VISOS.md` (erzeugt von
`scripts/record_visos.py`). Nicht von Hand pflegen.

## Lebendige Traditionen (SEC-019)

| Fixture | Leser | Inhalt |
|---|---|---|
| `traditionen_liste.json.gz` | `traditionen.parse_liste` | Antwort von `/api/collector/de/alle-traditionen.json` |
| `tradition_basler-fasnacht.json.gz` | `traditionen.parse_detail` | Tradition mit Kanton und UNESCO-Eintrag |
| `tradition_alphorn-und-buechelspiel.json.gz` | `traditionen.parse_detail` | überregional, Platzhalter-Link statt Kanton |
| `tradition_gebaerdensprachen.json.gz` | `traditionen.parse_detail` | «Kanton» als h4, «CH» für die ganze Schweiz |

Bis zum 7.11.2026 lagen hier zwei von Hand geschriebene HTML-Schnipsel
(`tradition_alphorn.html`, `tradition_list.html`). Sie hielten alle Tests grün,
während lebendige-traditionen.ch umgebaut war und beide Werkzeuge produktiv
scheiterten — sie kodierten genau die Annahme, die gebrochen war.

Ändert die Quelle ihre Form: neu aufzeichnen, `tests/test_traditionen.py`
gegen die neue Antwort laufen lassen, und was fällt, an der Quelle prüfen.

## VISOS-Aufnahmen (Sollwerte des ISOS-Live-Tests)

| Fixture | Leser | Inhalt |
|---|---|---|
| `visos_fassungen.json` | `visos_anhang.parse_fassungen` | Alle Fassungen der VISOS (SR 451.12) aus der SPARQL-Schnittstelle von Fedlex |
| `visos_anhang1_<JJJJMMTT>.html.gz` | `visos_anhang.parse_anhang1` | Deutsche HTML-Ausgabe der gueltigen Fassung, unveraendert, gzip |

Nach einer neuen Aufnahme gehoeren die Zahlen in `tests/test_visos_anhang.py`
mit einer unabhaengigen Auszaehlung nachgefuehrt.
