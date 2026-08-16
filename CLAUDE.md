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

Vor dem Lauf `ruff --version` prüfen: ein älteres ruff früher im `PATH`
schlägt den Pin, ohne dass der Install etwas meldet.

**Gates, wörtlich aus `ci.yml`** (Matrix: Python 3.11 / 3.12 / 3.13):

```bash
ruff check src/ tests/ scripts/
ruff format --check src/ tests/ scripts/
python -m py_compile src/swiss_culture_mcp/server.py
python -c "from swiss_culture_mcp.server import mcp; print('Import OK')"
PYTHONPATH=src pytest tests/ -m "not live"   # nur Python 3.11
python scripts/check_version_sync.py
```

**Live-Tests.** `.github/workflows/live-tests.yml` läuft geplant
(`cron: "53 4 * * 1"`, wöchentlich Mo) plus `workflow_dispatch`, gegen
`api3.geo.admin.ch`, `opendata.swiss` und den BAK-News-Feed; die
Einordnung macht `scripts/classify_live_run.py`
(`clear` / `finding` / `unknown`), ein Fund öffnet bzw. schliesst ein
`upstream`-Issue. `schedule` greift nur auf dem Default-Branch: Änderungen
an der Datei wirken erst nach dem Merge, vorher von Hand auslösen.
Der pytest-Aufruf braucht **`--run-live`**; ohne die Option überspringt
sich jeder Live-Test selbst und der Lauf endet mit 4 übersprungen /
Exit 0. Der Flag fehlte, `test_live_workflow.py` hält ihn jetzt fest.
Ein Live-Test läuft nie allein: Der modulweite HTTP-Client überlebt sonst
den Event-Loop des vorherigen Tests (`RuntimeError: Event loop is closed`,
sichtbar als `JSONDecodeError`). Die autouse-Fixture in `conftest.py` setzt
ihn je Live-Test zurück — ohne sie meldet der Job einen gebrochenen Vertrag,
wo nur zwei Tests hintereinander liefen.

**Die Allowlist prüft das Ziel, die Fixture muss es aufschreiben.**
`_assert_host_allowed()` prüft den Host NACH der Umleitung. `opendata.swiss`
beantwortet die CKAN-Aufrufe mit 302 auf `ckan.opendata.swiss` — der Host
fehlte in `ALLOWED_HOSTS`, also scheiterte jeder `bak_get_opendata`-Aufruf
produktiv, während alle Unit-Tests grün blieben. `adressen.json` notierte
brav 200: Der Recorder folgte der Umleitung und schrieb den Ausgangs-Host
auf. Er schreibt jetzt `final_host` mit, `test_umleitungsziele.py` prüft für
jede abgerufene Adresse Start- und Zielhost gegen die Allowlist. Nur die
abgerufenen — `gisos` und `bak_wurzel` gibt der Server als Link aus, ohne sie
zu holen; deren Ziel `www.bak.admin.ch` gehört nicht in die Liste.

Fixtures liegen unter `tests/fixtures/`, erzeugt von
`scripts/record_fixtures.py`, Aufnahmedatum in `PROVENANCE.md` — nicht von
Hand pflegen. Der Recorder bricht bei einem vorübergehenden 502 der Quelle
ab; die Ausgabe endet dann an einer Stelle, die wegen der Pipe-Pufferung
nicht die fehlerhafte Sonde ist. Einfach nochmal laufen lassen.
Alles Weitere: `README.md`, `CONTRIBUTING.md`.
