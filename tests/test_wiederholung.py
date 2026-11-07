"""Ein zweiter Versuch bei voruebergehenden Stoerungen — und nur dann.

`http_client._abrufen` fragt nach einer Zeitueberschreitung, einem
Netzwerkfehler, einer abgebrochenen Verbindung oder HTTP 502/503/504 genau ein
zweites Mal. Anlass: `api3.geo.admin.ch` hatte am 3.11.2026 Ausreisser von
30,5 s, der Client gibt nach 20 s auf, und das Werkzeug meldete
«Zeitueberschreitung», wo eine zweite Anfrage in unter einer Sekunde antwortete.

Ohne Netz: Die Gegenseite ist ein `httpx.MockTransport`, der mitzaehlt. Die
Pause ist der Modul-Alias `http_client._pause`, nicht `asyncio.sleep` — dieses
zu ersetzen, entschaerfte die Mechanik im ganzen Prozess (CLAUDE.md, «Tests»).
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import httpx
import pytest

from swiss_culture_mcp import http_client
from swiss_culture_mcp.models import IsosKantonInput
from swiss_culture_mcp.server import bak_isos_by_kanton

GEO = "https://api3.geo.admin.ch/rest/services/all/MapServer/find"


class _Gegenseite:
    """Spielt der Reihe nach ab, was `antworten` vorgibt, und zaehlt mit."""

    def __init__(self, antworten):
        self.antworten = list(antworten)
        self.anfragen: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.anfragen.append(request)
        naechste = self.antworten.pop(0) if len(self.antworten) > 1 else self.antworten[0]
        if isinstance(naechste, type) and issubclass(naechste, Exception):
            raise naechste("simuliert", request=request)
        if callable(naechste):
            return naechste(request)
        return naechste


@pytest.fixture
def gegenseite(monkeypatch):
    """Setzt den modulweiten Client auf eine Gegenseite und die Pause auf einen Zaehler."""
    pause = AsyncMock()
    monkeypatch.setattr(http_client, "_pause", pause)

    def bauen(*antworten):
        seite = _Gegenseite(antworten)
        client = httpx.AsyncClient(transport=httpx.MockTransport(seite), follow_redirects=True)
        monkeypatch.setattr(http_client, "_http_client", client)
        return seite, pause

    return bauen


def _ok(daten=None) -> httpx.Response:
    return httpx.Response(200, json=daten if daten is not None else {"ok": True})


class TestStoerungenWerdenEinmalWiederholt:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "fehler",
        [
            httpx.ReadTimeout,
            httpx.ConnectTimeout,
            httpx.ConnectError,
            httpx.ReadError,
            httpx.RemoteProtocolError,
        ],
    )
    async def test_nach_einer_stoerung_kommt_die_antwort(self, gegenseite, fehler):
        seite, pause = gegenseite(fehler, _ok())
        assert await http_client._get(GEO) == {"ok": True}
        assert len(seite.anfragen) == 2
        pause.assert_awaited_once_with(http_client.PAUSE_S)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status", [502, 503, 504])
    async def test_nach_einem_gateway_fehler_kommt_die_antwort(self, gegenseite, status):
        seite, pause = gegenseite(httpx.Response(status), _ok())
        assert await http_client._get(GEO) == {"ok": True}
        assert len(seite.anfragen) == 2
        pause.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_auch_der_textabruf_wiederholt(self, gegenseite):
        """`_get_text` (RSS) laeuft ueber denselben Weg wie `_get`."""
        seite, _ = gegenseite(httpx.ReadTimeout, httpx.Response(200, text="<rss/>"))
        assert await http_client._get_text(GEO) == "<rss/>"
        assert len(seite.anfragen) == 2

    @pytest.mark.asyncio
    async def test_zwei_stoerungen_bleiben_eine_stoerung(self, gegenseite):
        seite, pause = gegenseite(httpx.ReadTimeout)
        with pytest.raises(httpx.ReadTimeout):
            await http_client._get(GEO)
        assert len(seite.anfragen) == 2
        pause.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_zweimal_503_wird_als_503_gemeldet(self, gegenseite):
        seite, _ = gegenseite(httpx.Response(503))
        with pytest.raises(httpx.HTTPStatusError) as exc:
            await http_client._get(GEO)
        assert exc.value.response.status_code == 503
        assert len(seite.anfragen) == 2


class TestAntwortenWerdenNichtWiederholt:
    @pytest.mark.asyncio
    async def test_ein_erfolg_braucht_keinen_zweiten_versuch(self, gegenseite):
        seite, pause = gegenseite(_ok())
        assert await http_client._get(GEO) == {"ok": True}
        assert len(seite.anfragen) == 1
        pause.assert_not_awaited()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status", [400, 403, 404, 429, 500])
    async def test_eine_absage_wird_nicht_wiederholt(self, gegenseite, status):
        seite, pause = gegenseite(httpx.Response(status), _ok())
        with pytest.raises(httpx.HTTPStatusError):
            await http_client._get(GEO)
        assert len(seite.anfragen) == 1
        pause.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_ein_verbotener_zielhost_wird_nicht_wiederholt(self, gegenseite):
        """Die Allowlist-Pruefung ist eine Antwort, keine Stoerung."""

        def umleiten(request):
            if request.url.host == "api3.geo.admin.ch":
                return httpx.Response(302, headers={"Location": "https://boese.example/"})
            return _ok()

        seite, pause = gegenseite(umleiten)
        with pytest.raises(httpx.RequestError, match="Host nicht erlaubt"):
            await http_client._get(GEO)
        assert [r.url.host for r in seite.anfragen] == ["api3.geo.admin.ch", "boese.example"]
        pause.assert_not_awaited()


class TestWerkzeug:
    @pytest.mark.asyncio
    async def test_ein_ausreisser_wird_zur_antwort_statt_zur_fehlermeldung(self, gegenseite):
        """Was die Nutzer sehen: Daten, nicht «Zeitueberschreitung»."""
        treffer = {
            "results": [
                {"id": "1", "attributes": {"nummer": 3001, "name": "Solothurn", "kantone": ["SO"]}}
            ]
        }
        seite, _ = gegenseite(httpx.ReadTimeout, _ok(treffer))
        antwort = await bak_isos_by_kanton(IsosKantonInput(kanton="SO"))
        assert not antwort.startswith("Fehler"), antwort
        assert json.loads(antwort)["total_in_kanton"] == 1
        assert len(seite.anfragen) == 2
