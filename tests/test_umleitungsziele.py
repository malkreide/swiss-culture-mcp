"""Wo die Anfragen wirklich landen — und ob dieser Host erlaubt ist.

`_assert_host_allowed()` prueft die Adresse NACH der Umleitung. Die Fixture
`adressen.json` hielt aber nur den Statuscode unter dem Ausgangs-Host fest.
Damit war die Aufzeichnung blind fuer genau den Bruch, den sie sehen soll:
`opendata.swiss` beantwortet die CKAN-Aufrufe mit 302 auf
`ckan.opendata.swiss`, der Recorder folgte, notierte 200 — und produktiv
scheiterte trotzdem jeder `bak_get_opendata`-Aufruf an `Host nicht erlaubt`.
Alle Unit-Tests blieben gruen. Gefunden hat es der erste Live-Lauf (16.8.2026).

`record_fixtures.py` schreibt seither `final_url`, `final_host` und
`umgeleitet` mit. Diese Datei liest sie und laeuft **in** der CI, ohne Netz.
"""

from __future__ import annotations

import json
from pathlib import Path

from swiss_culture_mcp.http_client import ALLOWED_HOSTS

FIXTURES = Path(__file__).resolve().parent / "fixtures"

# Nur die Adressen, die der Server tatsaechlich abruft (`_get` / `_get_text`).
# `gisos` und `bak_wurzel` gibt er als Quellenlink aus, ohne sie zu holen —
# ihr Umleitungsziel (`www.bak.admin.ch`) gehoert deshalb NICHT in die
# Allowlist, und dieser Test darf es nicht verlangen.
ABGERUFEN = {
    "geo_mapserver": "GEO_ADMIN_BASE",
    "geo_searchserver": "GEO_ADMIN_SEARCH",
    "ckan": "CKAN_BASE",
    "rss": "RSS_BASE",
    "traditionen_liste": "TRADITIONS_BASE",
}


def _adressen() -> dict:
    pfad = FIXTURES / "adressen.json"
    if not pfad.is_file():
        raise FileNotFoundError(
            f"Keine Fixture unter {pfad}. Neu aufzeichnen mit `python scripts/record_fixtures.py`."
        )
    return json.loads(pfad.read_text(encoding="utf-8"))["adressen"]


def _host(url: str) -> str:
    return url.split("/", 3)[2].split("@")[-1].split(":")[0]


def test_die_fixture_haelt_die_umleitungsziele_ueberhaupt_fest() -> None:
    """Benennt den Grund, wenn die Aufzeichnung die Felder nicht mehr traegt.

    Der Test unten faellt in diesem Fall ohnehin — er greift die Felder direkt
    ab und endet in einem nackten `KeyError: 'final_host'`. Das sieht aus wie
    ein kaputter Test und nicht wie das, was es ist: eine Fixture von einem
    Recorder ohne Umleitungs-Aufzeichnung. Diese Kontrolle laeuft vorher und
    sagt es.
    """
    adressen = _adressen()
    for label in ABGERUFEN:
        assert label in adressen, f"{label} fehlt in adressen.json"
        eintrag = adressen[label]
        for feld in ("url", "final_url", "final_host", "umgeleitet"):
            assert feld in eintrag, (
                f"{label}: Feld {feld!r} fehlt — die Fixture stammt von einem "
                "Recorder ohne Umleitungs-Aufzeichnung. Neu aufzeichnen."
            )
        assert eintrag["final_host"], f"{label}: leerer final_host"


def test_jede_abgerufene_adresse_landet_auf_einem_erlaubten_host() -> None:
    """Der Bruch, der `bak_get_opendata` produktiv unbrauchbar machte.

    Geprueft wird Start- UND Zielhost: Bleibt die Umleitung eines Tages aus,
    faellt dieser Test nicht faelschlich um, und verschwindet der Eintrag fuer
    ein Ziel aus der Allowlist, solange umgeleitet wird, faellt er sofort.
    """
    adressen = _adressen()
    verstoesse = []
    for label, konstante in ABGERUFEN.items():
        eintrag = adressen[label]
        for rolle, host in (
            ("Start", _host(eintrag["url"])),
            ("Ziel", eintrag["final_host"]),
        ):
            if host not in ALLOWED_HOSTS:
                verstoesse.append(
                    f"{label} ({konstante}) {rolle}-Host {host!r} fehlt in ALLOWED_HOSTS"
                )
    assert not verstoesse, (
        "Aufrufe enden auf einem Host, den `_assert_host_allowed()` abweist — "
        f"produktiv scheitert das Tool, nicht nur der Test: {verstoesse}"
    )
