"""
Tests für swiss-culture-mcp.

Einheitstests mit Mocks (immer) und Live-Integrationstests (mit --run-live).
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from swiss_culture_mcp.server import (
    KANTONE,
    IsosDetailInput,
    IsosKantonInput,
    IsosSearchInput,
    NewsInput,
    KulturpreiseInput,
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
    bak_isos_by_kategorie,
    bak_isos_statistics,
    bak_list_traditions,
    bak_search_isos,
)

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
                "description": {"de": "Bundesinventar der schützenswerten Ortsbilder der Schweiz von nationaler Bedeutung."},
                "resources": [
                    {"format": "WMS", "url": "https://wms.geo.admin.ch/", "name": {"de": "WMS-Dienst"}},
                    {"format": "API", "url": "https://api3.geo.admin.ch/", "name": {"de": "REST API"}},
                ],
                "metadata_modified": "2024-01-15",
                "organization": {"name": "bundesamt-fur-kultur-bak"},
            }
        ],
    }
}

MOCK_TRADITION_HTML = """<html>
<head>
<title>Alphorn- und Büchelspiel | Lebendige Traditionen</title>
<meta name="description" content="Das Alphorn ist ein traditionelles Blasinstrument der Schweizer Alpen.">
</head>
<body>
<p>Das Alphorn ist ein langes Holzblasinstrument, das seit Jahrhunderten in den Schweizer Alpen gespielt wird.</p>
<p>Die Tradition ist besonders im Kanton Bern, Graubünden und Wallis verbreitet.</p>
</body>
</html>"""

MOCK_TRADITION_LIST_HTML = """<html><body>
<a href="/tradition/de/home/traditionen/alphorn--und-buechelspiel.html">Alphorn</a>
<a href="/tradition/de/home/traditionen/schwingen.html">Schwingen</a>
<a href="/tradition/de/home/traditionen/fasnacht-basel.html">Basler Fasnacht</a>
<a href="/tradition/de/home/traditionen/alphorn--und-buechelspiel.html">Alphorn (Duplikat)</a>
</body></html>"""

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
            assert all("design" in p["name"].lower() or "design" in p["sparte"].lower()
                       for p in data["preisuebersicht"])

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


class TestBakListTraditions:
    @pytest.mark.asyncio
    async def test_list_returns_traditions(self):
        with patch("swiss_culture_mcp.server._get_text", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MOCK_TRADITION_LIST_HTML
            result = await bak_list_traditions(TraditionListInput())
            data = json.loads(result)
            assert data["count"] == 3  # 3 unique slugs
            assert any("alphorn" in t["slug"] for t in data["traditions"])

    @pytest.mark.asyncio
    async def test_list_deduplication(self):
        with patch("swiss_culture_mcp.server._get_text", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MOCK_TRADITION_LIST_HTML
            result = await bak_list_traditions(TraditionListInput())
            data = json.loads(result)
            slugs = [t["slug"] for t in data["traditions"]]
            assert len(slugs) == len(set(slugs))  # Keine Duplikate

    @pytest.mark.asyncio
    async def test_list_buchstabe_filter(self):
        with patch("swiss_culture_mcp.server._get_text", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MOCK_TRADITION_LIST_HTML
            result = await bak_list_traditions(TraditionListInput(buchstabe="A"))
            data = json.loads(result)
            assert all(t["name_aus_slug"].upper().startswith("A") for t in data["traditions"])


class TestBakGetTraditionDetail:
    @pytest.mark.asyncio
    async def test_detail_extracts_title(self):
        with patch("swiss_culture_mcp.server._get_text", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MOCK_TRADITION_HTML
            result = await bak_get_tradition_detail(
                TraditionDetailInput(slug="alphorn--und-buechelspiel")
            )
            data = json.loads(result)
            assert "Alphorn" in data["titel"]
            assert data["slug"] == "alphorn--und-buechelspiel"

    @pytest.mark.asyncio
    async def test_detail_extracts_description(self):
        with patch("swiss_culture_mcp.server._get_text", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MOCK_TRADITION_HTML
            result = await bak_get_tradition_detail(
                TraditionDetailInput(slug="alphorn--und-buechelspiel")
            )
            data = json.loads(result)
            assert "Blasinstrument" in data["meta_beschreibung"]

    @pytest.mark.asyncio
    async def test_detail_kantone_detection(self):
        with patch("swiss_culture_mcp.server._get_text", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MOCK_TRADITION_HTML
            result = await bak_get_tradition_detail(
                TraditionDetailInput(slug="alphorn--und-buechelspiel")
            )
            data = json.loads(result)
            assert "Bern" in data["erwaehnte_kantone"]


# ---------------------------------------------------------------------------
# Integrationstests (Live)
# ---------------------------------------------------------------------------

@pytest.fixture
def run_live(request):
    return request.config.getoption("--run-live")


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
    async def test_live_isos_by_kanton_zh(self, run_live):
        if not run_live:
            pytest.skip("Live-Test übersprungen")
        result = await bak_isos_by_kanton(IsosKantonInput(kanton="ZH"))
        data = json.loads(result)
        assert data["total_in_kanton"] > 100  # ZH hat viele ISOS-Objekte

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
