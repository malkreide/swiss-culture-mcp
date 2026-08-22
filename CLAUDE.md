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

Seit `.claude/settings.json` läuft diese Prüfung als SessionStart-Hook
(`.claude/hooks/session-start.sh`) und meldet den Rückstand von selbst. Sie
blockiert nie und schweigt bei 0 — bleibt oben also von Hand zu fahren, wenn
der Hook nicht greift (fremder Klon, kein Netz beim Start). Begründung und
Zusicherungen: `.claude/hooks/README.md`.

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

## Wenn Codex gar nicht erst hinsieht

Die Zeile oben unterstellt, dass es einen Befund geben *kann*. Das ist nicht
immer so, und man sieht es dem PR nicht an.

Am 21.8.2026 war das Code-Review-Kontingent zwischen 08:41 und 09:48
aufgebraucht — davor echte Reviews, danach in 30 Repos nur noch:

```
You have reached your Codex usage limits for code reviews.
```

Bis mindestens zum 22.8. um 08:30, also 23 Stunden später, blieb es dabei. In
der Zwischenzeit sind 32 PRs mit formal erfülltem Häkchen gemergt worden, ohne
dass jemand hineingesehen hat.

Drei Gründe, warum Codex schweigt, und nur einer davon ist harmlos:

- **Kein Befund** — dann reagiert er mit 👍 und schreibt nichts.
- **Der PR ist ein Draft** — darauf läuft Codex nicht an.
- **Das Kontingent ist weg** — dann schreibt er die Meldung oben.

«Kein Kommentar» heisst also nicht «geprüft und sauber». Unterscheiden lässt es
sich an der Form: Ein echter Review ist ein Review-Objekt («💡 Codex Review»,
mit Commit-Angabe), die Limit-Meldung ein gewöhnlicher Issue-Kommentar. Das
sind zwei verschiedene Abfragen — `get_reviews` gegen `get_comments`; wer nur
eine davon nimmt, übersieht die andere Hälfte. Genau so ist die Limit-Meldung
zuerst durchgerutscht.

Portfolio-weit nachsehen:

```
search_pull_requests: user:malkreide commenter:chatgpt-codex-connector[bot] updated:>=<Datum>
```

Findet nur, wo er *kommentiert* hat. Repos ohne PR-Aktivität tauchen nicht auf
— das ist kein Beleg, dass dort geprüft wurde.

Zweiter Weg, den Prüfer zu verlieren, ganz ohne Kontingentproblem: zu schnell
mergen. Am 21./22.8. lagen zwischen «ready for review» und Merge mehrfach drei
bis fünf Sekunden. Codex wird beim Umschalten von Draft auf ready ausgelöst und
braucht danach Zeit; wer sofort mergt, hat das Häkchen gesetzt und den Review
nicht abgewartet.

Das Kontingent hängt am Konto, nicht am Repo, und Code-Reviews haben einen
eigenen Topf — nur GitHub-getriggerte Reviews zählen hinein. ChatGPT-Pläne
fahren ein rollendes Fünf-Stunden-Fenster plus Wochenlimits; welches greift,
steht im Codex-Dashboard. Zeigt das freies Kontingent, während Reviews weiter
scheitern, ist das ein bekannter Fehler bei mehreren verbundenen Konten — dann
den GitHub-Connector in den Codex-Einstellungen trennen und neu verbinden.

---

## Wenn zwei Agenten dasselbe tun

Vor dem Anlegen eines Branches mit vorgegebenem Namen prüfen, ob es ihn schon
gibt:

```bash
git ls-remote --heads origin claude/<name> | wc -l
```

Steht dort `1`, arbeitet jemand anderes daran — mit Schreibrecht auf denselben
Ref.

Ein PR mit leerem Diff wird geschlossen, nicht gemergt. Der Test ist
`get_files` auf dem PR: kommt `[]` zurück, ändert er nichts. Ein grüner Check
sagt dazu nichts — die CI prüft den Head, nicht die Differenz zur Basis.

Am 21.8.2026 liefen zwei Sessions dieselbe Aufgabe über 45 Repos, auf den
Branches `claude/codex-review-audit-templates-9sn6mx` und
`claude/codex-review-audit-7ioh56`. Wo die eine zuerst nach `main` kam, wurde
`main` in den Branch der anderen gemergt und der add/add-Konflikt zugunsten
von `main` aufgelöst. Übrig blieben 14 PRs, die durch sämtliche Gates grün
liefen und nichts enthielten; sie wurden gemergt und hinterliessen leere
Merge-Commits. Mit den zwei Folge-PRs, die aus demselben Grund gegenstandslos
waren, waren 16 der 59 PRs jenes Tages reine Reibung.

Dieselbe Klasse wie der handgeschriebene Stub, der denselben Feldnamen annahm
wie der Code: Nichts ist rot, weil nichts geprüft wird, worauf es ankommt.

## Dieses Repo

**ruff: genau eine Quelle** — `ruff==0.16.3` im dev-Extra von
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
python scripts/check_ruff_pin.py
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
Die Sollwerte der ISOS-Zahlen stehen nicht in der API, sondern im Anhang 1
der VISOS (SR 451.12, Fassung 1.6.2026): 1253 Ortsbilder, ZH 73, GR 105,
alle 26 Kantone deckungsgleich mit `api3.geo.admin.ch`. Fällt der Test, erst
die Verordnung nachzählen. Gezählt wird nach ISOS-`nummer`, nie nach
Feature-`id`: Die Quelle liefert je Objekt mehrere Features, in GR bis zu 51.
Ein Live-Test läuft nie allein: Der modulweite HTTP-Client überlebt sonst
den Event-Loop des vorherigen Tests (`RuntimeError: Event loop is closed`,
sichtbar als `JSONDecodeError`). Die autouse-Fixture in `conftest.py` setzt
ihn je Live-Test zurück — ohne sie meldet der Job einen gebrochenen Vertrag,
wo nur zwei Tests hintereinander liefen.

**Wer den Cron überwacht, braucht selbst Werkzeug.** Am 17.8.2026 feuerte
`schedule` zum ersten fälligen Termin nicht; beide bisherigen Live-Läufe
liefen von Hand. Ein Check-in dafür als Routine (`create_trigger`) hilft nur
mit Vorsicht: Die gefeuerte Session erbt **keine** MCP-Tools — die Warnung
steht im Rückgabewert des Aufrufs. GitHub ist hier kein claude.ai-Connector
(`ListConnectors` liefert leer), sondern hängt an der Session und dem Repo,
das ihr angehängt ist; `curl` und `WebFetch` auf `api.github.com` enden bei
«GitHub access is not enabled for this session» bzw. 403. Eine solche
Routine muss den Fall «keine Tools» darum ausdrücklich behandeln und dem
Menschen die URL nennen, statt etwas zu melden, das sie nicht geprüft hat.

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
