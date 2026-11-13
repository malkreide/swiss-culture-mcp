"""Der Live-Lauf weist aus, wie oft der Server ein zweites Mal fragen musste.

Seit dem 7.11.2026 wiederholt `http_client._abrufen` eine Anfrage nach einer
Stoerung einmal. Gelingt der zweite Versuch, ist der Test gruen — und pytest
zeigt die Ausgabe gruener Tests nicht. Die Live-Laeufe vom 9. und 11.11.2026
waren gruen, und ob dabei wiederholt wurde, gab das Protokoll nicht her.

Geprueft wird hier der echte `tests/conftest.py`, in einem inneren pytest-Lauf
(`pytester`): Ein nachgestellter Live-Test mit einer Wiederholung muss am Ende
den Abschnitt «Wiederholungen der Quellen» mit `Wiederholungen: 1` erzeugen.
"""

from __future__ import annotations

from pathlib import Path

pytest_plugins = ["pytester"]

_CONFTEST = (Path(__file__).resolve().parent / "conftest.py").read_text(encoding="utf-8")

# Wie `pyproject.toml`: ohne den Loop-Scope warnte pytest-asyncio im inneren Lauf
# wieder, und die Warnung landete in der Ausgabe des aeusseren (siehe #83).
_INI = """
[pytest]
asyncio_default_fixture_loop_scope = function
markers =
    live: Live-Test
"""

# Ein Live-Test, der eine Anfrage ueber den echten Server-Client schickt —
# gegen eine nachgestellte Gegenseite statt gegen das Netz.
_TESTS = '''
import asyncio

import httpx
import pytest

from swiss_culture_mcp import http_client


async def _keine_pause(_sekunden):
    return None


def _abruf(monkeypatch, *antworten):
    folge = list(antworten)

    def gegenseite(request):
        naechste = folge.pop(0)
        if isinstance(naechste, type):
            raise naechste("simuliert", request=request)
        return naechste

    client = httpx.AsyncClient(transport=httpx.MockTransport(gegenseite))
    monkeypatch.setattr(http_client, "_http_client", client)
    monkeypatch.setattr(http_client, "_pause", _keine_pause)
    return asyncio.run(http_client._get("https://api3.geo.admin.ch/x"))


@pytest.mark.live
def test_live_mit_wiederholung(monkeypatch):
    assert _abruf(monkeypatch, httpx.ReadTimeout, httpx.Response(200, json={})) == {}


@pytest.mark.live
def test_live_ohne_wiederholung(monkeypatch):
    assert _abruf(monkeypatch, httpx.Response(200, json={})) == {}


def test_offline_mit_wiederholung(monkeypatch):
    """Eine Wiederholung ausserhalb eines Live-Tests zaehlt nicht."""
    assert _abruf(monkeypatch, httpx.ReadTimeout, httpx.Response(200, json={})) == {}
'''


def _lauf(pytester, *argumente):
    pytester.makeconftest(_CONFTEST)
    pytester.makeini(_INI)
    pytester.makepyfile(test_innen=_TESTS)
    return pytester.runpytest("-p", "no:cacheprovider", *argumente)


def test_eine_wiederholung_im_live_test_steht_am_ende_des_laufs(pytester):
    ergebnis = _lauf(pytester, "--run-live", "-m", "live", "-k", "mit_wiederholung")
    ergebnis.assert_outcomes(passed=1)
    ergebnis.stdout.fnmatch_lines(
        [
            "*Wiederholungen der Quellen*",
            "Wiederholungen: 1",
            "  api3.geo.admin.ch  ReadTimeout  1",
        ]
    )


def test_null_wiederholungen_stehen_ausdruecklich_da(pytester):
    """Fehlte die Zeile bei null, waere «nichts wiederholt» nicht von «nicht gezaehlt» zu trennen."""
    ergebnis = _lauf(pytester, "--run-live", "-m", "live", "-k", "ohne_wiederholung")
    ergebnis.assert_outcomes(passed=1)
    ergebnis.stdout.fnmatch_lines(["Wiederholungen: 0 *"])


def test_wiederholungen_ausserhalb_der_live_tests_zaehlen_nicht(pytester):
    ergebnis = _lauf(pytester, "--run-live", "-k", "offline or ohne_wiederholung")
    ergebnis.assert_outcomes(passed=2)
    ergebnis.stdout.fnmatch_lines(["Wiederholungen: 0 *"])


def test_ohne_run_live_kein_abschnitt(pytester):
    ergebnis = _lauf(pytester, "-k", "offline")
    ergebnis.assert_outcomes(passed=1)
    ergebnis.stdout.no_fnmatch_line("*Wiederholungen*")
