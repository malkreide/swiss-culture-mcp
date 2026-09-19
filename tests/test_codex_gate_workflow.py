"""Die tragenden Stellen von `codex-gate.yml` — jede einzeln abgesichert.

Vier Details entscheiden darueber, ob das Gate etwas leistet oder bloss
gruen leuchtet. Alle vier sind leise, wenn sie brechen: Keines macht einen
anderen Job rot, jedes nimmt dem Gate die Wirkung.

1. **Der Job-Name.** Als required check wird ein NAME eingetragen. Wird er
   umbenannt, wartet die Branch Protection auf einen Check, den es nicht mehr
   gibt — oder, je nach Einstellung, auf gar keinen mehr.
2. **`env -u GITHUB_OUTPUT` in der Warteschleife.** Ohne das schriebe das
   Skript je Runde ein weiteres `state=` in dieselbe Datei; welcher Wert
   gilt, haenge dann daran, welchen der Runner zuletzt liest.
3. **Der Grund wird ueber `env:` durchgereicht, nicht ueber `${{ }}`.** Der
   Grund kann woertlich zitierten Fremdtext enthalten — `${{ }}` setzt ihn
   vor dem Start in die Shell ein.
4. **Der letzte Schritt endet bei `proven != true` mit `exit 1`.** Ohne das
   waere der ganze Job ein Kommentar.

Der Test liest die Datei als Text und nicht als YAML: Es geht um die
Shell-Zeilen in den `run:`-Bloecken, und die sind fuer einen YAML-Parser
nur ein String.
"""

from __future__ import annotations

import pathlib

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_WORKFLOW = _ROOT / ".github" / "workflows" / "codex-gate.yml"
_SKRIPT = _ROOT / "scripts" / "classify_codex_review.py"

#: Der Name, der in der Branch Protection als required check steht.
GATE_NAME = "codex-gate"


def _text() -> str:
    return _WORKFLOW.read_text(encoding="utf-8")


def _befehlszeilen() -> list[str]:
    """Nur echte Zeilen — ein erklaerender Kommentar ist kein Aufruf."""
    return [z.strip() for z in _text().splitlines() if not z.lstrip().startswith("#")]


def _klassifizierer_aufrufe() -> list[str]:
    """Zeilen, die das Skript wirklich STARTEN.

    Nicht bloss «Dateiname kommt vor»: Die Hinweise im Job-Summary nennen
    `scripts/classify_codex_review.py` ebenfalls, und ein Scan, der sie
    mitzaehlt, meldet den Aufruf als vorhanden, sobald irgendwo davon die
    Rede ist.
    """
    return [z for z in _befehlszeilen() if "python scripts/classify_codex_review.py" in z]


def test_der_workflow_existiert_und_ruft_den_klassifizierer() -> None:
    """Sichert alles darunter gegen eine leere oder umbenannte Datei ab.

    Faende der Scan die Datei nicht, waeren die Zusicherungen unten entweder
    ein Fehler beim Lesen oder — schlimmer — trivialerweise wahr.
    """
    assert _WORKFLOW.is_file(), f"{_WORKFLOW} fehlt"
    assert _SKRIPT.is_file(), f"{_SKRIPT} fehlt"
    aufrufe = _klassifizierer_aufrufe()
    assert len(aufrufe) == 2, (
        f"erwartet werden genau zwei Aufrufe (Schleife und Endstand), gefunden: {aufrufe}"
    )


def test_der_job_heisst_wie_der_required_check() -> None:
    """Ein umbenannter Job laesst die Branch Protection ins Leere warten."""
    zeilen = _befehlszeilen()
    assert f"{GATE_NAME}:" in zeilen, f"Job `{GATE_NAME}` fehlt in {_WORKFLOW.name}"
    assert f"name: {GATE_NAME}" in zeilen, (
        f"`name: {GATE_NAME}` fehlt — der angezeigte Check-Name muss dem "
        "Eintrag in der Branch Protection entsprechen."
    )


def test_die_warteschleife_schreibt_nicht_in_github_output() -> None:
    """Sonst stuenden dort je Runde weitere `state=`-Zeilen.

    Der Aufruf IN der Schleife muss `env -u GITHUB_OUTPUT` tragen, der
    Aufruf danach gerade nicht — er ist der einzige, der schreiben soll.
    """
    in_schleife = [z for z in _klassifizierer_aufrufe() if "env -u" in z]
    assert len(in_schleife) == 1, (
        "genau ein Aufruf soll `env -u GITHUB_OUTPUT` tragen (der in der "
        f"Warteschleife), gefunden: {in_schleife}"
    )
    assert "env -u GITHUB_OUTPUT python" in _text()


def test_der_grund_wird_ueber_env_durchgereicht_nicht_interpoliert() -> None:
    """`${{ }}` setzt Fremdtext vor dem Start in die Shell ein.

    Der Grund zitiert im Fall `unknown` woertlich, was Codex geschrieben hat.
    Steht diese Interpolation in einem `run:`-Block, laeuft der zitierte Text
    als Shell-Code.
    """
    text = _text()
    assert "REASON: ${{ steps.gate.outputs.reason }}" in text, (
        "der Grund muss ueber einen `env:`-Eintrag in den Schritt kommen"
    )
    for marke in ("outputs.reason", "outputs.state", "outputs.proven"):
        assert f'echo "${{{{ steps.gate.{marke} }}}}"' not in text, (
            f"`{marke}` wird in eine Shell-Zeile interpoliert — ueber `env:` gehen"
        )


def test_ein_unbelegtes_urteil_faerbt_den_job_rot() -> None:
    """Ohne `exit 1` waere das ganze Gate ein Kommentar."""
    zeilen = _befehlszeilen()
    assert 'if [ "$PROVEN" = "true" ]; then' in zeilen, (
        "die Verzweigung auf `proven` fehlt — dann haengt rot/gruen an nichts"
    )
    assert "exit 1" in zeilen, "kein `exit 1` — ein unbelegtes Urteil bliebe gruen"


def test_auf_einem_draft_laeuft_das_gate_nicht() -> None:
    """Ein Draft ist kein Merge-Kandidat; ein Gate darauf blockierte nur.

    Die Begruendung ist ausdruecklich NICHT «auf Drafts kommt nichts»: Im
    Nachbar-Repo kam auf einem Draft acht Sekunden nach dem Anlegen die
    Environment-Meldung.
    """
    assert "if: github.event.pull_request.draft == false" in _befehlszeilen()


@pytest.mark.parametrize("ausloeser", ["opened", "ready_for_review", "reopened", "synchronize"])
def test_jeder_ausloeser_der_den_head_aendern_kann_startet_das_gate(ausloeser: str) -> None:
    """`synchronize` ist der wichtigste und der am leichtesten vergessene.

    Ein Push nach dem Review aendert den Head; ohne `synchronize` bliebe der
    alte Check gruen stehen und deckte den neuen Commit mit ab.
    """
    zeile = next(z for z in _befehlszeilen() if z.startswith("types:"))
    assert ausloeser in zeile, f"`{ausloeser}` fehlt in `types:` — {zeile}"


def test_nach_einem_push_wird_ein_review_angestossen() -> None:
    """Ein Push ist kein Codex-Ausloeser — sonst liefe das Gate in den Timeout.

    Codex nennt in seinem Infokasten drei Ausloeser: PR zum Review geoeffnet,
    Draft auf ready, oder ein `@codex review`-Kommentar. Ein Push ist keiner
    davon.
    """
    text = _text()
    assert "if: github.event.action == 'synchronize'" in text
    assert "@codex review" in text
    assert "issues: write" in text, (
        "ohne `issues: write` kann der Job den Anstoss nicht kommentieren"
    )
