"""Ob die Adressen, die dieser Server baut, etwas liefern.

Ohne Netz. Grundlage ist `tests/fixtures/adressen.json`, aufgezeichnet am
2026-08-08 von `scripts/record_fixtures.py`.

Dieser Server braucht keine Zugangsdaten — seine gesamte Adressliste ist
pruefbar, und war es nie. Diese Datei laeuft **in** der CI.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

from swiss_culture_mcp.constants import BAK_WEBSITE, BAK_WEBSITE_TOT

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _adressen() -> dict:
    pfad = FIXTURES / "adressen.json"
    if not pfad.is_file():
        raise FileNotFoundError(
            f"Keine Fixture unter {pfad}. Neu aufzeichnen mit `python scripts/record_fixtures.py`."
        )
    return copy.deepcopy(json.loads(pfad.read_text(encoding="utf-8")))


class TestLebendeAdressen:
    def test_jede_ausgegebene_quelle_antwortete_mit_200(self):
        a = _adressen()["adressen"]
        for label in ("geo_mapserver", "geo_searchserver", "ckan", "gisos", "bak_wurzel", "rss"):
            assert a[label]["status"] == 200, f"{label}: {a[label]['status']}"

    def test_die_traditionsseiten_antworteten_mit_200(self):
        t = _adressen()["traditionen"]
        echte = {k: v for k, v in t.items() if not k.startswith("KONTROLLE")}
        assert len(echte) >= 3
        for slug, v in echte.items():
            assert v["status"] == 200, f"{slug}: {v}"


class TestKontrollen:
    """Ohne sie hiesse jeder Befund nur «ich habe eine 404 bekommen»."""

    def test_ein_erfundener_geo_dienst_gibt_404(self):
        assert _adressen()["adressen"]["kontrolle_geo_erfunden"]["status"] == 404

    def test_ein_erfundener_bak_pfad_gibt_404(self):
        assert _adressen()["adressen"]["kontrolle_bak_erfunden"]["status"] == 404

    def test_ein_erfundener_slug_gibt_404(self):
        """Der Beinahe-Fehlbefund, festgehalten.

        Beim ersten Versuch wurde ein Slug geraten, die Seite gab 404, und das
        sah nach einem Befund aus. Es war keiner — die echten Slugs
        funktionieren. Der Recorder zieht sie deshalb aus der Listenseite,
        statt sie sich auszudenken.
        """
        assert _adressen()["traditionen"]["KONTROLLE_erfundener_slug"]["status"] == 404

    def test_die_organisationsnummer_filtert_wirklich(self):
        """Ein 200 allein belegt beim RSS nichts.

        `org-nr=999999` liefert ebenfalls HTTP 200 — nur eben einen leeren
        Feed. Erst der Groessenunterschied zeigt, dass `BAK_ORG_NR` etwas
        auswaehlt.
        """
        a = _adressen()["adressen"]
        assert a["kontrolle_rss_erfunden"]["status"] == 200
        assert a["rss"]["bytes"] > 100 * a["kontrolle_rss_erfunden"]["bytes"]


class TestToteAdresse:
    def test_die_frueher_ausgegebene_bak_seite_war_404(self):
        a = _adressen()["adressen"]
        assert a["bak_baukultur_tot"]["status"] == 404
        assert a["bak_baukultur_tot"]["url"] == BAK_WEBSITE_TOT

    def test_kein_werkzeug_gibt_sie_noch_aus(self):
        """Sie bleibt als Konstante stehen, damit der Recorder sie prueft —
        aber sie darf in keiner Antwort mehr als Quelle erscheinen."""
        from swiss_culture_mcp import server

        code = Path(server.__file__).read_text(encoding="utf-8")
        assert "kulturerbe/baukultur.html" not in code
        assert "BAK_WEBSITE" in code

    def test_die_ersatzadresse_ist_die_gepruefte(self):
        a = _adressen()["adressen"]
        assert a["bak_wurzel"]["url"] == BAK_WEBSITE
        assert a["bak_wurzel"]["status"] == 200
