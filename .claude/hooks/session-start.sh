#!/usr/bin/env bash
# SessionStart-Hook: meldet, wie viele Commits der ausgecheckte Stand hinter
# origin/<Default-Branch> liegt. Begruendung: .claude/hooks/README.md
#
# Oberste Regel, wichtiger als jede Meldung: Dieser Hook blockiert die Session
# nie. Kein Netz, kein Remote, detached HEAD, flatterndes DNS, fehlende
# Anmeldedaten — jeder dieser Faelle endet still mit Exit 0 und ohne Ausgabe.
# Ein Hook, der bei Netzproblemen die Arbeit anhaelt, wird nach dem zweiten Mal
# abgeschaltet und schuetzt danach gar nichts mehr.

# Kein `set -e`: Ein fehlschlagender Befehl ist hier der Normalfall (offline),
# kein Abbruchgrund. Das `trap` faengt ab, was trotzdem durchrutscht — etwa
# eine ungesetzte Variable unter `set -u`.
set -uo pipefail
trap 'exit 0' EXIT

# Sekunden, die das Netz insgesamt kosten darf.
FETCH_TIMEOUT=${CLAUDE_STALE_CHECK_TIMEOUT:-8}

# Ein wartender Anmeldedialog haengt den Sessionstart, ohne dass ein Timeout
# auf `git` ueberhaupt greift: Der Prozess laeuft ja, er wartet nur auf eine
# Eingabe, die niemand gibt. Deshalb alle Dialoge vorab abschalten.
export GIT_TERMINAL_PROMPT=0
export GIT_ASKPASS=/bin/true
export SSH_ASKPASS=/bin/true
export GIT_SSH_COMMAND="${GIT_SSH_COMMAND:-ssh -o BatchMode=yes -o ConnectTimeout=5}"
# Zweite Reissleine fuer den Fall, dass `timeout(1)` fehlt: git bricht eine
# HTTP-Uebertragung ab, die so lange fast nichts mehr liefert.
export GIT_HTTP_LOW_SPEED_LIMIT=1000
export GIT_HTTP_LOW_SPEED_TIME="$FETCH_TIMEOUT"

mit_timeout() {
	if command -v timeout >/dev/null 2>&1; then
		timeout "$FETCH_TIMEOUT" "$@"
	else
		"$@"
	fi
}

# Den Default-Branch ermitteln, nicht `main` annehmen: Drei Server im
# Portfolio (openlex-mcp, swiss-courts-mcp, swisstopo-mcp) heissen ihren
# `master`. Genau diese Annahme hat schon einmal einen Branch 15 Commits alt
# werden lassen, weil `origin/main` mit «couldn't find remote ref main»
# scheiterte und das wie ein Netzproblem aussah.
default_branch() {
	local zweig
	# Zuerst lokal, ohne Netz: `git clone` setzt diese Referenz.
	zweig=$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null)
	zweig=${zweig#origin/}
	if [ -n "$zweig" ]; then
		printf '%s\n' "$zweig"
		return 0
	fi
	# Sonst den Remote fragen. Schlaegt das fehl, wird nichts geraten.
	mit_timeout git ls-remote --symref origin HEAD 2>/dev/null |
		sed -n 's|^ref: refs/heads/\([^[:space:]]*\).*|\1|p' |
		head -n 1
}

cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0

git rev-parse --git-dir >/dev/null 2>&1 || exit 0        # kein Git-Repo
git rev-parse --verify --quiet HEAD >/dev/null 2>&1 || exit 0  # noch kein Commit
git remote get-url origin >/dev/null 2>&1 || exit 0      # kein Remote `origin`

ZWEIG=$(default_branch)
[ -n "${ZWEIG:-}" ] || exit 0

# Nur dieser eine Branch, kein `--tags`, kein `--all`: Der Hook soll billig
# sein. Der Aufruf aktualisiert FETCH_HEAD und die Remote-Tracking-Referenz,
# er veraendert den Arbeitsbaum nicht.
mit_timeout git fetch --quiet origin "$ZWEIG" >/dev/null 2>&1 || exit 0

ZIEL=$(git rev-parse --verify --quiet FETCH_HEAD 2>/dev/null)
[ -n "${ZIEL:-}" ] || exit 0

# Funktioniert auch bei detached HEAD — dort ist HEAD eine gueltige Revision
# wie jede andere.
HINTER=$(git rev-list --count "HEAD..$ZIEL" 2>/dev/null)
case "${HINTER:-}" in
'' | *[!0-9]*) exit 0 ;;
esac

# Bei 0 schweigt der Hook. Eine Meldung «alles aktuell» bei jedem Sessionstart
# waere genau das Rauschen, das man nach der dritten Woche nicht mehr liest.
[ "$HINTER" -gt 0 ] || exit 0

if [ "$HINTER" -eq 1 ]; then
	WORT="Commit"
else
	WORT="Commits"
fi

cat <<MELDUNG
[Klon-Aktualitaet] Der ausgecheckte Stand liegt $HINTER $WORT hinter origin/$ZWEIG.

Ein veralteter Klon erzeugt eine rote CI, deren Ursache nicht im Diff steht:
Die fehlenden Commits sind erfahrungsgemaess genau die, die das Gate
einfuehren, an dem der Branch dann scheitert. Vor dem Arbeiten aktualisieren:

    git fetch origin $ZWEIG && git merge FETCH_HEAD
MELDUNG

exit 0
