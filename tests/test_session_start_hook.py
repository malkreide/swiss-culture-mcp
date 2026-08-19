"""Der SessionStart-Hook haelt vier Zusicherungen — hier laufen sie wirklich.

Die Pruefung stand bis dahin nur als Merksatz in `CLAUDE.md`. Ein Merksatz
wirkt so lange, wie ihn jemand liest; am 3.8.2026 erzeugte ein veralteter Klon
zweimal eine rote CI, deren Ursache nicht im Diff stand.

Getestet wird das Skript selbst, gegen echte Wegwerf-Repositorien: ein
Bare-Repo als «Remote», ein Klon davon als Arbeitsstand. Ein Test, der nur die
Datei nach Zeichenketten durchsucht, bliebe gruen, wenn die Mechanik bricht —
und genau die Mechanik ist hier das Zerbrechliche. `test_der_hook_meldet_...`
ist die Gegenprobe zu allen Schweige-Tests: Faende das Skript nie etwas,
waeren jene trivialerweise gruen.
"""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_HOOK = _ROOT / ".claude" / "hooks" / "session-start.sh"
_SETTINGS = _ROOT / ".claude" / "settings.json"

# Ohne diese Variablen erbt das Wegwerf-Repo die Identitaet des Aufrufenden —
# in der CI gibt es keine, und `git commit` scheitert.
_GIT_UMGEBUNG = {
    "GIT_AUTHOR_NAME": "Test",
    "GIT_AUTHOR_EMAIL": "test@example.invalid",
    "GIT_COMMITTER_NAME": "Test",
    "GIT_COMMITTER_EMAIL": "test@example.invalid",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_SYSTEM": os.devnull,
}


def _git(*args: str, cwd: pathlib.Path) -> str:
    ergebnis = subprocess.run(
        ["git", *args],
        cwd=cwd,
        env={**os.environ, **_GIT_UMGEBUNG},
        capture_output=True,
        text=True,
        check=True,
    )
    return ergebnis.stdout.strip()


def _ausgefuehrte_zeilen(quelltext: str) -> list[str]:
    """Nur Zeilen, die bash wirklich ausfuehrt.

    Kommentare und der Rumpf des Meldungs-Heredocs fallen raus. Letzterer
    enthaelt `git fetch ...` als Empfehlung an den Menschen — die erste Fassung
    dieses Tests hielt das fuer einen ungedeckelten Netzaufruf und war rot,
    ohne dass etwas falsch war.
    """
    zeilen: list[str] = []
    im_heredoc = False
    for zeile in quelltext.splitlines():
        if im_heredoc:
            im_heredoc = zeile.strip() != "MELDUNG"
            continue
        if "<<MELDUNG" in zeile:
            im_heredoc = True
            continue
        if zeile.lstrip().startswith("#"):
            continue
        zeilen.append(zeile)
    return zeilen


def _hook(projekt: pathlib.Path) -> subprocess.CompletedProcess[str]:
    """Das Skript so aufrufen, wie Claude Code es aufruft.

    Timeout 30 s: Der Hook selbst deckelt sich auf 8 s. Laeuft er hier in den
    Timeout von pytest, ist genau die Zusicherung verletzt, um die es geht.
    """
    return subprocess.run(
        ["bash", str(_HOOK)],
        cwd=projekt,
        env={**os.environ, **_GIT_UMGEBUNG, "CLAUDE_PROJECT_DIR": str(projekt)},
        capture_output=True,
        text=True,
        timeout=30,
    )


def _commit(repo: pathlib.Path, text: str) -> None:
    (repo / "datei.txt").write_text(text)
    _git("add", "datei.txt", cwd=repo)
    _git("commit", "-m", text, cwd=repo)


@pytest.fixture
def welt(tmp_path: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
    """Ein «Remote» mit Default-Branch `master` und ein Klon davon.

    Bewusst `master`, nicht `main`: Ein Hook, der `main` annimmt, ist hier rot
    statt in einem der drei Portfolio-Repos, die so heissen. Der Klon geht
    ueber einen Dateipfad — kein Netz, damit der Test ueberall laeuft.
    """
    quelle = tmp_path / "quelle"
    quelle.mkdir()
    _git("init", "--initial-branch=master", cwd=quelle)
    _commit(quelle, "erster")

    fern = tmp_path / "fern.git"
    _git("clone", "--bare", str(quelle), str(fern), cwd=tmp_path)

    klon = tmp_path / "klon"
    _git("clone", str(fern), str(klon), cwd=tmp_path)
    return quelle, klon


def _schiebe_remote_vor(quelle: pathlib.Path, tmp_path: pathlib.Path, anzahl: int) -> None:
    for i in range(anzahl):
        _commit(quelle, f"neu-{i}")
    _git("push", str(tmp_path / "fern.git"), "master", cwd=quelle)


def test_der_hook_ist_ausfuehrbar_und_registriert() -> None:
    """Ein nicht registrierter Hook laeuft nie — und faellt nie auf."""
    assert _HOOK.is_file(), f"{_HOOK} fehlt"
    assert os.access(_HOOK, os.X_OK), f"{_HOOK} ist nicht ausfuehrbar"

    eintraege = json.loads(_SETTINGS.read_text())["hooks"]["SessionStart"]
    befehle = [h["command"] for e in eintraege for h in e["hooks"]]
    assert any("session-start.sh" in b for b in befehle), (
        f"settings.json ruft das Skript nicht auf: {befehle}"
    )


def test_der_hook_meldet_fehlende_commits(
    welt: tuple[pathlib.Path, pathlib.Path], tmp_path: pathlib.Path
) -> None:
    """Die Gegenprobe: Liegt der Klon zurueck, sagt der Hook es auch.

    Ohne diesen Test waeren alle Schweige-Tests unten gruen, weil das Skript
    grundsaetzlich nichts sagt — nicht, weil es richtig schweigt.
    """
    quelle, klon = welt
    _schiebe_remote_vor(quelle, tmp_path, 3)

    ergebnis = _hook(klon)
    assert ergebnis.returncode == 0, ergebnis.stderr
    assert "3 Commits" in ergebnis.stdout, ergebnis.stdout
    assert "origin/master" in ergebnis.stdout, (
        f"Default-Branch nicht ermittelt, sondern geraten: {ergebnis.stdout!r}"
    )


def test_der_hook_schweigt_bei_aktuellem_klon(welt: tuple[pathlib.Path, pathlib.Path]) -> None:
    """Bei 0 fehlenden Commits keine Ausgabe — sonst liest es niemand mehr."""
    _, klon = welt
    ergebnis = _hook(klon)
    assert ergebnis.returncode == 0, ergebnis.stderr
    assert ergebnis.stdout == "", f"unerwartete Ausgabe: {ergebnis.stdout!r}"


def test_der_hook_zaehlt_nur_was_fehlt(
    welt: tuple[pathlib.Path, pathlib.Path], tmp_path: pathlib.Path
) -> None:
    """Eigene Commits sind kein Rueckstand.

    `HEAD..FETCH_HEAD` zaehlt nur die Gegenrichtung. Ein `--count` ueber
    `HEAD...FETCH_HEAD` (drei Punkte) waere hier rot: Es zaehlte die eigene
    Arbeit mit und meldete Rueckstand, wo keiner ist.
    """
    quelle, klon = welt
    _schiebe_remote_vor(quelle, tmp_path, 2)
    _commit(klon, "eigene-arbeit")
    _commit(klon, "eigene-arbeit-2")

    ergebnis = _hook(klon)
    assert "2 Commits" in ergebnis.stdout, ergebnis.stdout


@pytest.mark.parametrize(
    "fall",
    ["kein_repo", "kein_remote", "leeres_repo", "detached_head", "totes_remote"],
)
def test_der_hook_blockiert_nie(
    fall: str, welt: tuple[pathlib.Path, pathlib.Path], tmp_path: pathlib.Path
) -> None:
    """Jeder Stoerfall geht still durch: Exit 0, keine Ausgabe.

    Das ist die oberste Zusicherung. Ein Hook, der bei Netzproblemen die Arbeit
    anhaelt, wird nach dem zweiten Mal abgeschaltet und schuetzt danach nichts.
    `totes_remote` zeigt zusaetzlich, dass das Timeout greift: Die Adresse ist
    nicht aufloesbar, der Aufruf darf trotzdem nicht haengen.
    """
    quelle, klon = welt

    if fall == "kein_repo":
        ziel = tmp_path / "kein_repo"
        ziel.mkdir()
    elif fall == "leeres_repo":
        ziel = tmp_path / "leer"
        ziel.mkdir()
        _git("init", cwd=ziel)
    elif fall == "kein_remote":
        ziel = klon
        _git("remote", "remove", "origin", cwd=ziel)
    elif fall == "detached_head":
        ziel = klon
        _schiebe_remote_vor(quelle, tmp_path, 1)
        _git("checkout", "--detach", "HEAD", cwd=ziel)
    else:
        ziel = klon
        _git("remote", "set-url", "origin", "https://nicht.aufloesbar.invalid/x.git", cwd=ziel)
        # Der lokale `origin/HEAD` ueberlebt das Umbiegen; ohne ihn wuerde der
        # Hook schon an der Branch-Ermittlung aussteigen, statt am `fetch`.
        _git("symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/master", cwd=ziel)

    ergebnis = _hook(ziel)
    assert ergebnis.returncode == 0, f"{fall}: Exit {ergebnis.returncode}, {ergebnis.stderr}"

    if fall == "detached_head":
        # Detached HEAD ist kein Stoerfall fuer die Zaehlung — HEAD ist dort
        # eine gueltige Revision. Der Hook darf melden, aber nicht scheitern.
        assert "1 Commit" in ergebnis.stdout, ergebnis.stdout
    else:
        assert ergebnis.stdout == "", f"{fall}: unerwartete Ausgabe {ergebnis.stdout!r}"


def test_der_hook_raet_den_branch_nicht(
    welt: tuple[pathlib.Path, pathlib.Path], tmp_path: pathlib.Path
) -> None:
    """Ohne ermittelbaren Default-Branch schweigt er, statt `main` zu nehmen.

    Hier fehlt `refs/remotes/origin/HEAD` und der Remote ist nicht erreichbar.
    Ein fest verdrahtetes `main` haette hier zwei Wege: rot werden, oder — wie
    geschehen — wie ein Netzproblem aussehen und den veralteten Klon
    durchwinken.
    """
    quelle, klon = welt
    _schiebe_remote_vor(quelle, tmp_path, 4)
    _git("symbolic-ref", "--delete", "refs/remotes/origin/HEAD", cwd=klon)
    _git("remote", "set-url", "origin", "https://nicht.aufloesbar.invalid/x.git", cwd=klon)

    ergebnis = _hook(klon)
    assert ergebnis.returncode == 0, ergebnis.stderr
    assert ergebnis.stdout == "", f"Branch geraten: {ergebnis.stdout!r}"


def test_das_timeout_ist_kurz_und_deckelt_beide_netzaufrufe() -> None:
    """Wenige Sekunden, nicht Minuten — und `settings.json` deckelt nochmals.

    Der Hook macht zwei Netzaufrufe (`ls-remote` bei der Branch-Ermittlung,
    `fetch`). Beide muessen durch `mit_timeout` laufen; ein direkter Aufruf
    haette kein Limit.
    """
    quelltext = _HOOK.read_text()
    assert "CLAUDE_STALE_CHECK_TIMEOUT:-8}" in quelltext, "Vorgabe-Timeout nicht 8 s"

    ungedeckelt = [
        z.strip()
        for z in _ausgefuehrte_zeilen(quelltext)
        if ("git fetch" in z or "git ls-remote" in z) and "mit_timeout" not in z
    ]
    assert not ungedeckelt, f"Netzaufruf ohne Timeout: {ungedeckelt}"

    # Gegenprobe zum Filter: Faende er gar keine Netzaufrufe mehr, waere die
    # Zusicherung oben gruen, weil sie am falschen Ort sucht.
    gedeckelt = [z for z in _ausgefuehrte_zeilen(quelltext) if "mit_timeout git" in z]
    assert len(gedeckelt) == 2, f"erwartet: ls-remote und fetch, gefunden: {gedeckelt}"

    hook_eintrag = json.loads(_SETTINGS.read_text())["hooks"]["SessionStart"][0]["hooks"][0]
    assert 0 < hook_eintrag["timeout"] <= 30, (
        f"settings.json deckelt den Hook nicht kurz genug: {hook_eintrag.get('timeout')}"
    )


def test_kein_set_e_im_hook() -> None:
    """`set -e` machte jeden Offline-Lauf zum Fehlschlag.

    Der Hook lebt davon, dass fehlschlagende Befehle der Normalfall sind. Mit
    `set -e` endete er offline mit Exit 1 statt still mit 0 — Claude Code
    meldete dann bei jedem Sessionstart einen Hook-Fehler.
    """
    zeilen = [z.strip() for z in _ausgefuehrte_zeilen(_HOOK.read_text())]
    schaltet_ein = [z for z in zeilen if z.startswith("set ") and "e" in z.split()[1].lstrip("-")]
    assert not schaltet_ein, f"`set -e` im Hook: {schaltet_ein}"
    assert any(z.startswith("trap ") and "exit 0" in z for z in zeilen), (
        "kein `trap ... EXIT`, der unerwartete Fehler auf Exit 0 zieht"
    )


def test_keine_anmeldedialoge() -> None:
    """Ein wartender Passwort-Prompt haengt, ohne dass ein Timeout greift.

    `timeout` misst Laufzeit, nicht Fortschritt: Der git-Prozess laeuft ja, er
    wartet nur auf eine Eingabe. Nach 8 s waere er zwar weg — aber `timeout`
    schickt SIGTERM an `git`, nicht an das Terminal, das die Eingabe liest.
    Billiger ist, die Dialoge gar nicht erst zuzulassen.
    """
    quelltext = _HOOK.read_text()
    for schalter in ("GIT_TERMINAL_PROMPT=0", "GIT_ASKPASS", "BatchMode=yes"):
        assert schalter in quelltext, f"{schalter} fehlt — der Hook kann auf Eingabe warten"


def test_die_begruendung_ist_aufgeschrieben() -> None:
    """Der Grund gehoert neben den Hook, nicht in einen Commit-Text.

    Wer den Hook in einem Jahr fuer Rauschen haelt und ihn abschaltet, liest
    diese Datei — nicht `git log`.
    """
    readme = _HOOK.parent / "README.md"
    assert readme.is_file(), "Hook-README fehlt"
    text = readme.read_text()
    assert "3.8.2026" in text, "der Anlass fehlt"
    assert "rote CI" in text and "nicht im Diff" in text, "die Begruendung fehlt"


def test_bash_akzeptiert_das_skript() -> None:
    """Ein Syntaxfehler faellt sonst erst im Sessionstart auf."""
    bash = shutil.which("bash")
    assert bash, "bash nicht gefunden"
    geprueft = subprocess.run([bash, "-n", str(_HOOK)], capture_output=True, text=True)
    assert geprueft.returncode == 0, geprueft.stderr
