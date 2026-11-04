"""Der Leser fuer Anhang 1 der VISOS, offline gegen die Aufnahme vom 3.11.2026.

`scripts/visos_anhang.py` liefert dem ISOS-Live-Test seine Sollwerte. Liest er
falsch, vergleicht der Live-Test gegen etwas Falsches — und meldet das als
Befund der Quelle. Deshalb steht er hier gegen eine aufgezeichnete Antwort
(`tests/fixtures/visos_*`, erzeugt von `scripts/record_visos.py`, Herkunft in
`PROVENANCE_VISOS.md`).

Die Zahlen unten stammen nicht aus diesem Leser. Sie sind am 3.11.2026
zweimal unabhaengig davon ermittelt worden: einmal mit regulaeren Ausdruecken
ueber dieselbe Fassung, einmal ueber `api3.geo.admin.ch` fuer alle 26
Kantone. Beide kamen auf 1255 Eintraege, GR 107, ZH 73. Ein Leser, der hier
gruen ist, zaehlt also wie zwei andere Wege — nicht bloss wie sein Autor.

Wird `record_visos.py` nach einer Revision erneut gefahren, entsteht eine neue
`visos_anhang1_<JJJJMMTT>.html.gz`, und diese Zahlen gehoeren mit derselben
unabhaengigen Auszaehlung nachgefuehrt.
"""

from __future__ import annotations

import gzip
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import visos_anhang as va  # noqa: E402

_FIXTURES = Path(__file__).resolve().parent / "fixtures"
_ANHANG = _FIXTURES / "visos_anhang1_20261101.html.gz"


def _html() -> str:
    return gzip.decompress(_ANHANG.read_bytes()).decode("utf-8")


def _fassungen() -> list[va.Fassung]:
    antwort = json.loads((_FIXTURES / "visos_fassungen.json").read_text(encoding="utf-8"))
    return va.parse_fassungen(antwort)


class TestGueltigeFassung:
    @pytest.mark.parametrize(
        ("stichtag", "kennung"),
        [
            # Der Tag des roten Laufs und der Tag davor: Hier wechselt die Fassung.
            ("2026-10-31", "20260601"),
            ("2026-11-01", "20261101"),
            # Beide Raender einer Fassung zaehlen dazu.
            ("2026-06-01", "20260601"),
            ("2026-05-31", "20250501"),
        ],
    )
    def test_der_stichtag_waehlt_die_dann_gueltige_fassung(self, stichtag, kennung):
        gewaehlt = va.gueltige_fassung(_fassungen(), date.fromisoformat(stichtag))
        assert gewaehlt.kennung == kennung

    def test_vor_der_ersten_fassung_ist_ein_fehler_kein_raten(self):
        with pytest.raises(va.FedlexLeseError, match="0 Fassungen"):
            va.gueltige_fassung(_fassungen(), date(2019, 1, 1))

    def test_zwei_gleichzeitig_gueltige_fassungen_sind_ein_fehler(self):
        a = va.Fassung(f"{va.ELI}/20260101", date(2026, 1, 1), None, ("a.html",))
        b = va.Fassung(f"{va.ELI}/20260601", date(2026, 6, 1), None, ("b.html",))
        with pytest.raises(va.FedlexLeseError, match="2 Fassungen"):
            va.gueltige_fassung([a, b], date(2026, 7, 1))

    def test_eine_fassung_ohne_deutsche_html_ausgabe_ist_ein_fehler(self):
        ohne = va.Fassung(f"{va.ELI}/20260101", date(2026, 1, 1), None, ())
        with pytest.raises(va.FedlexLeseError, match="0 deutsche"):
            va.gueltige_fassung([ohne], date(2026, 7, 1))

    def test_die_html_adresse_laesst_sich_nicht_zusammensetzen(self):
        """Warum die Adresse aus der Abfrage kommt: Ihre Endung wechselt."""
        endungen = {f.html[0].rsplit("-", 1)[1] for f in _fassungen() if f.html}
        assert len(endungen) > 1, endungen


class TestAnhang1:
    def test_zaehlt_wie_die_unabhaengigen_auszaehlungen(self):
        eintraege = va.parse_anhang1(_html())
        je_kanton = Counter(e.kanton for e in eintraege)
        assert len(eintraege) == 1255
        assert len(je_kanton) == 26
        assert (je_kanton["GR"], je_kanton["ZH"]) == (107, 73)

    def test_die_revision_vom_1_11_2026_ist_enthalten(self):
        paare = {(e.kanton, e.nummer) for e in va.parse_anhang1(_html())}
        assert {("GR", "2061"), ("GR", "2065"), ("GR", "2296"), ("JU", "929")} <= paare
        assert not {("GR", "2183"), ("BE", "929")} & paare

    def test_wilen_bei_neunforn_steht_unter_beiden_kantonen(self):
        """Die Vorbedingung der einzigen Ausnahme im Live-Test.

        Die API fuehrt das Ortsbild einmal (3705, `kantone: ['TG', 'ZH']`), der
        Anhang je Kanton unter eigener Nummer.
        """
        paare = {(e.kanton, e.nummer) for e in va.parse_anhang1(_html())}
        assert {("TG", "3705"), ("ZH", "5782")} <= paare

    def test_eine_geaenderte_kopfzeile_bricht_ab(self):
        html = _html().replace(">Siedlungskategorie</p>", ">Kategorie</p>", 1)
        with pytest.raises(va.FedlexLeseError, match="Kopfzeile"):
            va.parse_anhang1(html)

    def test_eine_unlesbare_zeile_bricht_ab_statt_wegzufallen(self):
        """Weglassen ergaebe 1254 Eintraege — und das saehe aus wie eine Revision."""
        html = _html().replace('">2061</p>', '">2061a</p>', 1)
        with pytest.raises(va.FedlexLeseError, match="nicht lesbar"):
            va.parse_anhang1(html)

    def test_ohne_anhang_1_ist_ein_fehler(self):
        html = _html().replace('id="annex_1"', 'id="annex_x"', 1)
        with pytest.raises(va.FedlexLeseError, match="0 Tabellen"):
            va.parse_anhang1(html)
