# CLAUDE.md

## Vor der Arbeit

Klon-Aktualität prüfen: git fetch origin main && git rev-list --count HEAD..origin/main
Ein veralteter Klon erzeugt eine rote CI, deren Ursache nicht im Diff steht.
Am 3.8.2026 zweimal passiert — beide Male fehlten genau die Commits, die
das Gate einführten, an dem der Branch scheiterte.
Gates lokal fahren, mit der GEPINNTEN ruff-Version aus der CI. Eine andere
Version meldet Abweichungen, die niemand verursacht hat.

## Tests

Gegenprobe ist Pflicht. Ein Test, der grün bleibt, wenn man die
Implementierung entfernt, prüft nichts. Jede neue Zusicherung einzeln
neutralisieren und zeigen, dass genau die zugehörigen Tests fallen.
Zwei Fallen, die beide grün blieben:
- Eine Fake-Uhr, die nur beim Schlafen vorrückt, kann eine Zusicherung über
echte Zeit nicht widerlegen.
- monkeypatch.setattr(modul.asyncio, "sleep", ...) greift ins Modul
asyncio selbst und entschärft die Mechanik im ganzen Prozess. Patche
einen Modul-Alias (_sleep = asyncio.sleep), nicht das fremde Modul.
Handgeschriebene Fixtures kodieren die Annahme des Autors und können sie
nicht widerlegen. Mindestens eine aufgezeichnete Antwort pro externem
Endpunkt, mit Aufnahmedatum.

## Wenn etwas rot ist

Roter Live-Test: erst die Quelle abfragen, dann einordnen. Nicht aus der
Fehlermeldung schliessen. Am 3.8.2026 hiess "nicht gefunden" nicht, dass der
Datensatz weg war, sondern dass die Quelle die Schreibweise ihrer Kopfzeile
gewechselt hatte — vier von sechs Datensätzen produktiv kaputt, alle
Unit-Tests grün.
PR ohne jeden Check ist selten ein Repo ohne CI, meistens ein
Merge-Konflikt: GitHub berechnet dafür keinen Merge-Commit und startet nichts.
Ein Codex-Review auf einem PR wird beantwortet oder behoben, nie ignoriert.

---

## Dieses Repo

**ruff ist `0.16.1` — an drei Stellen.** Das dev-Extra in `pyproject.toml`
und die beiden `pip install ruff==` in `.github/workflows/ci.yml` (`:33`,
`:64`) müssen dieselbe Version nennen. `uv pip install -e ".[dev]"` liefert
damit die CI-Version. Eine `.pre-commit-config.yaml` gibt es nicht, und kein
Skript prüft den Gleichstand — beim Bump alle drei Stellen zusammen anfassen,
sonst lintet lokal eine andere Version als das Gate.

**Gates, wörtlich aus `ci.yml`** (Matrix: Python 3.11 / 3.12 / 3.13):

```bash
ruff check src/ tests/ scripts/
ruff format --check src/ tests/ scripts/
python -m py_compile src/swiss_culture_mcp/server.py
python -c "from swiss_culture_mcp.server import mcp; print('Import OK')"
PYTHONPATH=src pytest tests/ -m "not live"   # nur Python 3.11
python scripts/check_version_sync.py
```

**Live-Tests — DRIFT-005 erfüllt.** `.github/workflows/live-tests.yml`
läuft geplant (`cron: "53 4 * * 1"`, wöchentlich Mo) plus
`workflow_dispatch`, gegen `api3.geo.admin.ch`; die Einordnung macht
`scripts/classify_live_run.py` (`clear` / `finding` / `unknown`), ein Fund
öffnet bzw. schliesst ein `upstream`-Issue. Die PR-CI schliesst die Suite
per `-m "not live"` aus — das ist hier korrekt, weil der geplante Lauf
existiert. `schedule` greift nur auf dem Default-Branch: Änderungen an der
Datei wirken erst nach dem Merge, vorher von Hand auslösen.

Fixtures liegen unter `tests/fixtures/`, erzeugt von
`scripts/record_fixtures.py`, Aufnahmedatum in `PROVENANCE.md` — nicht von
Hand pflegen. Alles Weitere: `README.md`, `CONTRIBUTING.md`.
