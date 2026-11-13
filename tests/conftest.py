"""pytest conftest.py — CLI-Optionen, Isolation der Live-Tests, Wiederholungen."""

import collections

import pytest

# Die Wiederholungen des Server-Clients waehrend der Live-Tests, je (Host, Grund).
# Nur waehrend Live-Tests: Die Offline-Tests in `test_wiederholung.py` stellen
# Stoerungen nach und wiederholen dabei absichtlich — die gehoeren nicht in die
# Zahl, die etwas ueber die Quelle aussagen soll.
_LIVE_WIEDERHOLUNGEN: collections.Counter = collections.Counter()


@pytest.fixture(autouse=True)
def _frischer_http_client(request):
    """Vor jedem Live-Test den modulweiten HTTP-Client fallen lassen.

    `http_client._get_http_client()` haelt einen Client fuers Connection-Pooling
    und baut ihn nur neu, wenn er `None` oder `is_closed` ist. Im Serverbetrieb
    stimmt das — dort lebt ein Event-Loop, solange der Prozess laeuft. Unter
    pytest bekommt jeder Test einen eigenen Loop: Der zweite Live-Test erbt den
    Client des ersten, dessen Loop zu ist. `is_closed` ist dabei False, der
    Client wird also wiederverwendet und der Aufruf endet in
    `RuntimeError: Event loop is closed`.

    Sichtbar wurde das als `json.decoder.JSONDecodeError` — der Fehler-Handler
    gibt `Fehler: RuntimeError.` zurueck, und daran scheitert `json.loads`. Ohne
    diese Fixture meldet der woechentliche Lauf einen gebrochenen Vertrag mit
    der Quelle, wo nur zwei Tests hintereinander liefen: genau der Fehlbefund,
    den `classify_live_run.py` nicht abfangen kann, weil die Suite ja
    tatsaechlich rot ist.

    Nur `None` setzen, nicht schliessen: Zum Schliessen braucht es den Loop,
    der bereits zu ist.
    """
    if request.node.get_closest_marker("live") is None:
        yield
        return

    from swiss_culture_mcp import http_client

    http_client._http_client = None
    yield
    http_client._http_client = None


@pytest.fixture(autouse=True)
def _wiederholungen_zaehlen(request):
    """Zaehlt, wie oft der Server waehrend eines Live-Tests ein zweites Mal fragt.

    Seit dem 7.11.2026 wiederholt `http_client._abrufen` eine Anfrage nach einer
    Stoerung einmal. Gelingt der zweite Versuch, bleibt der Test gruen, und
    pytest zeigt die Ausgabe eines gruenen Tests nicht — die Wiederholung waere
    unsichtbar, und mit ihr, dass die Quelle hakt. Deshalb die Differenz des
    Zaehlers vor und nach jedem Live-Test, ausgewiesen am Ende des Laufs.
    """
    if request.node.get_closest_marker("live") is None:
        yield
        return

    from swiss_culture_mcp import http_client

    vorher = http_client.WIEDERHOLUNGEN.copy()
    yield
    _LIVE_WIEDERHOLUNGEN.update(http_client.WIEDERHOLUNGEN - vorher)


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Ein eigener Abschnitt am Ende jedes Live-Laufs — auch bei null.

    Die erste Zeile beginnt immer mit `Wiederholungen: `; der Workflow liest sie
    in die Zusammenfassung des Laufs. Eine 0 steht ausdruecklich da: Fehlte die
    Zeile bei null, waere «nichts wiederholt» nicht von «nicht gezaehlt» zu
    unterscheiden.
    """
    if not config.getoption("--run-live"):
        return
    terminalreporter.section("Wiederholungen der Quellen")
    gesamt = sum(_LIVE_WIEDERHOLUNGEN.values())
    if not gesamt:
        terminalreporter.write_line(
            "Wiederholungen: 0 — jede Anfrage des Server-Clients beim ersten Versuch beantwortet"
        )
        return
    terminalreporter.write_line(f"Wiederholungen: {gesamt}")
    for (host, grund), anzahl in sorted(_LIVE_WIEDERHOLUNGEN.items()):
        terminalreporter.write_line(f"  {host}  {grund}  {anzahl}")


def pytest_addoption(parser):
    parser.addoption(
        "--run-live",
        action="store_true",
        default=False,
        help="Live-Integrationstests ausführen (erfordert Netzwerkzugang)",
    )
