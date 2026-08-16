"""pytest conftest.py — CLI-Optionen und Isolation der Live-Tests."""

import pytest


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


def pytest_addoption(parser):
    parser.addoption(
        "--run-live",
        action="store_true",
        default=False,
        help="Live-Integrationstests ausführen (erfordert Netzwerkzugang)",
    )
