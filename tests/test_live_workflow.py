"""Der geplante Live-Lauf muss die Live-Tests auch wirklich einschalten.

`live-tests.yml` rief `pytest tests/ -m live` ohne `--run-live` auf. Jeder
Test in `TestLiveApis` liest die Option ueber die `run_live`-Fixture und
ueberspringt sich ohne sie selbst — der Job sammelte vier Tests ein,
uebersprang vier und endete mit 0. `classify_live_run.py` ordnete das korrekt
als `unknown` ein, der Job wurde also woechentlich rot, ohne die Quelle je
abgefragt zu haben.

Der Rueckfall ist teuer und leise zugleich: Er macht kein Gate rot, das nicht
ohnehin rot waere, aber er nimmt dem einzigen Lauf, der die Quelle befragt,
die Wirkung — und zwar so, dass die Ausgabe («4 skipped») nach Ordnung
aussieht. Genau deshalb steht hier ein Test und nicht bloss ein Kommentar.
"""

from __future__ import annotations

import pathlib
import re

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_WORKFLOW = _ROOT / ".github" / "workflows" / "live-tests.yml"

# Eine Zeile, die pytest mit der Live-Marke startet. Kommentarzeilen sind
# vorher entfernt, ein erklaerender Hinweis auf die Option zaehlt also nicht
# als Aufruf.
_PYTEST_LIVE = re.compile(r"\bpytest\b(?=.*-m\s+[\"']?live\b)")


def _befehlszeilen() -> list[str]:
    zeilen = _WORKFLOW.read_text(encoding="utf-8").splitlines()
    return [z.strip() for z in zeilen if not z.lstrip().startswith("#")]


def _live_aufrufe() -> list[str]:
    return [z for z in _befehlszeilen() if _PYTEST_LIVE.search(z)]


def test_der_workflow_existiert_und_ruft_pytest_mit_der_live_marke() -> None:
    """Sichert die Zusicherung unten gegen eine leere Liste ab.

    Faende die Suche keinen Aufruf, waere die Schleife leer und die Zusicherung
    trivialerweise wahr — gruen, ohne irgendetwas geprueft zu haben.
    """
    assert _WORKFLOW.is_file(), f"{_WORKFLOW} fehlt"
    aufrufe = _live_aufrufe()
    assert aufrufe, (
        "kein `pytest ... -m live`-Aufruf in live-tests.yml gefunden — "
        "der Scan sucht am falschen Ort"
    )


def test_jeder_live_aufruf_traegt_run_live() -> None:
    """Ohne die Option prueft der woechentliche Lauf nichts."""
    ohne = [z for z in _live_aufrufe() if "--run-live" not in z]
    assert not ohne, (
        f"`-m live` ohne `--run-live` in {_WORKFLOW.name}: {ohne}. Ohne die Option "
        "ueberspringt sich jeder Live-Test selbst; der Lauf endet mit 0, ohne die "
        "Quelle abgefragt zu haben."
    )


def test_die_option_ist_ueberhaupt_registriert() -> None:
    """`--run-live` muss es in conftest.py geben, sonst bricht pytest ab.

    Ohne diese Kontrolle bliebe der Test oben gruen, waehrend der Workflow eine
    Option uebergibt, die pytest nicht kennt (`unrecognized arguments`) — ein
    Lauf, der die Quelle wieder nicht erreicht.
    """
    conftest = (_ROOT / "tests" / "conftest.py").read_text(encoding="utf-8")
    assert '"--run-live"' in conftest or "'--run-live'" in conftest, (
        "conftest.py registriert `--run-live` nicht mehr"
    )
