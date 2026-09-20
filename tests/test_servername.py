"""Eine Identitaet, eine Schreibweise (C3).

Der Server hiess am Draht `swiss_culture_mcp`, mit Unterstrich — und ueberall
sonst `swiss-culture-mcp`: Distribution, Konsolenskript, Registry-Eintrag,
`User-Agent` gegenueber den Upstreams, Repository. Wer den Server anhand seines
`serverInfo.name` wiederzufinden versucht, sucht damit unter einem Namen, unter
dem er nirgends sonst gefuehrt wird.

Die Zusicherung hier ist bewusst nicht «der Name lautet X», sondern «alle
Stellen nennen denselben». Ein Literal in einem Test, das man beim Umbenennen
mitzieht, belegt nur, dass jemand zweimal dasselbe getippt hat; eine Klammer
ueber die Quellen faellt auch dann, wenn nur eine davon wandert.

Der Python-Logger heisst weiterhin `swiss_culture_mcp` und steht mit Absicht
NICHT in dieser Liste: Ein Logger-Name ist keine Server-Identitaet, und ihn
mitzuziehen braeche jede Logkonfiguration beim Betreiber, ohne irgendetwas
anzugleichen. Eine Ausnahme, die man nicht aufschreibt, wird beim naechsten
Aufraeumen zum Fehler.
"""

from __future__ import annotations

import json
import pathlib
import tomllib

from swiss_culture_mcp.http_client import USER_AGENT
from swiss_culture_mcp.server import mcp

WURZEL = pathlib.Path(__file__).resolve().parent.parent
NAME = "swiss-culture-mcp"


def _pyproject() -> dict:
    return tomllib.loads((WURZEL / "pyproject.toml").read_text(encoding="utf-8"))


def _server_json() -> dict:
    return json.loads((WURZEL / "server.json").read_text(encoding="utf-8"))


def test_serverinfo_name_traegt_den_bindestrich():
    """Die Stelle, die C3 benennt. `MCPServer` fuehrt diesen Namen in
    `serverInfo` — in der Aera `2026-07-28` in JEDER Antwort, nicht nur im
    Handshake."""
    assert mcp.name == NAME


def test_alle_stellen_nennen_denselben_namen():
    """Die Klammer. Faellt sie, ist eine Quelle gewandert und die uebrigen
    nicht — gleich welche."""
    py = _pyproject()
    sj = _server_json()
    gefunden = {
        "pyproject [project].name": py["project"]["name"],
        "pyproject [project.scripts]": next(iter(py["project"]["scripts"])),
        "server.json packages[0].identifier": sj["packages"][0]["identifier"],
        "MCPServer(...) / serverInfo.name": mcp.name,
    }
    abweichend = {ort: wert for ort, wert in gefunden.items() if wert != NAME}
    assert not abweichend, f"weichen ab: {abweichend}"


def test_der_registry_name_endet_auf_denselben_namen():
    """`server.json` fuehrt den Namen mit Namensraum
    (`io.github.<owner>/<name>`). Geprueft wird der Teil nach dem Schraegstrich
    — der Namensraum gehoert dem Besitzer, nicht dem Server."""
    voll = _server_json()["name"]
    assert voll.rsplit("/", 1)[-1] == NAME, voll


def test_der_user_agent_nennt_denselben_namen():
    """Der `User-Agent` ist der Name, unter dem die Bundesstellen diesen
    Server in ihren Logs sehen. Er trug den Bindestrich schon immer; diese
    Zeile haelt fest, dass er es weiterhin tut."""
    assert USER_AGENT.startswith(f"{NAME}/")


def test_das_konsolenskript_zeigt_auf_diesen_server():
    """Gegenprobe zum Namen des Skripts: Dass es richtig HEISST, sagt nichts
    darueber, wohin es zeigt. Ein Eintrag auf ein fremdes Modul waere ein
    Container, der startet und etwas anderes bedient."""
    ziel = _pyproject()["project"]["scripts"][NAME]
    assert ziel == "swiss_culture_mcp.server:main", ziel


def test_der_logger_behaelt_den_unterstrich():
    """Die aufgeschriebene Ausnahme. Ohne sie zieht der naechste Aufraeumlauf
    den Logger mit und bricht die Logkonfiguration jedes Betreibers, ohne dass
    irgendeine Identitaet dadurch einheitlicher wuerde."""
    from swiss_culture_mcp.http_client import logger

    assert logger.name == "swiss_culture_mcp"
