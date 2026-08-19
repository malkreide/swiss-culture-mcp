# SessionStart-Hook: Klon-Aktualität

`session-start.sh` meldet beim Sessionstart, wie viele Commits der
ausgecheckte Stand hinter `origin/<Default-Branch>` liegt. Registriert ist er
in `.claude/settings.json` für die Quellen `startup` und `resume` — nicht für
`compact`, das während einer Session mehrfach feuert und dabei nichts Neues
prüfen würde.

## Warum es ihn gibt

Ein veralteter Klon hat am 3.8.2026 zweimal eine rote CI erzeugt, deren
Ursache nicht im Diff stand. Die fehlenden Commits waren jeweils genau die,
die das Gate einführten, an dem der Branch scheiterte — der Fehler zeigte auf
Dateien, die niemand angefasst hatte. Die Prüfung kostet eine Sekunde und
ersetzt eine Fehlersuche in den falschen Dateien.

Die Prüfung stand bis dahin nur als Merksatz in `CLAUDE.md`, ganz oben unter
«Vor der Arbeit». Ein Merksatz wirkt genau so lange, wie ihn jemand liest.

## Was er zusichert

1. **Er blockiert die Session nie.** Kein Netz, kein Remote `origin`, kein
   Git-Repo, detached HEAD, ein Repo ohne Commits, flatterndes DNS, fehlende
   Anmeldedaten — jeder dieser Fälle endet still mit Exit 0 und ohne Ausgabe.
   Das ist die oberste Regel, wichtiger als jede Meldung: Ein Hook, der bei
   Netzproblemen die Arbeit anhält, wird nach dem zweiten Mal abgeschaltet und
   schützt danach gar nichts mehr.
2. **Kurzes Timeout aufs Netz.** `timeout(1)` deckelt jeden Git-Aufruf auf
   8 Sekunden (`CLAUDE_STALE_CHECK_TIMEOUT` übersteuert das). Fehlt `timeout`
   auf dem System, greifen `GIT_HTTP_LOW_SPEED_LIMIT`/`_TIME` als zweite
   Reissleine. Zusätzlich sind alle Anmeldedialoge abgeschaltet
   (`GIT_TERMINAL_PROMPT=0`, `GIT_ASKPASS`, `ssh -o BatchMode=yes`): Ein
   wartender Passwort-Prompt hängt den Sessionstart, ohne dass ein Timeout auf
   `git` überhaupt greifen würde — der Prozess läuft ja, er wartet nur.
   Zusätzlich deckelt `settings.json` den Hook selbst auf 15 Sekunden.
3. **Ausgabe nur, wenn Commits fehlen.** Bei 0 schweigt er. Eine Meldung
   «alles aktuell» bei jedem Sessionstart wäre genau das Rauschen, das man
   nach der dritten Woche nicht mehr liest.
4. **Der Default-Branch wird ermittelt, nicht angenommen.** Zuerst lokal über
   `refs/remotes/origin/HEAD` (kein Netz), sonst über `git ls-remote --symref`.
   Liefert beides nichts, wird nichts geraten und der Hook schweigt. Drei
   Server im Portfolio (`openlex-mcp`, `swiss-courts-mcp`, `swisstopo-mcp`)
   heissen ihren Default-Branch `master`; ein fest verdrahtetes `origin/main`
   scheitert dort mit «couldn't find remote ref main». Wer das für ein
   Netzproblem hält, arbeitet weiter auf genau dem veralteten Klon — so wurde
   ein Branch einmal 15 Commits alt.

`tests/test_session_start_hook.py` hält diese vier Punkte fest und führt das
Skript dafür gegen echte Wegwerf-Repositorien aus.

## Selbst ausprobieren

```bash
CLAUDE_PROJECT_DIR="$PWD" .claude/hooks/session-start.sh; echo "Exit: $?"
```

Auf einem aktuellen Klon: keine Ausgabe, Exit 0.
