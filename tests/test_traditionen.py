"""Lebendige Traditionen: Leser und Werkzeuge, offline gegen echte Antworten.

Die Fixtures sind Antworten von `lebendige-traditionen.ch/api/collector/de/`,
unveraendert aufgezeichnet von `scripts/record_fixtures.py` am 7.11.2026
(Herkunft in `PROVENANCE.md`). Bis dahin standen hier zwei von Hand
geschriebene HTML-Schnipsel von zusammen 776 Bytes. Sie hielten jeden Test
gruen, waehrend beide Werkzeuge produktiv scheiterten: Die Website war
umgebaut, die alten Adressen antworteten mit 404, und die Schnipsel kodierten
genau die Annahme, die gebrochen war.

Die Zahlen unten (228 Traditionen, 9 UNESCO-Eintraege, Kantone der Basler
Fasnacht) stammen aus der Quelle selbst und sind am 7.11.2026 ueber alle 228
Detailseiten gegengeprueft: Jede trug Beschreibungstext, Kategorie und PDF, und
die 20 Traditionen ohne Kanton waren genau die 20, die die Seite unter
«Schweiz» fuehrt.
"""

from __future__ import annotations

import copy
import gzip
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from swiss_culture_mcp import traditionen as t
from swiss_culture_mcp.server import (
    TraditionDetailInput,
    TraditionListInput,
    bak_get_tradition_detail,
    bak_list_traditions,
)

_FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _antwort(name: str) -> dict:
    return json.loads(gzip.decompress((_FIXTURES / name).read_bytes()))


def _liste() -> dict:
    return _antwort("traditionen_liste.json.gz")


def _fasnacht() -> dict:
    return _antwort("tradition_basler-fasnacht.json.gz")


def _alphorn() -> dict:
    return _antwort("tradition_alphorn-und-buechelspiel.json.gz")


def _gebaerdensprachen() -> dict:
    return _antwort("tradition_gebaerdensprachen.json.gz")


def _ersetze_im_baum(seite: dict, alt: str, neu: str) -> dict:
    """Eine Zeichenkette ueberall im Komponentenbaum ersetzen."""
    return json.loads(json.dumps(seite, ensure_ascii=False).replace(alt, neu))


class TestListe:
    def test_liest_alle_traditionen_der_aufnahme(self):
        liste = t.parse_liste(_liste())
        assert len(liste["traditionen"]) == 228
        assert liste["max_elements"] == 250
        slugs = [e["slug"] for e in liste["traditionen"]]
        assert len(slugs) == len(set(slugs))

    def test_der_stern_heisst_unesco_und_faellt_aus_dem_namen(self):
        eintraege = {e["slug"]: e for e in t.parse_liste(_liste())["traditionen"]}
        assert sum(e["unesco_repraesentative_liste"] for e in eintraege.values()) == 9
        fasnacht = eintraege["basler-fasnacht"]
        assert fasnacht["name"] == "Basler Fasnacht"
        assert fasnacht["unesco_repraesentative_liste"] is True
        assert eintraege["schwingen"]["unesco_repraesentative_liste"] is False
        assert not any("*" in e["name"] for e in eintraege.values())

    def test_sortiert_umlaute_unter_ihren_grundbuchstaben(self):
        namen = [e["name"] for e in t.parse_liste(_liste())["traditionen"]]
        assert namen.index("Älplerchilbi (Sennenchilbi)") < namen.index(
            "Amateurtheater in der Westschweiz"
        )

    def test_ohne_listen_komponente_ist_ein_fehler(self):
        seite = _ersetze_im_baum(_liste(), '"dynamic-page-teaser"', '"etwas-anderes"')
        with pytest.raises(t.TraditionenLeseError, match="0 Listen-Komponenten"):
            t.parse_liste(seite)

    def test_ein_eintrag_ohne_slug_ist_ein_fehler(self):
        seite = _ersetze_im_baum(_liste(), '"/de/basler-fasnacht"', '""')
        with pytest.raises(t.TraditionenLeseError, match="ohne Titel oder Slug"):
            t.parse_liste(seite)


class TestDetail:
    def test_basler_fasnacht(self):
        d = t.parse_detail(_fasnacht(), "basler-fasnacht")
        assert d["titel"] == "Basler Fasnacht"
        assert d["unesco_repraesentative_liste"] is True
        assert d["kantone"] == [{"kuerzel": "BS", "name": "Basel-Stadt"}]
        assert d["ueberregional"] is False
        assert d["kategorien"] == [
            "Gesellschaftliche Praktiken",
            "Mündliche Ausdrucksweisen",
            "Darstellende Künste",
            "Traditionelles Handwerk",
        ]
        assert d["beschreibung"] and d["beschreibung"][0].startswith("Ein Ritterturnier von 1376")
        assert {"slug": "jurassischer-karneval", "name": "Jurassischer Karneval"} in d[
            "verwandte_traditionen"
        ]
        assert d["detailbeschreibung_pdf"].startswith("https://backend.lebendige-traditionen.ch/")
        assert d["fehlende_abschnitte"] == []

    def test_der_unesco_vermerk_ist_kein_beschreibungstext(self):
        d = t.parse_detail(_fasnacht(), "basler-fasnacht")
        assert not any("UNESCO" in a for a in d["beschreibung"])

    def test_alphorn_ist_ueberregional(self):
        d = t.parse_detail(_alphorn(), "alphorn-und-buechelspiel")
        assert d["kantone"] == []
        assert d["ueberregional"] is True
        assert "Schweiz" in d["kantone_hinweis"]
        assert d["fehlende_abschnitte"] == []

    def test_kanton_als_h4_und_ch_fuer_die_ganze_schweiz(self):
        """Auf drei der 228 Seiten steht «Kanton» als h4 statt h2 — hier mit «CH»."""
        d = t.parse_detail(_gebaerdensprachen(), "gebaerdensprachen")
        assert d["fehlende_abschnitte"] == []
        assert d["kantone"] == [] and d["ueberregional"] is True
        assert d["kategorien"] and d["beschreibung"]

    def test_nach_einem_akkordeon_endet_der_abschnitt(self):
        """Was nach dem Akkordeon kommt, gehoert nicht mehr zu «Kategorie».

        Gebaut, nicht aufgezeichnet: In keiner der 228 Seiten folgt einem
        Akkordeon noch ein Link im selben Abschnitt. Ohne diese Regel wuerde
        ein solcher Link aber still zur Kategorie — das soll nicht erst die
        Quelle zeigen muessen.
        """
        p = lambda text: {"identifier": "p", "properties": {"text": text}}  # noqa: E731
        seite = {
            "metadata": {"title": "Probe"},
            "content": [
                {"identifier": "heading-h2", "properties": {"label": "Kategorie"}},
                p('<a href="/de/handwerk" aria-label="Handwerk">Handwerk</a>'),
                {"identifier": "accordion-container", "nestedContent": []},
                p('<a href="/de/irgendwas" aria-label="Irgendwas">Irgendwas</a>'),
                {"identifier": "heading-h2", "properties": {"label": "Kanton"}},
                p('<a href="/de/bern" aria-label="BE">BE</a>'),
            ],
        }
        d = t.parse_detail(seite, "probe")
        assert d["kategorien"] == ["Handwerk"]
        assert [k["kuerzel"] for k in d["kantone"]] == ["BE"]

    def test_verwandte_kommen_nur_aus_dem_akkordeon(self):
        """Kantons- und Kategorielinks sind keine verwandten Traditionen."""
        slugs = {
            v["slug"]
            for v in t.parse_detail(_fasnacht(), "basler-fasnacht")["verwandte_traditionen"]
        }
        assert not slugs & {"basel-stadt", "gesellschaftliche-praktiken", "kantone"}

    def test_ein_fehlender_kantonsabschnitt_wird_gemeldet(self):
        seite = _ersetze_im_baum(_fasnacht(), '"label": "Kanton"', '"label": "Region"')
        d = t.parse_detail(seite, "basler-fasnacht")
        assert "Kanton" in d["fehlende_abschnitte"]
        assert d["kantone"] == []
        assert d["ueberregional"] is False

    def test_ein_unlesbarer_kantonsabschnitt_wird_gemeldet_nicht_ueberregional(self):
        seite = _ersetze_im_baum(_fasnacht(), 'aria-label=\\"BS\\">BS<', 'aria-label=\\"XY\\">XY<')
        d = t.parse_detail(seite, "basler-fasnacht")
        assert d["kantone"] == []
        assert d["ueberregional"] is False
        assert "Kanton" in d["fehlende_abschnitte"]

    def test_ohne_titel_ist_ein_fehler(self):
        seite = copy.deepcopy(_fasnacht())
        seite["metadata"]["title"] = ""
        with pytest.raises(t.TraditionenLeseError, match="kein Titel"):
            t.parse_detail(seite, "basler-fasnacht")


class TestKantonsformen:
    """Alle Formen, die im Abschnitt «Kanton» der 228 Seiten vorkommen (7.11.2026)."""

    @pytest.mark.parametrize(
        ("text", "links", "kuerzel", "ueberregional"),
        [
            ("BS", [{"href": "/de/basel-stadt", "label": "BS", "text": "BS"}], ["BS"], False),
            (
                "Graubünden",
                [{"href": "/de/graubuenden", "label": "Graubünden", "text": "Graubünden"}],
                ["GR"],
                False,
            ),
            ("BE", [], ["BE"], False),
            ("LU NW OW SZ UR ZG", [], ["LU", "NW", "OW", "SZ", "UR", "ZG"], False),
            ("CH", [{"href": "/de/schweiz", "label": "CH", "text": "CH"}], [], True),
            (
                "Traditionen nach Kantone",
                [{"href": "/de/kantone", "label": "Traditionen nach Kantone", "text": "x"}],
                [],
                True,
            ),
            ("Traditionen Liste", [], [], True),
            ("Irgendwo", [], [], False),
        ],
    )
    def test_form(self, text, links, kuerzel, ueberregional):
        assert t._kantone_aus(text, links) == (kuerzel, ueberregional)


class TestBuchstabe:
    @pytest.mark.parametrize(
        ("name", "erwartet"),
        [("Älplerchilbi", "A"), ("Übernamen", "U"), ("«Le Chant»", "L"), ("schwingen", "S")],
    )
    def test_grundbuchstabe(self, name, erwartet):
        assert t.buchstabe(name) == erwartet


class TestWerkzeuge:
    @pytest.mark.asyncio
    async def test_liste_mit_offiziellen_namen(self):
        with patch("swiss_culture_mcp.server._get", new_callable=AsyncMock) as get:
            get.return_value = _liste()
            data = json.loads(await bak_list_traditions(TraditionListInput()))
        assert get.await_args.args[0].endswith("/api/collector/de/alle-traditionen.json")
        assert data["gesamt"] == data["count"] == 228
        assert "warnung" not in data
        assert {"name", "slug", "url", "unesco_repraesentative_liste"} == set(data["traditions"][0])

    @pytest.mark.asyncio
    async def test_buchstabenfilter_findet_umlaute(self):
        with patch("swiss_culture_mcp.server._get", new_callable=AsyncMock) as get:
            get.return_value = _liste()
            data = json.loads(await bak_list_traditions(TraditionListInput(buchstabe="u")))
        namen = [e["name"] for e in data["traditions"]]
        assert "Übernamen in der Zentralschweiz" in namen
        assert all(t.buchstabe(n) == "U" for n in namen)
        assert data["gesamt"] == 228

    @pytest.mark.asyncio
    async def test_eine_volle_uebersicht_wird_als_moeglicherweise_abgeschnitten_gemeldet(self):
        seite = _ersetze_im_baum(_liste(), '"maxElements": 250', '"maxElements": 228')
        with patch("swiss_culture_mcp.server._get", new_callable=AsyncMock) as get:
            get.return_value = seite
            data = json.loads(await bak_list_traditions(TraditionListInput()))
        assert "abgeschnitten" in data["warnung"]

    @pytest.mark.asyncio
    async def test_detail(self):
        with patch("swiss_culture_mcp.server._get", new_callable=AsyncMock) as get:
            get.return_value = _fasnacht()
            data = json.loads(
                await bak_get_tradition_detail(TraditionDetailInput(slug="basler-fasnacht"))
            )
        assert get.await_args.args[0].endswith("/api/collector/de/basler-fasnacht.json")
        assert data["kantone"] == [{"kuerzel": "BS", "name": "Basel-Stadt"}]
        assert data["url"] == "https://www.lebendige-traditionen.ch/de/basler-fasnacht"

    @pytest.mark.asyncio
    async def test_ein_alter_slug_bekommt_den_neuen_vorgeschlagen(self):
        anfrage = httpx.Request("GET", "https://www.lebendige-traditionen.ch/x")
        nicht_da = httpx.HTTPStatusError(
            "", request=anfrage, response=httpx.Response(404, request=anfrage)
        )
        with patch("swiss_culture_mcp.server._get", new_callable=AsyncMock) as get:
            get.side_effect = [nicht_da, _liste()]
            antwort = await bak_get_tradition_detail(
                TraditionDetailInput(slug="alphorn--und-buechelspiel")
            )
        assert antwort.startswith("Fehler: Keine Tradition")
        assert "alphorn-und-buechelspiel" in antwort
        # Ein 404 ist eine Antwort: kein Rat, es spaeter noch einmal zu versuchen.
        assert "später" not in antwort

    @pytest.mark.asyncio
    async def test_eine_unerwartete_form_wird_benannt(self):
        seite = _ersetze_im_baum(_liste(), '"dynamic-page-teaser"', '"etwas-anderes"')
        with patch("swiss_culture_mcp.server._get", new_callable=AsyncMock) as get:
            get.return_value = seite
            antwort = await bak_list_traditions(TraditionListInput())
        assert antwort.startswith("Fehler: lebendige-traditionen.ch antwortet in unerwarteter Form")
