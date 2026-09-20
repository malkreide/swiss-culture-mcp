"""Spec `2026-07-28` am Draht gemessen, nicht aus SDK-Konstanten geschlossen.

`tests/test_protocol_version.py` pinnt die beiden Revisionen gegen die
Konstanten des SDK und benannte dabei seine eigene Schwaeche: «dieses Repo baut
keine ASGI-App, durch die sich ein `initialize` schicken liesse». Diese Datei
baut sie. Sie ist der gemessene Teil, der dort fehlte.

Warum das nicht dasselbe ist wie ein `Client(mcp)`-Test: Die moderne Aera
existiert nur auf dem HTTP-Einstieg. `StreamableHTTPSessionManager` routet
einen Request, dessen `mcp-protocol-version`-Header keine
Handshake-Revision nennt, auf den Pro-Request-Pfad
(`mcp/server/_streamable_http_modern.py`); stdio und die In-Process-Clients
kennen ausschliesslich den `initialize`-Handshake. Wer Spec `2026-07-28` ueber
einen In-Process-Client prueft, prueft die Handler und nicht die Aera.

Genau daran lag der Befund, der diese Datei ausgeloest hat: `main()` rief
`mcp.run(transport="streamable_http")` — mit Unterstrich, wo das SDK
`streamable-http` verlangt. Der HTTP-Transport brach beim Start mit
`ValueError` ab, der Server sprach die Spec also gar nicht, und alles blieb
gruen: die Transport-Tests patchten `mcp.run` und hielten den Tippfehler gegen
sich selbst.

Der Envelope wird hier von Hand gebaut, weil es ums Drahtformat geht. Was eine
moderne Anfrage mitbringen muss, ist gemessen und nicht angenommen — jede
dieser Zusicherungen hat eine Gegenprobe weiter unten:

* Header `mcp-protocol-version: 2026-07-28` — er entscheidet das Routing.
* Header `mcp-method`, deckungsgleich mit `method` im Koerper; fehlt er,
  antwortet der Server `-32020`.
* Bei den namenstragenden Methoden zusaetzlich `mcp-name`. WELCHES Feld er
  spiegelt, haengt an der Methode — `name` bei `tools/call` und `prompts/get`,
  `uri` bei `resources/read`. Geraten war hier `name` fuer alle drei, was
  `resources/read` mit `-32020` abwies. Die Zuordnung kommt jetzt aus
  `NAME_BEARING_METHODS` des SDK und nicht aus einer zweiten Tabelle, die
  auseinanderlaufen koennte.
* `params._meta` mit `protocolVersion` und `clientCapabilities`; fehlt das,
  antwortet der Server `-32602`.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import AsyncIterator, Mapping
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from mcp.server.caching import CACHEABLE_METHODS
from mcp.server.mcpserver import MCPServer
from mcp.shared.inbound import NAME_BEARING_METHODS

# `test_protocol_version` steht als Modul und nicht als Paketpfad da: `tests/`
# ist kein Paket (kein `__init__.py`), pytest legt das Verzeichnis selbst in
# den Pfad. Die Revisionen kommen aus dem Pin-Modul und nicht als zweite Kopie
# hierher — eine Kopie koennte driften, und dann bestaetigte die Messung etwas
# anderes als der Pin festhaelt.
from test_protocol_version import (
    DOCUMENTED_HANDSHAKE_VERSION,
    DOCUMENTED_MODERN_VERSION,
)

from swiss_culture_mcp import __version__
from swiss_culture_mcp.constants import PROJECT_URL
from swiss_culture_mcp.server import LIST_CACHE_TTL_MS, mcp

# `_assert_host_allowed()` ist die Allowlist FUER AUSGEHENDE Aufrufe; hier
# greift die eingehende Seite: `TransportSecurityMiddleware` prueft den
# `Host`-Header und antwortet sonst 421. `httpx`' Standard-`base_url`
# `http://testserver` faellt darunter — gemessen, nicht geraten. Eine
# Loopback-Adresse ist erlaubt, weil `streamable_http_app()` sie im
# Default-Setting fuehrt.
BASE_URL = "http://127.0.0.1:8000"
MCP_PATH = "/mcp"

SERVER_INFO_KEY = "io.modelcontextprotocol/serverInfo"
PROTOCOL_VERSION_KEY = "io.modelcontextprotocol/protocolVersion"
CLIENT_INFO_KEY = "io.modelcontextprotocol/clientInfo"
CLIENT_CAPABILITIES_KEY = "io.modelcontextprotocol/clientCapabilities"

# Parameter, den die gehinweisten Methoden zum Aufruf brauchen. `server/discover`
# und die drei Listen nehmen keinen.
_NO_ARGS: dict[str, Any] = {}


def envelope(version: str = DOCUMENTED_MODERN_VERSION) -> dict[str, Any]:
    """Der Pro-Request-Envelope, den die moderne Aera in `params._meta` erwartet."""
    return {
        PROTOCOL_VERSION_KEY: version,
        CLIENT_INFO_KEY: {"name": "pytest-drahtprobe", "version": "0"},
        CLIENT_CAPABILITIES_KEY: {},
    }


@contextlib.asynccontextmanager
async def _asgi_lifespan(app: Any) -> AsyncIterator[None]:
    """Den ASGI-Lifespan der App fahren.

    Ohne ihn ist die Task-Group des Session-Managers nicht gesetzt und JEDE
    Anfrage endet in `RuntimeError: Task group is not initialized` — also nicht
    in einer Protokoll-Aussage, sondern in einem Test, der etwas anderes
    gemessen haette als er behauptet. `httpx.ASGITransport` fasst den Lifespan
    nicht an, deshalb steht er hier von Hand.
    """
    inbound: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    outbound: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    task = asyncio.create_task(
        app({"type": "lifespan", "asgi": {"version": "3.0"}}, inbound.get, outbound.put)
    )
    await inbound.put({"type": "lifespan.startup"})
    started = await outbound.get()
    assert started["type"] == "lifespan.startup.complete", started
    try:
        yield
    finally:
        await inbound.put({"type": "lifespan.shutdown"})
        with contextlib.suppress(Exception):
            await asyncio.wait_for(task, timeout=5)


@contextlib.asynccontextmanager
async def draht(server: MCPServer[Any] | None = None) -> AsyncIterator[httpx.AsyncClient]:
    """Ein HTTP-Client auf die echte ASGI-App dieses Servers."""
    app = (server or mcp).streamable_http_app()
    async with _asgi_lifespan(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=BASE_URL
        ) as client:
            yield client


async def modern(
    client: httpx.AsyncClient,
    method: str,
    params: Mapping[str, Any] | None = None,
    *,
    version: str = DOCUMENTED_MODERN_VERSION,
    header_version: str | None = None,
    drop_method_header: bool = False,
    with_envelope: bool = True,
) -> httpx.Response:
    """Eine Anfrage in der modernen Aera abschicken."""
    body_params: dict[str, Any] = dict(params or {})
    if with_envelope:
        body_params["_meta"] = envelope(version)
    headers = {
        "mcp-protocol-version": header_version or version,
        "accept": "application/json, text/event-stream",
        "content-type": "application/json",
        "mcp-method": method,
    }
    name_feld = NAME_BEARING_METHODS.get(method)
    if name_feld is not None and name_feld in body_params:
        headers["mcp-name"] = str(body_params[name_feld])
    if drop_method_header:
        del headers["mcp-method"]
    return await client.post(
        MCP_PATH,
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": body_params},
        headers=headers,
    )


async def handshake(client: httpx.AsyncClient, requested: str) -> dict[str, Any]:
    """Einen `initialize`-Handshake der Legacy-Aera fahren und das Resultat lesen.

    Die Antwort kommt als SSE-Rahmen (`event: message` / `data: {...}`), nicht
    als nackter JSON-Koerper — das ist die Drahtform dieses Transports und der
    Grund, warum hier geparst statt `r.json()` gerufen wird.
    """
    response = await client.post(
        MCP_PATH,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": requested,
                "capabilities": {},
                "clientInfo": {"name": "pytest-drahtprobe", "version": "0"},
            },
        },
        headers={
            "accept": "application/json, text/event-stream",
            "content-type": "application/json",
        },
    )
    assert response.status_code == 200, response.text
    for line in response.text.splitlines():
        if line.startswith("data: "):
            return json.loads(line.removeprefix("data: "))
    raise AssertionError(f"kein SSE-data-Rahmen in der Antwort: {response.text!r}")


# ---------------------------------------------------------------------------
# Die Aera antwortet ueberhaupt
# ---------------------------------------------------------------------------


async def test_eine_moderne_anfrage_wird_beantwortet() -> None:
    """Die lasttragende Zusicherung dieser Datei.

    Sie faellt, sobald der Server die moderne Aera nicht mehr bedient — egal
    ob der Transport nicht startet, das Routing sich aendert oder der Envelope
    abgewiesen wird.
    """
    async with draht() as client:
        response = await modern(client, "tools/list")

    assert response.status_code == 200, response.text
    result = response.json()["result"]
    assert result["resultType"] == "complete"
    assert len(result["tools"]) == 10, "die 10 Werkzeuge werden beim Import registriert"


def test_der_transportname_ist_einer_den_das_sdk_annimmt() -> None:
    """Der Befund, der diese Datei ausgeloest hat — an der Quelle statt am Mock.

    `mcp.run()` prueft den Namen gegen ein `Literal` und wirft sonst
    `ValueError`. Hier wird er wirklich uebergeben; ein Mock haette auch
    `streamable_http` angenommen, und genau das tat er ein Jahr lang.

    Der Lauf wird kurz vor dem Binden abgebrochen: die Pruefung des Namens
    liegt VOR `anyio.run(...)`, ein Sentinel aus dem Handler reicht deshalb als
    Beleg, dass der Name durchkam. Ohne diesen Abbruch wuerde der Test einen
    Port belegen und nie enden.

    Synchron und nicht `async`: `mcp.run()` ruft selbst `anyio.run(...)` und
    endet aus einem laufenden Loop heraus in `RuntimeError: Already running
    asyncio in this thread` — eine Meldung, die nichts ueber den
    Transportnamen sagt und den Test gruen wie rot bedeutungslos macht.
    """
    from swiss_culture_mcp.server import SDK_HTTP_TRANSPORT

    sentinel = RuntimeError("bis hierher und nicht weiter")

    async def abbrechen(**kwargs: Any) -> None:
        raise sentinel

    with patch.object(mcp, "run_streamable_http_async", abbrechen):
        with pytest.raises(RuntimeError) as erhoben:
            mcp.run(transport=SDK_HTTP_TRANSPORT, host="127.0.0.1", port=0)

    assert erhoben.value is sentinel, (
        "der Transportname kam nicht bis zum Handler durch — bei einem vom SDK "
        "abgewiesenen Namen steht hier ein ValueError"
    )


def test_ein_falscher_transportname_wird_vom_sdk_abgewiesen() -> None:
    """Gegenprobe zum Test darueber: zeigt, dass er etwas pruefen KANN.

    Ohne diese Zeile liesse sich der Test oben nicht von einem lesen, der
    jeden Namen durchwinkt. Der Unterstrich ist der konkrete Tippfehler, der
    im Auslieferungspfad stand.
    """
    with pytest.raises(ValueError, match="Unknown transport"):
        mcp.run(transport="streamable_http", host="127.0.0.1", port=0)  # type: ignore[call-overload]


# ---------------------------------------------------------------------------
# Was die Aera von einer Anfrage verlangt
# ---------------------------------------------------------------------------


async def test_ohne_envelope_weist_der_server_die_anfrage_ab() -> None:
    """Gegenprobe zum Envelope: er ist Pflicht, nicht Zierde.

    Bleibt diese Antwort eines Tages 200, baut der Test oben seinen Envelope
    umsonst und wuerde die Aera auch dann noch gruen melden, wenn sie gar
    nicht mehr geprueft wird.
    """
    async with draht() as client:
        response = await modern(client, "tools/list", with_envelope=False)

    assert response.status_code == 400, response.text
    assert response.json()["error"]["code"] == -32602


async def test_ohne_den_method_header_weist_der_server_die_anfrage_ab() -> None:
    """Zweite Gegenprobe: auch der Header traegt die Anfrage, nicht nur der Koerper."""
    async with draht() as client:
        response = await modern(client, "tools/list", drop_method_header=True)

    assert response.status_code == 400, response.text
    assert response.json()["error"]["code"] == -32020


async def test_eine_fremde_revision_wird_benannt_abgewiesen() -> None:
    """Eine deterministische Absage, die sagt WAS sie kann — kein blankes 400.

    Genau die Unterscheidung, die `CLAUDE.md` am `lotId`-Fall festhaelt: Der
    Statuscode allein liest sich fuer ein Modell wie eine Stoerung. Hier nennt
    die Antwort die angefragte und die unterstuetzte Revision, und die
    unterstuetzte ist die, gegen die dieses Repo gepinnt ist.
    """
    async with draht() as client:
        response = await modern(client, "tools/list", version="2099-01-01")

    assert response.status_code == 400, response.text
    error = response.json()["error"]
    assert error["code"] == -32022
    assert error["data"]["requested"] == "2099-01-01"
    assert error["data"]["supported"] == [DOCUMENTED_MODERN_VERSION]


# ---------------------------------------------------------------------------
# Die beiden Aeren sind getrennt — gemessen
# ---------------------------------------------------------------------------


async def test_die_moderne_aera_kennt_keinen_handshake() -> None:
    """`initialize` ist in der modernen Aera keine Methode.

    Das ist die Trennung, die beide READMEs beschreiben, an der Antwort statt
    an der Beschreibung. Ein Client, der den Handshake auf dem modernen Draht
    versucht, bekommt keine halb gueltige Sitzung, sondern eine Absage.
    """
    async with draht() as client:
        response = await modern(
            client,
            "initialize",
            {"protocolVersion": DOCUMENTED_HANDSHAKE_VERSION, "capabilities": {}},
        )

    assert response.status_code == 404, response.text
    assert response.json()["error"]["code"] == -32601


async def test_der_handshake_antwortet_mit_der_angefragten_revision() -> None:
    async with draht() as client:
        result = await handshake(client, DOCUMENTED_HANDSHAKE_VERSION)

    assert result["result"]["protocolVersion"] == DOCUMENTED_HANDSHAKE_VERSION


async def test_der_handshake_deckelt_bei_der_dokumentierten_revision() -> None:
    """Die Obergrenze, die beide READMEs nennen — gemessen statt behauptet.

    Ein Client, der etwas Neueres verlangt, bekommt die Obergrenze zurueck und
    NICHT die moderne Revision: Wer `2026-07-28` will, nimmt den Envelope.
    """
    async with draht() as client:
        result = await handshake(client, "2099-01-01")

    aushandelt = result["result"]["protocolVersion"]
    assert aushandelt == DOCUMENTED_HANDSHAKE_VERSION
    assert aushandelt != DOCUMENTED_MODERN_VERSION


# ---------------------------------------------------------------------------
# `server/discover`
# ---------------------------------------------------------------------------


async def test_server_discover_nennt_genau_die_gepinnte_revision() -> None:
    async with draht() as client:
        response = await modern(client, "server/discover")

    assert response.status_code == 200, response.text
    result = response.json()["result"]
    assert result["supportedVersions"] == [DOCUMENTED_MODERN_VERSION]
    assert result["instructions"], "ohne Instructions fehlt dem Client die Einordnung"


# ---------------------------------------------------------------------------
# `serverInfo` in `_meta` jeder Antwort
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "method",
    ["tools/list", "resources/list", "resources/templates/list", "prompts/list", "server/discover"],
)
async def test_jede_antwort_traegt_die_serverinfo(method: str) -> None:
    """Die moderne Aera fuehrt `serverInfo` pro Antwort mit, nicht einmal pro Sitzung.

    Was hier fehlt, fehlt darum bei jedem Aufruf. Vor diesem Commit stand in
    jeder Antwort `{"name": "swiss_culture_mcp", "version": ""}` — der
    Unterstrich ist der gemessene Altstand, seit dem 20.9.2026 traegt der Name
    den Bindestrich wie ueberall sonst im Projekt.
    """
    async with draht() as client:
        response = await modern(client, method)

    assert response.status_code == 200, response.text
    info = response.json()["result"]["_meta"][SERVER_INFO_KEY]
    assert info["name"] == "swiss-culture-mcp"
    assert info["version"] == __version__
    assert info["version"], "ein leerer String ist die Drahtform von «weiss nicht»"
    assert info["websiteUrl"] == PROJECT_URL


async def test_die_version_am_draht_ist_die_der_paketmetadaten() -> None:
    """Die Version kommt aus `importlib.metadata`, nicht aus einem Literal.

    `scripts/check_version_sync.py` weist eine handgepflegte Nummer in `src/`
    zurueck; diese Zusicherung ist die andere Haelfte davon — sie zeigt, dass
    am Draht auch wirklich die Nummer der Distribution steht und nicht
    `0.0.0+source` aus einem Lauf ohne Install.
    """
    from importlib.metadata import version as verteilungsversion

    async with draht() as client:
        response = await modern(client, "tools/list")

    info = response.json()["result"]["_meta"][SERVER_INFO_KEY]
    assert info["version"] == verteilungsversion("swiss-culture-mcp")


async def test_ein_server_ohne_identitaet_meldet_eine_leere_version() -> None:
    """Gegenprobe: gleiches SDK, gleicher Draht, nur ohne `version=`.

    Sie belegt zweierlei. Erstens, dass die Tests oben etwas pruefen koennen —
    ohne sie waeren sie auch gruen, wenn das SDK die Nummer von sich aus
    setzte. Zweitens, dass der leere String kein unvermeidlicher Default ist,
    sondern das, was ein Server meldet, der nichts uebergibt.
    """
    async with draht(MCPServer("kontrolle")) as client:
        response = await modern(client, "tools/list")

    info = response.json()["result"]["_meta"][SERVER_INFO_KEY]
    assert info["name"] == "kontrolle"
    assert info["version"] == ""
    assert "websiteUrl" not in info


# ---------------------------------------------------------------------------
# Frischehinweise (SEP-2549) — am Draht statt an der Konfiguration
# ---------------------------------------------------------------------------


# Die Methoden, die nach Spec cachebar sind, ABER Inhalt liefern statt eines
# Verzeichnisses. Sie tragen bewusst keinen Hinweis — ein Hinweis darauf waere
# eine Zusicherung ueber den Inhalt.
INHALTS_METHODEN = frozenset({"resources/read", "prompts/get"})


@pytest.mark.parametrize("method", sorted(set(CACHEABLE_METHODS) - INHALTS_METHODEN))
async def test_jede_auflistende_methode_traegt_den_hinweis_am_draht(method: str) -> None:
    """`tests/test_cache_hints.py` prueft dasselbe ueber einen In-Process-Client.

    Hier steht es an der Drahtform der modernen Aera: `ttlMs` und `cacheScope`
    als Felder des Resultats.

    Parametrisiert ueber `CACHEABLE_METHODS` des SDK, NICHT ueber `CACHE_HINTS`
    — und das ist der Punkt. Die erste Fassung nahm `sorted(CACHE_HINTS)`, weil
    ein neuer Eintrag so von selbst mitgeprueft wird. Die Gegenprobe zeigte,
    warum das zu wenig ist: `prompts/list` aus `CACHE_HINTS` zu loeschen liess
    die Suite gruen, weil mit dem Eintrag auch der Testfall verschwand. Ein
    Test, der ueber sein Pruefobjekt parametrisiert, kann dessen Entfernung
    nicht bemerken.

    Die Liste des SDK kann er das: sie kommt von aussen. Faellt dieser Test,
    ist entweder ein Hinweis verlorengegangen oder die Spec hat eine neue
    cachebare Methode — dann ist zu entscheiden, ob sie ein Verzeichnis
    liefert oder nach `INHALTS_METHODEN` gehoert.
    """
    async with draht() as client:
        response = await modern(client, method)

    assert response.status_code == 200, response.text
    result = response.json()["result"]
    assert result["ttlMs"] == LIST_CACHE_TTL_MS
    assert result["cacheScope"] == "public"


async def test_der_inhalt_einer_ressource_traegt_am_draht_keinen_hinweis() -> None:
    """Die negative Zusicherung, auch hier: `resources/read` liefert Inhalt.

    Ein Hinweis darauf waere eine Aussage ueber den Inhalt statt ueber das
    Verzeichnis.
    """
    async with draht() as client:
        response = await modern(client, "resources/read", {"uri": "bak://isos/kantone"})

    assert response.status_code == 200, response.text
    result = response.json()["result"]
    assert result["ttlMs"] == 0
    assert result["cacheScope"] == "private"


# ---------------------------------------------------------------------------
# Ein Werkzeugaufruf ueber den modernen Draht
# ---------------------------------------------------------------------------


async def test_ein_werkzeugaufruf_laeuft_ueber_den_modernen_draht() -> None:
    """Nicht nur die Verzeichnisse — auch die Nutzlast.

    Der Upstream ist gemockt: geprueft wird der Weg durch die moderne Aera,
    nicht die Quelle. Dass die Quelle noch das liefert, was der Server
    erwartet, halten die Live-Tests fest.
    """
    async with draht() as client:
        with patch("swiss_culture_mcp.server._get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"results": []}
            response = await modern(
                client,
                "tools/call",
                {"name": "bak_search_isos", "arguments": {"params": {"query": "Zürich"}}},
            )

    assert response.status_code == 200, response.text
    result = response.json()["result"]
    assert result["resultType"] == "complete"
    assert result["isError"] is False
    assert result["content"][0]["type"] == "text"
    assert mock_get.await_count == 1, "der Aufruf erreichte den Handler nicht"
    nutzlast = json.loads(result["content"][0]["text"])
    assert nutzlast["query"] == "Zürich", "der Suchbegriff kam nicht im Handler an"


async def test_ein_unbekanntes_werkzeug_wird_am_draht_abgewiesen() -> None:
    """Gegenprobe zum Test darueber: der Draht fuehrt wirklich in die Registry.

    Ohne sie koennte der Aufruf oben auch von einem Pfad kommen, der jeden
    Namen annimmt.

    Erwartet war hier ein 4xx. Gemessen antwortet der Server `200` mit
    `isError: true` — und das ist richtig: ein fehlgeschlagener Werkzeugaufruf
    ist nach Spec ein RESULTAT, damit das Modell die Meldung sieht, und kein
    JSON-RPC-Fehler, der die Ebene darunter betrifft. Der Statuscode ist hier
    also keine Auskunft ueber den Aufruf. Dieselbe Verwechslung, gegen die
    `CLAUDE.md` bei `lotId` und beim 403 argumentiert, nur in die andere
    Richtung: nicht jede Absage ist ein Fehler, und nicht jede 200 ein Erfolg.
    """
    async with draht() as client:
        response = await modern(
            client, "tools/call", {"name": "bak_gibt_es_nicht", "arguments": {}}
        )

    assert response.status_code == 200, response.text
    result = response.json()["result"]
    assert result["isError"] is True
    assert "bak_gibt_es_nicht" in result["content"][0]["text"]
