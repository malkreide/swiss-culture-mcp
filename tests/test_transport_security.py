"""Eingehende Host-/Origin-Pruefung des HTTP-Transports (SEC-005).

`main()` startete den HTTP-Transport ueber `mcp.run()`, das `transport_security`
gar nicht entgegennimmt. Der Befund dazu lautete: «ohne `transport_security`
prueft das SDK weder `Host` noch `Origin`», gestuetzt auf den Kommentar in
`mcp/server/transport_security.py` («If not specified, disable DNS rebinding
protection by default for backwards compatibility»).

**Die Gegenprobe unten hat genau diesen Satz widerlegt**, und das ist der
Grund, warum sie hier steht. `Server.streamable_http_app()` schaltet den
Schutz bei einem Loopback-Bind von sich aus ein, und `mcp.run()` reicht `host`
dorthin durch. Gemessen, `transport_security=None`:

    host=127.0.0.1   fremder Host -> 421   127.0.0.1:9999 -> 200
    host=0.0.0.0     fremder Host -> 200   127.0.0.1:9999 -> 200

Der Befund traegt also fuer `MCP_HOST=0.0.0.0` — die Vorgabe des
Container-Images — und nur dort. Und die Vorgabe des SDK fuer Loopback traegt
einen PORT-WILDCARD (`127.0.0.1:*`); die Liste dieses Moduls ist portgenau und
damit enger als das, was vorher galt. Darum ist
`test_richtiger_host_falscher_port_wird_abgewiesen` kein Zierrat, sondern der
einzige Fall, in dem sich die neue Liste ueberhaupt von der alten Vorgabe
unterscheidet.

Offline: der `TestClient` von Starlette spricht die ASGI-App direkt an, es
geht kein Paket ins Netz.
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from swiss_culture_mcp.server import build_transport_security, mcp

_INIT = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "1"},
    },
}
_HEADERS = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}


# ---------------------------------------------------------------------------
# Die hergeleitete Allowlist
# ---------------------------------------------------------------------------


def test_loopback_bind_schaltet_den_schutz_ein(monkeypatch):
    monkeypatch.delenv("MCP_ALLOWED_HOSTS", raising=False)
    sec = build_transport_security("127.0.0.1", 8000)
    assert sec is not None
    assert sec.enable_dns_rebinding_protection is True
    assert "127.0.0.1:8000" in sec.allowed_hosts
    assert "localhost:8000" in sec.allowed_hosts


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1"])
def test_alle_schreibweisen_von_loopback_gelten_als_lokal(host, monkeypatch):
    monkeypatch.delenv("MCP_ALLOWED_HOSTS", raising=False)
    assert build_transport_security(host, 8000) is not None


def test_nicht_lokaler_bind_ohne_allowlist_bleibt_ungeschuetzt(monkeypatch):
    """0.0.0.0 ohne Allowlist: Unter welchem Namen der Server erreichbar ist,
    weiss dieser Prozess nicht. Eine geratene Liste wuerde JEDE echte Anfrage
    mit 421 abweisen. Der Schutz bleibt aus, `_run_http()` warnt dafuer.

    Diese Luecke ist Absicht und darum eine eigene Zusicherung — sonst sieht
    ein spaeterer Blick sie fuer ein Versehen an und `fixt` sie in einen
    Totalausfall.
    """
    monkeypatch.delenv("MCP_ALLOWED_HOSTS", raising=False)
    assert build_transport_security("0.0.0.0", 8000) is None


def test_nicht_lokaler_bind_mit_allowlist_schaltet_den_schutz_ein(monkeypatch):
    monkeypatch.setenv("MCP_ALLOWED_HOSTS", "mcp.example.ch, kultur.example.ch")
    sec = build_transport_security("0.0.0.0", 8000)
    assert sec is not None
    assert "mcp.example.ch" in sec.allowed_hosts
    # Leerzeichen um das Komma duerfen nicht in den Eintrag geraten: das SDK
    # vergleicht zeichenweise, " kultur.example.ch" passt auf nichts.
    assert "kultur.example.ch" in sec.allowed_hosts


def test_loopback_bleibt_trotz_allowlist_erlaubt(monkeypatch):
    """Sonst meldet der Healthcheck des Containers — der auf 127.0.0.1
    verbindet — einen gesunden Server als krank."""
    monkeypatch.setenv("MCP_ALLOWED_HOSTS", "mcp.example.ch")
    sec = build_transport_security("0.0.0.0", 8000)
    assert "127.0.0.1:8000" in sec.allowed_hosts


def test_der_port_wird_mitgefuehrt(monkeypatch):
    monkeypatch.delenv("MCP_ALLOWED_HOSTS", raising=False)
    sec = build_transport_security("127.0.0.1", 9443)
    assert "127.0.0.1:9443" in sec.allowed_hosts
    assert "127.0.0.1:8000" not in sec.allowed_hosts


def test_der_wildcard_wandert_nicht_in_die_origins(monkeypatch):
    """`*` wird vom SDK zeichenweise verglichen. Kopiert saehe er wie ein
    Wildcard aus und taete nichts — die gefaehrlichste Form von beidem."""
    monkeypatch.delenv("MCP_ALLOWED_HOSTS", raising=False)
    monkeypatch.setenv("ALLOWED_ORIGINS", "*")
    sec = build_transport_security("127.0.0.1", 8000)
    assert "*" not in sec.allowed_origins
    # Die hergeleiteten Loopback-Origins muessen trotzdem dastehen, sonst
    # weist der Server eine Browser-Anfrage vom selben Host ab.
    assert "http://127.0.0.1:8000" in sec.allowed_origins


def test_konfigurierte_origins_bestehen_auch_die_transport_pruefung(monkeypatch):
    """Sonst weist der Transport genau die Browser-Clients ab, die CORS
    zulaesst — zwei Listen, die sich widersprechen, und der Fehler zeigt sich
    erst am lebenden Deployment."""
    monkeypatch.delenv("MCP_ALLOWED_HOSTS", raising=False)
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://claude.ai")
    sec = build_transport_security("127.0.0.1", 8000)
    assert "https://claude.ai" in sec.allowed_origins


# ---------------------------------------------------------------------------
# Am Draht: was die App tatsaechlich beantwortet
# ---------------------------------------------------------------------------


def _post_mit_host(host_header: str):
    # `transport_security` ist in mcp 2.x ein Argument DER APP, kein Feld auf
    # `mcp.settings` — dort gibt es es nicht mehr.
    app = mcp.streamable_http_app(
        transport_security=build_transport_security("127.0.0.1", 8000),
    )
    with TestClient(app) as client:
        return client.post("/mcp", headers={"Host": host_header, **_HEADERS}, json=_INIT)


def test_erlaubter_host_wird_bedient(monkeypatch):
    monkeypatch.delenv("MCP_ALLOWED_HOSTS", raising=False)
    assert _post_mit_host("127.0.0.1:8000").status_code == 200


def test_fremder_host_wird_abgewiesen(monkeypatch):
    monkeypatch.delenv("MCP_ALLOWED_HOSTS", raising=False)
    assert _post_mit_host("evil.example.com").status_code == 421


def test_richtiger_host_falscher_port_wird_abgewiesen(monkeypatch):
    """Der tragende Fall. Eine Notfall-Regel, die nur `localhost` durchlaesst,
    wuerde `evil.example.com` ebenfalls abweisen — dieser Test bliebe gruen,
    obwohl die portgenaue Liste gar nicht installiert ist. Erst richtiger
    Hostname bei falschem Port zeigt, dass sie wirklich wirkt.
    """
    monkeypatch.delenv("MCP_ALLOWED_HOSTS", raising=False)
    assert _post_mit_host("127.0.0.1:9999").status_code == 421


def _post_ohne_schutz(bind_host: str, host_header: str):
    """Dieselbe App OHNE `transport_security` — also der Zustand vor SEC-005.

    `bind_host` ist nicht kosmetisch: Das SDK leitet aus ihm seine eigene
    Vorgabe ab. Ein Aufruf, der ihn weglaesst, misst den Default `127.0.0.1`
    und damit den geschuetzten Fall — genau daran ist die erste Fassung dieses
    Moduls gescheitert.
    """
    app = mcp.streamable_http_app(transport_security=None, host=bind_host)
    with TestClient(app) as client:
        return client.post("/mcp", headers={"Host": host_header, **_HEADERS}, json=_INIT)


def test_ohne_schutz_geht_der_fremde_host_bei_public_bind_durch():
    """Die Gegenprobe zur Zusicherung selbst: Dass oben 421 kommt, liegt an
    der Allowlist und nicht daran, dass die App fremde Hosts ohnehin abwiese.

    Das ist zugleich der Nachweis des Befunds SEC-005. `0.0.0.0` ist, was das
    Container-Image setzt.
    """
    assert _post_ohne_schutz("0.0.0.0", "evil.example.com").status_code == 200, (
        "ohne transport_security weist das SDK bei 0.0.0.0 einen fremden Host "
        "inzwischen selbst ab — dann ist die Begruendung dieses Moduls zu pruefen"
    )


def test_die_sdk_vorgabe_fuer_loopback_traegt_einen_port_wildcard():
    """Was die neue Liste ueber die SDK-Vorgabe hinaus leistet, und sonst
    nichts.

    Bei einem Loopback-Bind installiert `streamable_http_app()` von sich aus
    `127.0.0.1:*` — fremde Hosts fallen damit schon durch, beliebige Ports
    nicht. Faellt diese Zeile, hat das SDK seine Vorgabe geaendert und die
    Begruendung im Kopf dieses Moduls stimmt nicht mehr.
    """
    assert _post_ohne_schutz("127.0.0.1", "evil.example.com").status_code == 421
    assert _post_ohne_schutz("127.0.0.1", "127.0.0.1:9999").status_code == 200
