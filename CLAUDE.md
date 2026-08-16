# CLAUDE.md

## Vor der Arbeit

Klon-Aktualität prüfen — Standard-Branch ermitteln, nicht `main` annehmen:

```bash
B=$(git ls-remote --symref origin HEAD | sed -n 's|^ref: refs/heads/\([^[:space:]]*\).*|\1|p')
git fetch origin "${B:?Standard-Branch nicht ermittelbar}" &&
  git rev-list --count HEAD..FETCH_HEAD
```

Drei Server im Portfolio heissen ihren Standard-Branch `master`
(`openlex-mcp`, `swiss-courts-mcp`, `swisstopo-mcp`); dort scheitert ein fest
verdrahtetes `origin/main` mit «couldn't find remote ref main». Wer das für ein
Netzproblem hält, arbeitet weiter auf genau dem veralteten Klon, vor dem dieser
Absatz warnt. Den `:?`-Schutz nicht weglassen: Bei leerem `B` fetcht git still
den Remote-HEAD und endet mit 0.

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

**ruff: genau eine Quelle** — `ruff==0.16.1` im dev-Extra von
`pyproject.toml`. Der dev-Install liefert damit die CI-Version, lokal wie
dort. Keine zweite Version in die Workflows schreiben: ein solcher Schritt
läuft nach dem Install und überstimmt den Pin still. `ci.yml` hatte zwei
solche Schritte (Jobs `test` und `lint`); `test_werkzeug_versionen.py` hält
beides fest. Eine `.pre-commit-config.yaml` gibt es nicht.

**Der `lint`-Job muss das Projekt installieren.** Er hatte als einzige
ruff-Quelle den eigenen Pin-Schritt — den ersatzlos zu streichen nahm ihm
das Werkzeug (`ruff: command not found`). Er trägt deshalb ein
`pip install -e ".[dev]"`, anders als der `test`-Job, der ohnehin installiert.

**Gates, wörtlich aus `ci.yml`** (Matrix: Python 3.11 / 3.12 / 3.13):

```bash
ruff check src/ tests/ scripts/
ruff format --check src/ tests/ scripts/
python -m py_compile src/swiss_culture_mcp/server.py
python -c "from swiss_culture_mcp.server import mcp; print('Import OK')"
PYTHONPATH=src pytest tests/ -m "not live"   # nur Python 3.11
python scripts/check_version_sync.py
```

**Live-Tests — geplant, aber leer laufend (offener Befund).**
`.github/workflows/live-tests.yml` läuft geplant (`cron: "53 4 * * 1"`,
wöchentlich Mo) plus `workflow_dispatch`, gegen `api3.geo.admin.ch`
(die Suite fasst zusätzlich `opendata.swiss` und den BAK-News-Feed an);
die Einordnung macht `scripts/classify_live_run.py`
(`clear` / `finding` / `unknown`), ein Fund öffnet bzw. schliesst ein
`upstream`-Issue. `schedule` greift nur auf dem Default-Branch: Änderungen
an der Datei wirken erst nach dem Merge, vorher von Hand auslösen.
Der Lauf ruft aber `pytest tests/ -m live` **ohne `--run-live`** auf, und
ohne diese Option überspringt sich jeder Live-Test selbst: 4 gesammelt,
4 übersprungen, Exit 0 — `classify_live_run.py` sagt dazu korrekt
`unknown`. Der Job wird also wöchentlich rot, ohne die Quelle je abgefragt
zu haben; DRIFT-005 ist bis dahin nicht erfüllt. Fix ist `--run-live` am
pytest-Aufruf. Bis das steht, trägt der `-m "not live"`-Ausschluss der
PR-CI nichts: es prüft niemand.

Fixtures liegen unter `tests/fixtures/`, erzeugt von
`scripts/record_fixtures.py`, Aufnahmedatum in `PROVENANCE.md` — nicht von
Hand pflegen. Alles Weitere: `README.md`, `CONTRIBUTING.md`.
