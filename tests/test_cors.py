"""CORS des HTTP-Transports (SDK-004).

`MCPServer.run()` serviert die ASGI-App ohne CORS. Ein Browser-Client kann den
Antwort-Header `Mcp-Session-Id` dann nicht lesen und verliert seine Sitzung —
der Server antwortet korrekt, und der Client kommt trotzdem nicht weiter.

Offline: nichts hier spricht mit einem Upstream.
"""

from __future__ import annotations

from starlette.middleware.cors import CORSMiddleware
from starlette.testclient import TestClient

from swiss_culture_mcp.server import (
    CORS_ALLOW_HEADERS,
    build_http_app,
    configured_origins,
)


def _cors_middleware(app):
    """Die installierte CORS-Schicht samt ihren Argumenten herausziehen.

    Ueber `app.user_middleware` und nicht ueber eine Anfrage: Die Optionen
    stehen so einzeln da, und ein Test kann eine fehlende benennen, statt nur
    einen ausbleibenden Header zu melden.
    """
    for mw in app.user_middleware:
        if mw.cls is CORSMiddleware:
            return mw
    raise AssertionError("keine CORSMiddleware installiert")


# ---------------------------------------------------------------------------
# Konfiguration der Schicht
# ---------------------------------------------------------------------------


def test_die_app_traegt_eine_cors_schicht(monkeypatch):
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    _cors_middleware(build_http_app())


def test_mcp_session_id_wird_dem_browser_freigegeben(monkeypatch):
    """Der eigentliche Punkt von SDK-004. Ein Browser liest einen
    Antwort-Header nur, wenn er in `expose_headers` steht."""
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    mw = _cors_middleware(build_http_app())
    assert "Mcp-Session-Id" in mw.kwargs["expose_headers"]


def test_die_header_allowlist_ist_kein_wildcard():
    """Bei `"*"` schaltet Starlette auf `allow_all_headers` und spiegelt
    zurueck, was der Browser ankuendigt. Das ist nicht eine Allowlist, sondern
    ihr Fehlen — und es verdeckt jede Drift, weil ein Wildcard nicht falsch
    werden kann."""
    assert "*" not in CORS_ALLOW_HEADERS


def test_die_header_allowlist_nennt_die_header_des_protokolls():
    """Die Routing-Header der Aera `2026-07-28` plus Sitzung und
    SSE-Wiederaufnahme. Faellt einer weg, bricht nur der zugehoerige Fall —
    bei `Last-Event-ID` sogar nur die Wiederaufnahme nach Paketverlust, der
    unangenehmste Weg, einen Fehler zu finden."""
    for header in (
        "Content-Type",
        "Mcp-Method",
        "Mcp-Name",
        "Mcp-Protocol-Version",
        "Mcp-Session-Id",
        "Last-Event-ID",
    ):
        assert header in CORS_ALLOW_HEADERS, f"{header} fehlt in CORS_ALLOW_HEADERS"


def test_die_erlaubten_methoden_decken_den_transport_ab(monkeypatch):
    """Streamable HTTP nutzt POST fuer Aufrufe, GET fuer den SSE-Strom und
    DELETE fuer das Beenden einer Sitzung."""
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    mw = _cors_middleware(build_http_app())
    for methode in ("GET", "POST", "DELETE", "OPTIONS"):
        assert methode in mw.kwargs["allow_methods"]


# ---------------------------------------------------------------------------
# Origins: fail-closed
# ---------------------------------------------------------------------------


def test_ohne_env_var_ist_kein_origin_zugelassen(monkeypatch):
    """Fail-closed: Wer nichts setzt, erbt keine durchlaessige Einstellung."""
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    assert configured_origins() == []


def test_origins_werden_kommagetrennt_gelesen(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://claude.ai, https://example.ch ")
    assert configured_origins() == ["https://claude.ai", "https://example.ch"]


def test_leere_eintraege_fallen_weg(monkeypatch):
    """`"https://claude.ai,"` darf keinen leeren Origin erzeugen — ein leerer
    String in der Liste waere ein Eintrag, der auf nichts passt und trotzdem
    wie eine Konfiguration aussieht."""
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://claude.ai,,")
    assert configured_origins() == ["https://claude.ai"]


def test_ein_fremdes_origin_bekommt_keine_freigabe(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://claude.ai")
    with TestClient(build_http_app()) as client:
        antwort = client.options(
            "/mcp",
            headers={
                "Origin": "https://evil.example.com",
                "Access-Control-Request-Method": "POST",
            },
        )
    assert "access-control-allow-origin" not in {k.lower() for k in antwort.headers}


def test_ein_konfiguriertes_origin_bekommt_die_freigabe(monkeypatch):
    """Gegenprobe zur Zeile darueber: Ohne sie waere jener Test auch gruen,
    wenn die CORS-Schicht gar nichts freigibt."""
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://claude.ai")
    with TestClient(build_http_app()) as client:
        antwort = client.options(
            "/mcp",
            headers={
                "Origin": "https://claude.ai",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type,mcp-session-id",
            },
        )
    assert antwort.headers.get("access-control-allow-origin") == "https://claude.ai"
    erlaubt = antwort.headers.get("access-control-allow-headers", "").lower()
    assert "mcp-session-id" in erlaubt
