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

## `codex_kommentare.json` — nicht vom Recorder

Die übrigen Dateien hier erzeugt `scripts/record_fixtures.py`; `PROVENANCE.md`
schreibt es mit und darf deshalb nicht von Hand gepflegt werden. Diese eine
Datei fällt heraus: Sie hält echte Antwortkörper der **GitHub-API**
(`issues/{n}/comments`), gegen die `scripts/classify_codex_review.py` geprüft
wird — der Recorder kennt nur die Datenquellen des Servers.

| Eintrag | Herkunft | Zustand |
|---|---|---|
| PR #56 | dieses Repo, 2026-09-19 | `✅ Completed`, Head `b503b48` |
| PR #61 | dieses Repo, 2026-09-19 | `✅ Completed`, Head `9a035de` |
| PR #90 | `swiss-cultural-heritage-mcp`, 2026-09-19 | `🔄 Running`, Head `bfe7ab7` |

Der laufende Zustand liess sich hier nicht aufzeichnen: Codex schreibt die
Tabelle **in Ort** fort — gleiche Kommentar-ID, `created_at` unverändert,
`updated_at` wandert. Nach dem Lauf ist `Running` nicht mehr abrufbar. Die
dritte Zeile stammt deshalb aus einem anderen Repo und ist hier nicht
nachgemessen; das steht auch in der Datei selbst.

Aufnahmedatum und Herkunft jedes Eintrags stehen unter `_herkunft` und
`_quelle` in der JSON — ohne Datum ist «gemessen» nach zwei Jahren von
«angenommen» nicht mehr zu unterscheiden.
