"""Jede GitHub-Action haengt an einem Commit-SHA, nicht an einem Tag.

Ein Tag ist beweglich. `actions/checkout@v7` und `pypa/...@release/v1` zeigen
auf das, worauf der Herausgeber sie zeigen laesst — auch nachtraeglich, auch
auf anderen Code als gestern. Bei `publish.yml` haengt daran ein Job mit
`id-token: write`, der auf PyPI veroeffentlichen darf.

Der Rueckfall ist leise: Ein Tag-Pin macht kein Gate rot, er nimmt der
Lieferkette nur die Nachpruefbarkeit. Deshalb steht hier ein Test.

Der Kommentar hinter dem SHA ist nicht Zierde: Ohne ihn steht in der Datei
eine 40-stellige Zahl, und niemand sieht mehr, welche Version das ist oder ob
sie alt ist.
"""

from __future__ import annotations

import pathlib
import re

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_WORKFLOWS = _ROOT / ".github" / "workflows"

# `uses:` mit Wert, Kommentarzeilen sind vorher raus.
_USES = re.compile(r"^\s*-?\s*uses:\s*(?P<ref>\S+)\s*(?P<rest>.*)$")
_SHA = re.compile(r"^[0-9a-f]{40}$")
# `# v1.2.3` oder `# v1` — irgendeine lesbare Versionsangabe.
_VERSIONSKOMMENTAR = re.compile(r"#\s*v?\d[\w.\-+]*")


def _workflow_dateien() -> list[pathlib.Path]:
    """Beide Endungen: GitHub laedt `*.yml` UND `*.yaml`."""
    return sorted([*_WORKFLOWS.glob("*.yml"), *_WORKFLOWS.glob("*.yaml")])


def _verwendungen() -> list[tuple[pathlib.Path, str, str]]:
    """(Datei, Referenz, Rest der Zeile) je `uses:`-Zeile."""
    gefunden = []
    for wf in _workflow_dateien():
        for zeile in wf.read_text(encoding="utf-8").splitlines():
            if zeile.lstrip().startswith("#"):
                continue
            treffer = _USES.match(zeile)
            if treffer:
                gefunden.append((wf, treffer.group("ref"), treffer.group("rest")))
    return gefunden


def test_der_scan_findet_ueberhaupt_actions() -> None:
    """Sichert die Zusicherungen unten gegen eine leere Liste ab.

    Faende der Scan nichts — umbenanntes Verzeichnis, geaenderte Schreibweise —,
    waeren die Schleifen leer und beide Tests trivialerweise wahr.
    """
    verwendungen = _verwendungen()
    assert len(verwendungen) >= 5, f"verdaechtig wenige `uses:` gefunden: {verwendungen}"


def test_jede_action_haengt_an_einem_commit_sha() -> None:
    """Ein Tag kann umgehaengt werden, ein Commit-SHA nicht."""
    lose = []
    for wf, ref, _ in _verwendungen():
        if ref.startswith("./"):
            continue  # lokale Action im Repo, kein Fremdcode
        _, _, version = ref.partition("@")
        if not _SHA.match(version):
            lose.append(f"{wf.name}: {ref}")
    assert not lose, (
        f"nicht auf einen Commit-SHA gepinnt: {lose}. Ein Tag oder Branch zeigt auf "
        "das, worauf der Herausgeber ihn zeigen laesst — auch nachtraeglich. "
        "SHA ermitteln mit: git ls-remote https://github.com/<owner>/<repo> "
        "'refs/tags/<tag>^{}'"
    )


def test_jeder_pin_sagt_welche_version_er_ist() -> None:
    """Sonst steht da eine 40-stellige Zahl und niemand sieht, wie alt sie ist."""
    ohne = []
    for wf, ref, rest in _verwendungen():
        if ref.startswith("./"):
            continue
        if not _VERSIONSKOMMENTAR.search(rest):
            ohne.append(f"{wf.name}: {ref}")
    assert not ohne, (
        f"Pin ohne Versionskommentar: {ohne}. Erwartet wird `uses: owner/repo@<sha> # v1.2.3`."
    )
