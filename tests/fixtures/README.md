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

Alle Einträge stammen aus **diesem** Repo, aufgezeichnet am 2026-09-19:

| Eintrag | Zustand | Head |
|---|---|---|
| PR #56 | `✅ Completed` | `b503b48` |
| PR #61 | `✅ Completed` | `9a035de` |
| PR #62, Draft-Stand | Environment-Meldung | — |
| PR #62, laufend | `🔄 Running` | `f09a9e0` |
| PR #62, fertig | `✅ Completed` | `f09a9e0` |

Die letzten beiden sind **derselbe Kommentar** (ID 5740705055), 56 Sekunden
auseinander gelesen: `created_at` beide Male 09:15:14, `updated_at` von
09:15:14 auf 09:16:11 gewandert. Codex schreibt die Tabelle in Ort fort.

Hier stand eine Fassung lang, der laufende Zustand sei gar nicht
aufzuzeichnen, und für `🔄 Running` eine fremde Aufnahme aus
`swiss-cultural-heritage-mcp`. Das war zu stark: Aufzuzeichnen ist er sehr
wohl — nur eben **während** des Laufs. Die fremde Aufnahme ist ersetzt.

Der Draft-Eintrag ist selbst ein Befund. Er kam 30 Sekunden nach dem Anlegen
des Drafts, neun Minuten bevor derselbe PR auf ready einen regulären Review
bekam. Die Environment-Meldung auf einem Draft sagt also nichts über das
Repo; Begründung in `CLAUDE.md`.

Aufnahmedatum und Herkunft jedes Eintrags stehen unter `_herkunft` und
`_quelle` in der JSON — ohne Datum ist «gemessen» nach zwei Jahren von
«angenommen» nicht mehr zu unterscheiden.
