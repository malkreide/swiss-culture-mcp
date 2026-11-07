"""
Tests für swiss-culture-mcp.

Einheitstests mit Mocks (immer) und Live-Integrationstests (mit --run-live).
"""

import json
import pathlib
import sys
from datetime import datetime
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import httpx
import pytest

from swiss_culture_mcp.server import (
    KANTONE,
    SDK_HTTP_TRANSPORT,
    IsosDetailInput,
    IsosKantonInput,
    IsosSearchInput,
    KulturpreiseInput,
    NewsInput,
    OpendataInput,
    TraditionDetailInput,
    TraditionListInput,
    _format_isos_entry,
    _handle_error,
    _parse_rss_items,
    bak_get_isos_detail,
    bak_get_kulturpreise,
    bak_get_news,
    bak_get_opendata,
    bak_get_tradition_detail,
    bak_isos_by_kanton,
    bak_list_traditions,
    bak_search_isos,
    main,
    mcp,
)

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

import visos_anhang  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures & Hilfsdaten
# ---------------------------------------------------------------------------

MOCK_ISOS_RESULTS = {
    "results": [
        {
            "id": "1148957451775839307",
            "featureId": "1148957451775839307",
            "attributes": {
                "nummer": 5800,
                "kantone": ["ZH"],
                "name": "Zürich",
                "siedlungskategorie": "Stadt",
                "url": "https://www.gisos.bak.admin.ch/sites/5800",
                "label": "Zürich",
                "teil_name": None,
                "teil_nummer": None,
            },
        },
        {
            "id": "1149000000000000001",
            "featureId": "1149000000000000001",
            "attributes": {
                "nummer": 5801,
                "kantone": ["ZH"],
                "name": "Zürich-Wiedikon",
                "siedlungskategorie": "Dorf",
                "url": "https://www.gisos.bak.admin.ch/sites/5801",
                "label": "Zürich-Wiedikon",
                "teil_name": None,
                "teil_nummer": None,
            },
        },
    ]
}

MOCK_ISOS_FEATURE = {
    "feature": {
        "id": "1148957451775839307",
        "featureId": "1148957451775839307",
        "geometry": {"x": 683350.0, "y": 247355.0, "spatialReference": {"wkid": 21781}},
        "attributes": {
            "nummer": 5800,
            "kantone": ["ZH"],
            "name": "Zürich",
            "siedlungskategorie": "Stadt",
            "url": "https://www.gisos.bak.admin.ch/sites/5800",
            "teil_name": None,
            "teil_nummer": None,
        },
    }
}

MOCK_RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:nsb="https://www.news.admin.ch/rss">
<channel>
  <title>News Service Bund</title>
  <item nsb:id="abc123">
    <title>Schweizer Grand Prix Literatur 2026 geht an Corinne Desarzens</title>
    <description>Das Bundesamt für Kultur würdigt das Werk der Schriftstellerin.</description>
    <link>https://news.admin.ch/de/newnsb/abc123</link>
    <pubDate>2026-02-15</pubDate>
    <author>Bundesamt für Kultur</author>
  </item>
  <item nsb:id="def456">
    <title>ISOS: Neue Ortsbildaufnahmen publiziert</title>
    <description>Das BAK hat 12 neue Ortsbildaufnahmen ins ISOS-Inventar aufgenommen.</description>
    <link>https://news.admin.ch/de/newnsb/def456</link>
    <pubDate>2026-01-20</pubDate>
    <author>Bundesamt für Kultur</author>
  </item>
</channel>
</rss>"""

MOCK_CKAN_RESPONSE = {
    "result": {
        "count": 5,
        "results": [
            {
                "name": "bundesinventar-der-schutzenswerten-ortsbilder-isos",
                "title": {"de": "ISOS – Bundesinventar der schützenswerten Ortsbilder"},
                "description": {
                    "de": "Bundesinventar der schützenswerten Ortsbilder der Schweiz von nationaler Bedeutung."
                },
                "resources": [
                    {
                        "format": "WMS",
                        "url": "https://wms.geo.admin.ch/",
                        "name": {"de": "WMS-Dienst"},
                    },
                    {
                        "format": "API",
                        "url": "https://api3.geo.admin.ch/",
                        "name": {"de": "REST API"},
                    },
                ],
                "metadata_modified": "2024-01-15",
                "organization": {"name": "bundesamt-fur-kultur-bak"},
            }
        ],
    }
}

# ---------------------------------------------------------------------------
# Unit-Tests: Hilfsfunktionen
# ---------------------------------------------------------------------------


class TestHelperFunctions:
    def test_format_isos_entry_complete(self):
        attrs = {
            "nummer": 5800,
            "kantone": ["ZH"],
            "name": "Zürich",
            "siedlungskategorie": "Stadt",
            "url": "https://www.gisos.bak.admin.ch/sites/5800",
            "teil_name": None,
            "teil_nummer": None,
        }
        result = _format_isos_entry(attrs, "123456")
        assert result["feature_id"] == "123456"
        assert result["isos_nummer"] == 5800
        assert result["name"] == "Zürich"
        assert result["kantone"] == ["ZH"]
        assert result["siedlungskategorie"] == "Stadt"
        assert "gisos.bak.admin.ch" in result["gisos_url"]

    def test_format_isos_entry_missing_url(self):
        attrs = {"nummer": 999, "name": "Test", "kantone": ["BE"], "url": None}
        result = _format_isos_entry(attrs, "abc")
        assert "999" in result["gisos_url"]

    def test_format_isos_entry_no_nummer(self):
        attrs = {"name": "Unbekannt", "kantone": []}
        result = _format_isos_entry(attrs, "xyz")
        assert result["isos_nummer"] == "–"

    def test_parse_rss_items(self):
        items = _parse_rss_items(MOCK_RSS_XML)
        assert len(items) == 2
        assert "Grand Prix Literatur" in items[0]["title"]
        assert items[0]["pubDate"] == "2026-02-15"
        assert items[1]["id"] == "def456"

    def test_parse_rss_items_limit(self):
        items = _parse_rss_items(MOCK_RSS_XML, max_items=1)
        assert len(items) == 1

    def test_handle_error_timeout(self):
        import httpx

        err = httpx.TimeoutException("timeout")
        result = _handle_error(err)
        assert "Zeitüberschreitung" in result

    def test_handle_error_404(self):
        import httpx

        request = httpx.Request("GET", "https://example.com")
        response = httpx.Response(404, request=request)
        err = httpx.HTTPStatusError("not found", request=request, response=response)
        result = _handle_error(err)
        assert "nicht gefunden" in result

    def test_handle_error_429(self):
        import httpx

        request = httpx.Request("GET", "https://example.com")
        response = httpx.Response(429, request=request)
        err = httpx.HTTPStatusError("rate limit", request=request, response=response)
        result = _handle_error(err)
        assert "Anfragelimit" in result

    def test_handle_error_generic(self):
        result = _handle_error(ValueError("something went wrong"))
        assert "ValueError" in result

    def test_handle_error_no_upstream_body_leak(self):
        import httpx

        request = httpx.Request("GET", "https://example.com")
        response = httpx.Response(418, request=request, text="SECRET_TEAPOT_INTERNALS")
        err = httpx.HTTPStatusError("teapot", request=request, response=response)
        result = _handle_error(err)
        assert "SECRET_TEAPOT_INTERNALS" not in result
        assert "418" in result


# ---------------------------------------------------------------------------
# Unit-Tests: main() / Server-Start-Hardening (SEC-003)
# ---------------------------------------------------------------------------


class TestMainHardening:
    """Der HTTP-Zweig laeuft seit SEC-005 nicht mehr ueber `mcp.run()`.

    `mcp.run(transport="streamable-http", ...)` nimmt weder
    `transport_security` noch CORS entgegen — und ohne `transport_security`
    schaltet das SDK die Host-Pruefung ausdruecklich ab. `main()` ruft deshalb
    `_run_http(host, port)`. Die Tests unten patchen genau diese Stelle; wer
    weiter `mcp.run` patcht, prueft eine Aufrufstelle, die es fuer HTTP nicht
    mehr gibt, und bliebe gruen, waehrend der HTTP-Transport gar nicht mehr
    startet.
    """

    @pytest.fixture(autouse=True)
    def _kein_echter_serverstart(self):
        """Kein Test dieser Klasse darf einen echten Server starten.

        Beide Startwege werden geklammert, und beide aus einem gemessenen
        Grund — die Gegenprobe vom 20.9.2026 hat sie nacheinander geliefert:

        1. `mcp.run(transport="streamable-http", ...)`: Die Mutation «main()
           geht wieder ueber mcp.run()» lief in den Timeout, statt gefangen zu
           werden. Ein Lauf, der nicht endet, ist keine Messung.

        2. `_run_http`: schlimmer, weil gruen. Unter der Mutation «Sperre
           gegen public bind entfaellt» rief
           `test_main_refuses_public_bind_without_override` den ECHTEN
           `_run_http` auf; uvicorn scheiterte am schon belegten Port 8000 und
           beendete sich mit `sys.exit(1)`. Das erwartete `SystemExit` kam
           also — aus der Bindung statt aus der Sperre, und der Test meldete
           bestanden, waehrend er genau das Gegenteil belegt hatte. Waere der
           Port frei gewesen, haette er stattdessen gehangen.

        Tests, die auf einem der beiden Mocks etwas zusichern, patchen ihn
        zusaetzlich selbst; die innere Klammer gewinnt.
        """
        with patch("swiss_culture_mcp.server.mcp.run"):
            with patch("swiss_culture_mcp.server._run_http"):
                yield

    def test_main_refuses_public_bind_without_override(self, monkeypatch):
        monkeypatch.setenv("MCP_TRANSPORT", "streamable_http")
        monkeypatch.setenv("MCP_HOST", "0.0.0.0")
        monkeypatch.delenv("MCP_ALLOW_PUBLIC_BIND", raising=False)
        with pytest.raises(SystemExit):
            main()

    def test_die_sperre_greift_vor_dem_start(self, monkeypatch):
        """Gegenprobe zur Zeile darueber: `SystemExit` allein sagt nicht, dass
        nichts gestartet wurde.

        Das ist nicht theoretisch. Ohne die Klammer oben kam das `SystemExit`
        des Tests darueber unter Mutation aus uvicorns fehlgeschlagener
        Bindung — gemessen am 20.9.2026. Wer nur auf die Ausnahme prueft,
        prueft nicht, WOHER sie kommt.
        """
        monkeypatch.setenv("MCP_TRANSPORT", "streamable_http")
        monkeypatch.setenv("MCP_HOST", "0.0.0.0")
        monkeypatch.delenv("MCP_ALLOW_PUBLIC_BIND", raising=False)
        with patch("swiss_culture_mcp.server._run_http") as mock_http:
            with pytest.raises(SystemExit):
                main()
        mock_http.assert_not_called()

    def test_main_allows_public_bind_with_override(self, monkeypatch):
        monkeypatch.setenv("MCP_TRANSPORT", "streamable_http")
        monkeypatch.setenv("MCP_HOST", "0.0.0.0")
        monkeypatch.setenv("MCP_ALLOW_PUBLIC_BIND", "true")
        with patch("swiss_culture_mcp.server._run_http") as mock_http:
            main()
        mock_http.assert_called_once_with("0.0.0.0", 8000)

    def test_der_http_zweig_laeuft_nicht_mehr_ueber_mcp_run(self, monkeypatch):
        """Die eigentliche Zusicherung von SEC-005 an dieser Stelle.

        `mcp.run()` hat keinen Parameter fuer `transport_security`; wer den
        HTTP-Transport darueber startet, laeuft zwangslaeufig ohne
        Host-Pruefung. Dass `main()` diesen Weg NICHT mehr nimmt, ist darum
        selbst eine Zusicherung und nicht bloss ein Umbau.
        """
        import inspect

        assert "transport_security" not in inspect.signature(type(mcp).run).parameters, (
            "mcp.run() nimmt inzwischen transport_security entgegen — dann ist "
            "die Begruendung fuer die eigene uvicorn-Schleife zu pruefen"
        )

        monkeypatch.setenv("MCP_TRANSPORT", "streamable_http")
        monkeypatch.delenv("MCP_HOST", raising=False)
        monkeypatch.delenv("MCP_ALLOW_PUBLIC_BIND", raising=False)
        with patch("swiss_culture_mcp.server._run_http"):
            with patch("swiss_culture_mcp.server.mcp.run") as mock_run:
                main()
        mock_run.assert_not_called()

    def test_die_transportkonstante_bleibt_ein_name_den_das_sdk_kennt(self, monkeypatch):
        """Hier stand die Erwartung `transport="streamable_http"` — als Literal.

        Das SDK nimmt nur `streamable-http` an, mit Bindestrich; `mcp.run()`
        prueft gegen ein `Literal` und wirft sonst `ValueError: Unknown
        transport`. Der HTTP-Transport startete deshalb nie, und der Test
        blieb gruen: Er patchte `mcp.run` und hielt den uebergebenen String
        gegen eine handgeschriebene Erwartung — denselben Tippfehler. Ein Mock
        nimmt jeden Namen an.

        Seit SEC-005 geht der HTTP-Zweig gar nicht mehr durch `mcp.run()`, die
        Konstante wird dort also nicht mehr uebergeben. Geprueft wird sie
        trotzdem weiter gegen die Signatur des SDK: `tests/test_modern_era.py`
        fuehrt sie real durch `mcp.run()`, und ein stiller Namenswechsel im SDK
        soll hier auffallen, wo die uebrigen `main()`-Tests stehen.
        """
        from typing import get_args, get_type_hints

        erlaubt = get_args(get_type_hints(type(mcp).run)["transport"])
        assert erlaubt, "die Signatur von run() nennt keine Transportnamen mehr"
        assert SDK_HTTP_TRANSPORT in erlaubt, (
            f"SDK_HTTP_TRANSPORT={SDK_HTTP_TRANSPORT!r}; mcp.run() nimmt nur "
            f"{erlaubt} an und wirft sonst ValueError"
        )

    def test_beide_schreibweisen_der_env_var_waehlen_den_http_transport(self, monkeypatch):
        """Die READMEs dokumentieren `streamable_http`, das SDK heisst anders.

        Beide Schreibweisen muessen den HTTP-Transport waehlen, sonst benennt
        dieser Commit eine funktionierende Deployment-Konfiguration um. Faellt
        dieser Test fuer den Unterstrich, faellt er fuer bestehende Betreiber.
        """
        for wert in ("streamable_http", "streamable-http"):
            monkeypatch.setenv("MCP_TRANSPORT", wert)
            monkeypatch.delenv("MCP_HOST", raising=False)
            monkeypatch.delenv("MCP_ALLOW_PUBLIC_BIND", raising=False)
            with patch("swiss_culture_mcp.server._run_http") as mock_http:
                main()
            assert mock_http.call_count == 1, (
                f"MCP_TRANSPORT={wert} waehlte nicht den HTTP-Transport"
            )

    def test_ein_unbekannter_transportname_faellt_auf_stdio_zurueck(self, monkeypatch):
        """Gegenprobe zur Alias-Liste: sie nimmt nicht einfach alles an.

        Ohne diese Zeile waere der Test darueber auch gruen, wenn die
        Bedingung jeden Wert als HTTP einordnete — dann waere `stdio` selbst
        HTTP.
        """
        monkeypatch.setenv("MCP_TRANSPORT", "streamablehttp")
        with patch("swiss_culture_mcp.server._run_http") as mock_http:
            with patch("swiss_culture_mcp.server.mcp.run") as mock_run:
                main()
        mock_run.assert_called_once_with(transport="stdio")
        mock_http.assert_not_called()

    def test_main_default_loopback_bind(self, monkeypatch):
        monkeypatch.setenv("MCP_TRANSPORT", "streamable_http")
        monkeypatch.delenv("MCP_HOST", raising=False)
        monkeypatch.delenv("MCP_ALLOW_PUBLIC_BIND", raising=False)
        with patch("swiss_culture_mcp.server._run_http") as mock_http:
            main()
        assert mock_http.call_args.args[0] == "127.0.0.1"

    def test_main_reicht_den_port_aus_der_umgebung_durch(self, monkeypatch):
        """Gegenprobe zum Default: 8000 steht in beiden Zweigen, ein
        weggefallenes `MCP_PORT` faellt ohne abweichenden Wert nicht auf."""
        monkeypatch.setenv("MCP_TRANSPORT", "streamable_http")
        monkeypatch.delenv("MCP_HOST", raising=False)
        monkeypatch.setenv("MCP_PORT", "9443")
        monkeypatch.delenv("MCP_ALLOW_PUBLIC_BIND", raising=False)
        with patch("swiss_culture_mcp.server._run_http") as mock_http:
            main()
        assert mock_http.call_args.args[1] == 9443

    def test_main_stdio_default(self, monkeypatch):
        monkeypatch.delenv("MCP_TRANSPORT", raising=False)
        with patch("swiss_culture_mcp.server.mcp.run") as mock_run:
            main()
            mock_run.assert_called_once_with(transport="stdio")


# ---------------------------------------------------------------------------
# Unit-Tests: Host-Allowlist + Defused-XML (SEC-004, SEC-005)
# ---------------------------------------------------------------------------


class TestSecurityHardening:
    def test_assert_host_allowed_blocks_unknown_host(self):
        import httpx as _httpx

        from swiss_culture_mcp.server import _assert_host_allowed

        with pytest.raises(_httpx.RequestError):
            _assert_host_allowed(_httpx.URL("https://evil.example.com/x"))

    def test_assert_host_allowed_passes_known_host(self):
        import httpx as _httpx

        from swiss_culture_mcp.server import _assert_host_allowed

        _assert_host_allowed(_httpx.URL("https://api3.geo.admin.ch/rest"))

    def test_defusedxml_blocks_billion_laughs(self):
        from swiss_culture_mcp.server import _parse_rss_items

        billion_laughs = """<?xml version="1.0"?>
<!DOCTYPE lolz [
  <!ENTITY lol "lol">
  <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
]>
<rss><channel><item><title>&lol2;</title></item></channel></rss>"""
        with pytest.raises(Exception):
            _parse_rss_items(billion_laughs)


# ---------------------------------------------------------------------------
# Unit-Tests: Connection-Pool (SCALE-001)
# ---------------------------------------------------------------------------


class TestConnectionPool:
    def test_http_client_is_singleton(self):
        from swiss_culture_mcp.server import _get_http_client

        c1 = _get_http_client()
        c2 = _get_http_client()
        assert c1 is c2

    def test_http_client_has_user_agent(self):
        from swiss_culture_mcp.server import _get_http_client

        c = _get_http_client()
        assert "swiss-culture-mcp" in c.headers.get("user-agent", "")


# ---------------------------------------------------------------------------
# Unit-Tests: Input-Validierung
# ---------------------------------------------------------------------------


class TestInputValidation:
    def test_isos_kanton_valid(self):
        inp = IsosKantonInput(kanton="zh")
        assert inp.kanton == "ZH"  # Uppercasing

    def test_isos_kanton_invalid(self):
        with pytest.raises(Exception):
            IsosKantonInput(kanton="XX")

    def test_isos_search_min_length(self):
        with pytest.raises(Exception):
            IsosSearchInput(query="A")  # Zu kurz

    def test_isos_search_valid(self):
        inp = IsosSearchInput(query="  Bern  ")
        assert inp.query == "Bern"  # Whitespace-Trimming

    def test_news_limit_bounds(self):
        with pytest.raises(Exception):
            NewsInput(limit=0)
        with pytest.raises(Exception):
            NewsInput(limit=51)

    def test_kantone_vollstaendig(self):
        assert len(KANTONE) == 26
        assert "ZH" in KANTONE
        assert "GE" in KANTONE
        assert "TI" in KANTONE

    def test_tradition_slug_rejects_path_traversal(self):
        with pytest.raises(Exception):
            TraditionDetailInput(slug="../../etc/passwd")

    def test_tradition_slug_rejects_uppercase(self):
        with pytest.raises(Exception):
            TraditionDetailInput(slug="Fasnacht-Basel")

    def test_tradition_slug_rejects_special_chars(self):
        with pytest.raises(Exception):
            TraditionDetailInput(slug="schwingen?injected=1")

    def test_tradition_slug_accepts_current_slug(self):
        # Echter Slug, gemessen am 7.11.2026. Bis zum Umbau der Website hiess er
        # 'alphorn--und-buechelspiel'; den doppelten Bindestrich gibt es nicht mehr.
        inp = TraditionDetailInput(slug="alphorn-und-buechelspiel")
        assert inp.slug == "alphorn-und-buechelspiel"


# ---------------------------------------------------------------------------
# Unit-Tests: Tools (mit Mocks)
# ---------------------------------------------------------------------------


class TestBakSearchIsos:
    @pytest.mark.asyncio
    async def test_search_returns_results(self):
        with patch("swiss_culture_mcp.server._get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MOCK_ISOS_RESULTS
            result = await bak_search_isos(IsosSearchInput(query="Zürich"))
            data = json.loads(result)
            assert data["count"] >= 1
            assert data["results"][0]["name"] == "Zürich"
            assert data["results"][0]["kantone"] == ["ZH"]

    @pytest.mark.asyncio
    async def test_search_deduplication(self):
        # Duplikate in den Resultaten
        dup_results = {
            "results": [
                MOCK_ISOS_RESULTS["results"][0],
                MOCK_ISOS_RESULTS["results"][0],  # Duplikat
            ]
        }
        with patch("swiss_culture_mcp.server._get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = dup_results
            result = await bak_search_isos(IsosSearchInput(query="Zürich"))
            data = json.loads(result)
            assert data["count"] == 1  # Duplikat entfernt

    @pytest.mark.asyncio
    async def test_search_limit_respected(self):
        with patch("swiss_culture_mcp.server._get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MOCK_ISOS_RESULTS
            result = await bak_search_isos(IsosSearchInput(query="Zürich", limit=1))
            data = json.loads(result)
            assert data["count"] <= 1

    @pytest.mark.asyncio
    async def test_search_error_handling(self):
        import httpx

        with patch("swiss_culture_mcp.server._get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.TimeoutException("timeout")
            result = await bak_search_isos(IsosSearchInput(query="Bern"))
            assert "Zeitüberschreitung" in result


class TestBakIsosByKanton:
    @pytest.mark.asyncio
    async def test_kanton_results_sorted(self):
        with patch("swiss_culture_mcp.server._get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MOCK_ISOS_RESULTS
            result = await bak_isos_by_kanton(IsosKantonInput(kanton="ZH"))
            data = json.loads(result)
            assert data["kanton"] == "ZH"
            assert data["kanton_name"] == "Zürich"
            assert isinstance(data["results"], list)

    @pytest.mark.asyncio
    async def test_kanton_be(self):
        with patch("swiss_culture_mcp.server._get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"results": []}
            result = await bak_isos_by_kanton(IsosKantonInput(kanton="BE"))
            data = json.loads(result)
            assert data["kanton_name"] == "Bern"


class TestBakGetIsosDetail:
    @pytest.mark.asyncio
    async def test_detail_with_coordinates(self):
        with patch("swiss_culture_mcp.server._get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MOCK_ISOS_FEATURE
            result = await bak_get_isos_detail(IsosDetailInput(feature_id="1148957451775839307"))
            data = json.loads(result)
            assert data["name"] == "Zürich"
            assert data["koordinaten_lv03"]["x"] == 683350.0
            assert "LV03" in data["koordinaten_lv03"]["beschreibung"]


class TestBakGetNews:
    @pytest.mark.asyncio
    async def test_news_returns_items(self):
        with patch("swiss_culture_mcp.server._get_text", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MOCK_RSS_XML
            result = await bak_get_news(NewsInput(limit=10))
            data = json.loads(result)
            assert data["count"] == 2
            assert "Grand Prix" in data["items"][0]["title"]

    @pytest.mark.asyncio
    async def test_news_keyword_filter(self):
        with patch("swiss_culture_mcp.server._get_text", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MOCK_RSS_XML
            result = await bak_get_news(NewsInput(limit=10, keyword="ISOS"))
            data = json.loads(result)
            assert data["count"] == 1
            assert "ISOS" in data["items"][0]["title"]

    @pytest.mark.asyncio
    async def test_news_keyword_no_match(self):
        with patch("swiss_culture_mcp.server._get_text", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MOCK_RSS_XML
            result = await bak_get_news(NewsInput(keyword="XYZ_NICHT_VORHANDEN"))
            data = json.loads(result)
            assert data["count"] == 0


class TestBakGetKulturpreise:
    @pytest.mark.asyncio
    async def test_returns_preisuebersicht(self):
        with patch("swiss_culture_mcp.server._get_text", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MOCK_RSS_XML
            result = await bak_get_kulturpreise(KulturpreiseInput())
            data = json.loads(result)
            assert len(data["preisuebersicht"]) >= 6
            assert "Schweizer Filmpreis" in data["preisuebersicht"][0]["name"]

    @pytest.mark.asyncio
    async def test_sparten_filter_design(self):
        with patch("swiss_culture_mcp.server._get_text", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MOCK_RSS_XML
            result = await bak_get_kulturpreise(KulturpreiseInput(sparte="Design"))
            data = json.loads(result)
            assert all(
                "design" in p["name"].lower() or "design" in p["sparte"].lower()
                for p in data["preisuebersicht"]
            )

    @pytest.mark.asyncio
    async def test_fallback_on_rss_error(self):
        import httpx

        with patch("swiss_culture_mcp.server._get_text", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.ConnectError("no connection")
            result = await bak_get_kulturpreise(KulturpreiseInput())
            data = json.loads(result)
            # Preisuebersicht trotzdem vorhanden
            assert len(data["preisuebersicht"]) > 0
            assert "fehler_rss" in data


class TestBakGetOpendata:
    @pytest.mark.asyncio
    async def test_returns_datasets(self):
        with patch("swiss_culture_mcp.server._get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MOCK_CKAN_RESPONSE
            result = await bak_get_opendata(OpendataInput())
            data = json.loads(result)
            assert data["count"] == 1
            assert "ISOS" in data["datasets"][0]["title"]

    @pytest.mark.asyncio
    async def test_query_parameter_passed(self):
        with patch("swiss_culture_mcp.server._get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"result": {"count": 0, "results": []}}
            result = await bak_get_opendata(OpendataInput(query="ISOS"))
            data = json.loads(result)
            assert data["query"] == "ISOS"
            # Verify parameter was passed correctly
            call_args = mock_get.call_args
            assert "q" in call_args[1]["params"] or "q" in call_args[0][1]


# Die Werkzeuge der lebendigen Traditionen stehen in `tests/test_traditionen.py`,
# gegen aufgezeichnete Antworten der Quelle. Hier standen bis zum 7.11.2026
# Tests gegen zwei von Hand geschriebene HTML-Schnipsel — gruen, waehrend beide
# Werkzeuge produktiv scheiterten.


# ---------------------------------------------------------------------------
# Integrationstests (Live)
# ---------------------------------------------------------------------------


@pytest.fixture
def run_live(request):
    return request.config.getoption("--run-live")


# Anhang-Nummer -> API-Nummer, je Kanton, fuer den VISOS-Abgleich. Am
# 3.11.2026 gemessen: Wilen bei Neunforn steht im Anhang unter TG (3705) und
# unter ZH (5782); die API fuehrt nur 3705, mit `kantone: ['TG', 'ZH']`. Faellt
# der Eintrag im Anhang weg, meldet der Live-Test das, statt die Ausnahme
# still weiterzutragen.
_ANHANG_ZU_API = {("ZH", "5782"): "3705"}

# Bis zum 7.11.2026 fragte dieser Test einen Kanton nach einer Stoerung selbst ein
# zweites Mal (`_kanton_abfragen`). Das tut jetzt der Server fuer alle Nutzer
# (`http_client._abrufen`, geprueft in `tests/test_wiederholung.py`); eine
# zweite Schicht hier ergaebe bis zu vier Versuche je Kanton und pruefte nicht
# mehr, was die Nutzer erleben.


@pytest.mark.live
class TestLiveApis:
    @pytest.mark.asyncio
    async def test_live_isos_search_zuerich(self, run_live):
        if not run_live:
            pytest.skip("Live-Test übersprungen (--run-live nicht gesetzt)")
        result = await bak_search_isos(IsosSearchInput(query="Zürich"))
        data = json.loads(result)
        assert data["count"] >= 1
        assert any(r["name"] == "Zürich" for r in data["results"])

    @pytest.mark.asyncio
    async def test_live_isos_deckt_sich_mit_der_gueltigen_visos(self, run_live):
        """Die API gegen die VISOS, die heute gilt — Sollwerte live von Fedlex.

        Massstab ist Anhang 1 der VISOS (SR 451.12) in der Fassung, die am
        Stichtag gilt. `scripts/visos_anhang.py` liest sie zur Laufzeit; offline
        geprueft wird der Leser in `tests/test_visos_anhang.py`.

        Bis zum 3.11.2026 standen hier feste Zahlen, ZH 73 und GR 105 aus der
        Fassung vom 1.6.2026. Am 1.11.2026 trat eine Revision in Kraft (AS 2026
        488: Hinterrhein, Jenaz, Vals-Platz neu, Roveredo gestrichen), die API
        zog nach, und der geplante Lauf vom 2.11.2026 wurde rot — auf demselben
        Commit, der eine Woche zuvor gruen war. Der Server lieferte die
        gueltige Zahl; veraltet war der Test. Feste Zahlen fragen «wurde die
        VISOS revidiert?», und das ist kein Vertrag mit der Quelle. Dieser Test
        fragt nur noch: «Liefert der Server, was die gueltige Verordnung
        festsetzt?»

        Verglichen wird je Kanton zweierlei, und beides braucht es:

        * die **Nummern** — eine Revision, die ein Ortsbild streicht und ein
          anderes aufnimmt, laesst die Anzahl gleich;
        * `total_in_kanton` — gegen den alten Fehler, Features statt Ortsbilder
          zu zaehlen (GR 507 statt 105). Als Menge fallen doppelte Nummern
          zusammen; nur die Anzahl sieht ihn.

        Rot heisst: API und gueltige Verordnung weichen ab, die Meldung nennt
        Kanton, Nummern und Fassung. Kurz nach einer Revision kann das die
        Nachfuehrung bei geo.admin sein; ob die API noch die Vorfassung
        liefert, zeigt die Fedlex-Abfrage in `CLAUDE.md`. Faellt Fedlex selbst
        aus, nennt die Meldung `FedlexLeseError`.
        """
        if not run_live:
            pytest.skip("Live-Test übersprungen")
        stichtag = datetime.now(ZoneInfo("Europe/Zurich")).date()
        with httpx.Client(
            timeout=60.0,
            follow_redirects=True,
            headers={"User-Agent": "swiss-culture-mcp-live-tests"},
        ) as client:
            fassung, eintraege = visos_anhang.abrufen(client, stichtag)

        im_anhang = {(e.kanton, e.nummer) for e in eintraege}
        namen = {e.nummer: e.objekt for e in eintraege}
        soll: dict[str, set[str]] = {}
        for kanton, nummer in im_anhang:
            soll.setdefault(kanton, set()).add(_ANHANG_ZU_API.get((kanton, nummer), nummer))
        assert set(soll) == set(KANTONE), (
            f"Anhang 1 der Fassung {fassung.kennung} nennt {sorted(soll)} statt der "
            "26 Kantone — erst den Leser gegen die Quelle pruefen."
        )

        befunde = [
            f"Ausnahme {k} -> {v} hat kein Gegenstueck mehr im Anhang; die Liste "
            "_ANHANG_ZU_API gehoert nachgefuehrt."
            for k, v in _ANHANG_ZU_API.items()
            if k not in im_anhang
        ]
        for kanton in sorted(soll):
            antwort = await bak_isos_by_kanton(IsosKantonInput(kanton=kanton, limit=500))
            # Ein Fehlertext des Tools ist ein Befund mit Namen, kein
            # JSONDecodeError: Der erste Lauf dieses Tests am 3.11.2026 war rot,
            # 18 s langsamer als sonst, und seine Ursache liess sich hinterher
            # nicht mehr lesen. Der zweite solche Lauf nannte sie dank dieser
            # Zeile: SO, Zeitueberschreitung nach 20 s. Steht sie hier, hat
            # auch der zweite Versuch des Servers nicht gereicht.
            try:
                data = json.loads(antwort)
            except json.JSONDecodeError:
                befunde.append(f"{kanton}: Server meldet {antwort[:200]!r}")
                continue
            ist = {str(r["isos_nummer"]) for r in data["results"]}
            api_namen = {str(r["isos_nummer"]): r["name"] for r in data["results"]}
            if data["total_in_kanton"] != len(soll[kanton]):
                befunde.append(
                    f"{kanton}: total_in_kanton {data['total_in_kanton']} statt {len(soll[kanton])}"
                )
            nur_anhang = sorted(soll[kanton] - ist, key=int)
            nur_api = sorted(ist - soll[kanton], key=int)
            if nur_anhang:
                befunde.append(
                    f"{kanton}: nur im Anhang "
                    + ", ".join(f"{n} {namen.get(n, '?')}" for n in nur_anhang)
                )
            if nur_api:
                befunde.append(
                    f"{kanton}: nur in der API " + ", ".join(f"{n} {api_namen[n]}" for n in nur_api)
                )
        assert not befunde, (
            f"API und VISOS-Fassung {fassung.kennung} (gueltig ab {fassung.ab:%d.%m.%Y}, "
            f"{fassung.eli}) weichen ab:\n" + "\n".join(befunde)
        )

    @pytest.mark.asyncio
    async def test_live_traditionen(self, run_live):
        """Liste und Detail gegen lebendige-traditionen.ch, an bekannten Eintraegen.

        Die Website wurde zwischen dem 16.8. und dem 3.11.2026 umgebaut, und
        keiner der damaligen Live-Tests fragte sie ab: Beide Werkzeuge waren
        kaputt, und der Wochenlauf blieb gruen. Geprueft wird an gezielt
        gewaehlten Eintraegen, nicht am ersten Treffer — die Basler Fasnacht
        (ein Kanton, UNESCO-Eintrag) und das Alphorn- und Buechelspiel
        (ueberregional). Die Gesamtzahl ist eine Untergrenze: Das Inventar
        waechst selten, aber es waechst (2012: 167, 2017: 199, heute 228).
        """
        if not run_live:
            pytest.skip("Live-Test übersprungen")
        liste_text = await bak_list_traditions(TraditionListInput())
        assert liste_text.startswith("{"), liste_text
        liste = json.loads(liste_text)
        assert liste["gesamt"] >= 228, liste["gesamt"]
        assert "warnung" not in liste, liste["warnung"]
        eintraege = {e["slug"]: e for e in liste["traditions"]}
        assert eintraege["basler-fasnacht"]["unesco_repraesentative_liste"] is True

        fasnacht = json.loads(
            await bak_get_tradition_detail(TraditionDetailInput(slug="basler-fasnacht"))
        )
        assert fasnacht["fehlende_abschnitte"] == []
        assert [k["kuerzel"] for k in fasnacht["kantone"]] == ["BS"]
        assert fasnacht["beschreibung"] and fasnacht["kategorien"]
        assert fasnacht["detailbeschreibung_pdf"]

        alphorn = json.loads(
            await bak_get_tradition_detail(TraditionDetailInput(slug="alphorn-und-buechelspiel"))
        )
        assert alphorn["fehlende_abschnitte"] == []
        assert alphorn["kantone"] == [] and alphorn["ueberregional"] is True

    @pytest.mark.asyncio
    async def test_live_bak_news(self, run_live):
        if not run_live:
            pytest.skip("Live-Test übersprungen")
        result = await bak_get_news(NewsInput(limit=5))
        data = json.loads(result)
        assert data["count"] >= 1

    @pytest.mark.asyncio
    async def test_live_opendata(self, run_live):
        if not run_live:
            pytest.skip("Live-Test übersprungen")
        result = await bak_get_opendata(OpendataInput())
        data = json.loads(result)
        assert data["total"] >= 3  # Mindestens 3 BAK-Datensätze auf opendata.swiss
