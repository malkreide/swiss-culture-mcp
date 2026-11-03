"""Anhang 1 der VISOS (SR 451.12), gelesen aus Fedlex — die Sollwerte der ISOS-Tests.

WARUM DAS ES GIBT
-----------------
Bis zum 3.11.2026 standen die Sollwerte des ISOS-Live-Tests fest im Test: ZH
73, GR 105, ausgezaehlt aus der Fassung vom 1.6.2026. Am 1.11.2026 trat eine
Revision in Kraft (AS 2026 488), `api3.geo.admin.ch` zog nach, und der
geplante Lauf vom 2.11.2026 wurde rot — auf demselben Commit, der eine Woche
zuvor gruen war. Der Server lieferte die gueltige Zahl; veraltet war der Test.

Die Verordnung wurde 2024, 2025 und zweimal 2026 revidiert. Fest eingetragene
Zahlen machen die Suite also etwa zweimal im Jahr rot, ohne dass irgendetwas
kaputt ist. Und sie vermischen zwei Fragen: «Wurde die VISOS revidiert?» und
«Liefert die API, was die Verordnung festsetzt?» Nur die zweite gehoert in den
Vertrag mit der Quelle. Deshalb liest der Live-Test die Sollwerte zur Laufzeit
aus der Fassung, die am Stichtag gilt.

WAS HIER GEPRUEFT WIRD, STATT ES STILL HINZUNEHMEN
-------------------------------------------------
* Die Kopfzeile der Tabelle muss woertlich `Kanton | Nr. | Objekt |
  Siedlungskategorie` lauten. Am 3.8.2026 hiess «nicht gefunden» in einem
  anderen Repo, dass eine Quelle die Schreibweise ihrer Kopfzeile gewechselt
  hatte; alle Unit-Tests blieben gruen. Eine geaenderte Kopfzeile bricht hier
  ab, mit der gelesenen Zeile in der Meldung.
* Jede Datenzeile muss vier Zellen und eine rein numerische Nummer tragen.
  Eine Zeile, die das nicht tut, wird nicht uebersprungen: Ein Parser, der
  Unlesbares weglaesst, liefert eine kuerzere Liste, und eine kuerzere Liste
  sieht aus wie eine Revision.
* Am Stichtag muss genau eine Fassung gelten, und sie muss eine deutsche
  HTML-Ausgabe haben. Deren Dateiname traegt eine wechselnde Endung
  (`-html-1`, `-html-2`, `-html-5` — am 3.11.2026 gemessen); er kommt deshalb
  aus der Abfrage und wird nicht zusammengesetzt.

Fedlex ist eine Quelle wie jede andere: Ist sie nicht erreichbar, scheitert
der Live-Test mit `FedlexLeseError` und nennt Fedlex in der Meldung. Der
Lauf wird dann als `finding` eingeordnet, nicht als `clear` — ein Vergleich,
der nicht stattfand, darf kein offenes Issue schliessen.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser

import httpx

ELI = "https://fedlex.data.admin.ch/eli/cc/2019/673"
SPARQL = "https://fedlex.data.admin.ch/sparqlendpoint"
KOPFZEILE = ("Kanton", "Nr.", "Objekt", "Siedlungskategorie")
_ANHANG_1 = "annex_1"

_ABFRAGE = """\
PREFIX jolux: <http://data.legilux.public.lu/resource/ontology/jolux#>
SELECT DISTINCT ?fassung ?ab ?bis ?datei WHERE {
  ?fassung jolux:isMemberOf <%(eli)s> ; jolux:dateApplicability ?ab .
  OPTIONAL { ?fassung jolux:dateEndApplicability ?bis }
  OPTIONAL {
    ?fassung jolux:isRealizedBy ?ausdruck .
    ?ausdruck jolux:language <http://publications.europa.eu/resource/authority/language/DEU> ;
              jolux:isEmbodiedBy ?form .
    ?form jolux:isExemplifiedBy ?datei .
    FILTER(CONTAINS(STR(?datei), "/de/html/"))
  }
} ORDER BY DESC(?ab)
"""


class FedlexLeseError(RuntimeError):
    """Fedlex hat nicht geliefert, was der Abgleich braucht.

    Ausdruecklich ein eigener Typ: Die Meldung muss sagen, dass die
    Sollwert-Quelle versagt hat, nicht `api3.geo.admin.ch`.
    """


@dataclass(frozen=True)
class Fassung:
    eli: str
    ab: date
    bis: date | None
    html: tuple[str, ...]

    @property
    def kennung(self) -> str:
        """`JJJJMMTT`, wie Fedlex die Fassung in der ELI fuehrt."""
        return self.eli.rsplit("/", 1)[-1]


@dataclass(frozen=True)
class Eintrag:
    kanton: str
    nummer: str
    objekt: str
    siedlungskategorie: str


def abfrage(eli: str = ELI) -> str:
    """Die SPARQL-Abfrage nach allen Fassungen eines Erlasses."""
    return _ABFRAGE % {"eli": eli}


def parse_fassungen(antwort: dict) -> list[Fassung]:
    """Fassungen aus einer `application/sparql-results+json`-Antwort.

    Je Fassung kann die Abfrage mehrere Zeilen liefern (eine je HTML-Datei);
    sie werden hier zusammengefasst.
    """
    gesammelt: dict[str, dict] = {}
    for zeile in antwort["results"]["bindings"]:
        eli = zeile["fassung"]["value"]
        eintrag = gesammelt.setdefault(
            eli,
            {
                "ab": date.fromisoformat(zeile["ab"]["value"]),
                "bis": date.fromisoformat(zeile["bis"]["value"]) if "bis" in zeile else None,
                "html": set(),
            },
        )
        if "datei" in zeile:
            eintrag["html"].add(zeile["datei"]["value"])
    return sorted(
        (Fassung(eli, e["ab"], e["bis"], tuple(sorted(e["html"]))) for eli, e in gesammelt.items()),
        key=lambda f: f.ab,
        reverse=True,
    )


def gueltige_fassung(fassungen: list[Fassung], stichtag: date) -> Fassung:
    """Die eine Fassung, die am Stichtag gilt — sonst ein Fehler, kein Raten."""
    treffer = [f for f in fassungen if f.ab <= stichtag and (f.bis is None or stichtag <= f.bis)]
    if len(treffer) != 1:
        raise FedlexLeseError(
            f"Fedlex: am {stichtag:%d.%m.%Y} gelten {len(treffer)} Fassungen der VISOS "
            f"statt genau einer: {[f.kennung for f in treffer] or 'keine'}"
        )
    fassung = treffer[0]
    if len(fassung.html) != 1:
        raise FedlexLeseError(
            f"Fedlex: die Fassung {fassung.kennung} hat {len(fassung.html)} deutsche "
            f"HTML-Ausgaben statt genau einer: {list(fassung.html) or 'keine'}"
        )
    return fassung


class _TabellenLeser(HTMLParser):
    """Sammelt die Zellen jeder Tabelle, samt den `section`-IDs um sie herum."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tabellen: list[tuple[tuple[str | None, ...], list[list[str]]]] = []
        self._sections: list[str | None] = []
        self._zeilen: list[list[list[str]]] | None = None
        self._zelle: list[str] | None = None
        self._um_tabelle: tuple[str | None, ...] = ()
        self._tiefe = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "section":
            self._sections.append(dict(attrs).get("id"))
        elif tag == "table":
            self._tiefe += 1
            if self._tiefe == 1:
                self._zeilen = []
                self._um_tabelle = tuple(self._sections)
        elif self._tiefe == 1 and self._zeilen is not None:
            if tag == "tr":
                self._zeilen.append([])
            elif tag in ("td", "th") and self._zeilen:
                self._zelle = []
                self._zeilen[-1].append(self._zelle)

    def handle_endtag(self, tag: str) -> None:
        if tag == "section" and self._sections:
            self._sections.pop()
        elif tag == "table":
            self._tiefe -= 1
            if self._tiefe == 0 and self._zeilen is not None:
                zeilen = [[" ".join("".join(z).split()) for z in r] for r in self._zeilen]
                self.tabellen.append((self._um_tabelle, zeilen))
                self._zeilen = None
        elif tag in ("td", "th"):
            self._zelle = None

    def handle_data(self, data: str) -> None:
        if self._zelle is not None:
            self._zelle.append(data)


def parse_anhang1(html: str) -> list[Eintrag]:
    """Die Ortsbilder aus Anhang 1, Zeile fuer Zeile, ohne etwas wegzulassen."""
    leser = _TabellenLeser()
    leser.feed(html)
    leser.close()
    tabellen = [zeilen for sections, zeilen in leser.tabellen if _ANHANG_1 in sections]
    if len(tabellen) != 1:
        raise FedlexLeseError(
            f"Fedlex: Anhang 1 enthaelt {len(tabellen)} Tabellen statt genau einer"
        )
    kopf, *daten = tabellen[0]
    if tuple(kopf) != KOPFZEILE:
        raise FedlexLeseError(
            f"Fedlex: Kopfzeile von Anhang 1 geaendert — gelesen {kopf}, erwartet "
            f"{list(KOPFZEILE)}. Erst die Quelle ansehen, dann den Leser anpassen."
        )
    eintraege = []
    for nr, zeile in enumerate(daten, start=2):
        if len(zeile) != 4 or not zeile[1].isdigit():
            raise FedlexLeseError(
                f"Fedlex: Zeile {nr} von Anhang 1 ist nicht lesbar: {zeile}. "
                "Sie wird nicht uebersprungen — eine kuerzere Liste sieht aus "
                "wie eine Revision."
            )
        eintraege.append(Eintrag(*zeile))
    if not eintraege:
        raise FedlexLeseError("Fedlex: Anhang 1 enthaelt keine einzige Datenzeile")
    return eintraege


def abrufen(client: httpx.Client, stichtag: date) -> tuple[Fassung, list[Eintrag]]:
    """Die am Stichtag gueltige Fassung und ihr Anhang 1, live von Fedlex."""
    try:
        r = client.get(
            SPARQL,
            params={"query": abfrage()},
            headers={"Accept": "application/sparql-results+json"},
        )
        r.raise_for_status()
        fassung = gueltige_fassung(parse_fassungen(json.loads(r.text)), stichtag)
        r = client.get(fassung.html[0])
        r.raise_for_status()
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        raise FedlexLeseError(f"Fedlex nicht lesbar: {type(exc).__name__}: {exc}") from exc
    return fassung, parse_anhang1(r.text)
