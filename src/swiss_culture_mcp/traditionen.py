"""Lebendige Traditionen: die JSON-Antworten von lebendige-traditionen.ch lesen.

WARUM ES DAS GIBT
-----------------
Bis Herbst 2026 holte der Server HTML von `/tradition/de/home/...` und las es
mit regulaeren Ausdruecken. Die Website ist seither eine Nuxt-Anwendung; die
alten Adressen antworten mit 404 (festgestellt am 3.11.2026, am 16.8.2026
noch 200), weitergeleitet wird nichts. `bak_list_traditions` meldete
«Ressource nicht gefunden», und alle Unit-Tests blieben gruen — ihre Fixtures
waren von Hand geschrieben und kodierten genau die Annahme, die gebrochen war.

Die neue Seite laedt ihre Inhalte als JSON von `/api/collector/de/<slug>.json`
auf demselben Host. Das ist robuster als HTML: Titel, Slugs, Kantone und
Kategorien stehen dort als Daten, nicht als Darstellung.

WAS DIE QUELLE HERGIBT (gemessen am 7.11.2026)
---------------------------------------------
* `alle-traditionen` traegt einen `dynamic-page-teaser` mit 228 `teaser-item`
  — je Tradition offizieller Titel und Slug. Die Komponente zeigt hoechstens
  `maxElements` (250) Eintraege; erreicht die Liste diese Zahl, kann sie
  abgeschnitten sein, und das wird gemeldet statt verschwiegen.
* Ein `*` am Titel heisst, so steht es auf jeder dieser Seiten:
  «Aufgenommen in die Repraesentative Liste des immateriellen Kulturerbes der
  UNESCO». Neun Titel tragen ihn.
* Eine Detailseite: Absaetze vor der ersten Zwischenueberschrift sind der
  Beschreibungstext. «Detailbeschreibung» ist kein Text, sondern ein PDF auf
  `backend.lebendige-traditionen.ch` — der Server gibt es als Link aus und
  ruft es nicht ab, deshalb steht der Host nicht in der Allowlist.
  «Kategorie» und «Kanton» sind Links; der Kantonslink traegt das Kuerzel als
  `aria-label`. Ueberregionale Traditionen nennen dort keinen Kanton, sondern
  verweisen auf die Uebersicht; die Seite fuehrt sie unter «Schweiz».
  Verwandte Traditionen stehen in einem Akkordeon gleichen Titels.

Fehlt ein erwarteter Abschnitt, steht er in `fehlende_abschnitte`. Ein Leser,
der Fehlendes stillschweigend leer laesst, liefert eine Antwort, die aussieht
wie eine Tradition ohne Kanton.
"""

from __future__ import annotations

import unicodedata
from html.parser import HTMLParser

from .constants import KANTONE, TRADITIONEN_API, TRADITIONEN_SEITE

LISTE_SLUG = "alle-traditionen"
UNESCO_VERMERK = "Aufgenommen in die Repräsentative Liste des immateriellen Kulturerbes der UNESCO"
ERWARTETE_ABSCHNITTE = ("Kategorie", "Kanton")
# h3/h4 gelten nur mit diesen Namen als Abschnittsgrenze: «Kanton» steht auf
# drei Seiten als h4 statt h2 (Amateurtheater in der Westschweiz,
# Gebaerdensprachen, Viehzucht und Kuhkaempfe). Jede andere Zwischenueberschrift
# bleibt Teil des laufenden Abschnitts, sonst fiele Beschreibungstext weg.
_ABSCHNITTSNAMEN = frozenset({"Detailbeschreibung", *ERWARTETE_ABSCHNITTE})
_VERWANDTE = "Verwandte Traditionen"
_NAME_ZU_KUERZEL = {name: kuerzel for kuerzel, name in KANTONE.items()}
_GANZE_SCHWEIZ = frozenset({"CH", "Schweiz"})
# Platzhalter, mit denen die Quelle «kein einzelner Kanton» ausdrueckt.
_PLATZHALTER = frozenset({"Traditionen nach Kantone", "Traditionen Liste"})


class TraditionenLeseError(ValueError):
    """Die Antwort hat nicht die Form, gegen die dieser Leser geschrieben ist."""


def api_url(slug: str) -> str:
    return f"{TRADITIONEN_API}/{slug}.json"


def seiten_url(slug: str) -> str:
    return f"{TRADITIONEN_SEITE}/de/{slug}"


def buchstabe(name: str) -> str:
    """Der Anfangsbuchstabe ohne Diakritika: «Älplerchilbi» steht unter A."""
    for zeichen in unicodedata.normalize("NFD", name):
        if zeichen.isalpha():
            return zeichen.upper()
    return ""


def _sortierschluessel(name: str) -> str:
    zerlegt = unicodedata.normalize("NFD", name.casefold())
    return "".join(z for z in zerlegt if not unicodedata.combining(z))


def _titel(roh: str) -> tuple[str, bool]:
    """Titel ohne Stern, und ob der Stern da war."""
    roh = (roh or "").strip()
    return roh.rstrip("*").strip(), roh.endswith("*")


def _knoten(baum: list) -> list[tuple[str | None, dict, list]]:
    """Alle Komponenten in Dokumentreihenfolge: (identifier, properties, Kinder)."""
    aus: list[tuple[str | None, dict, list]] = []
    for k in baum or []:
        kinder = k.get("nestedContent") or []
        aus.append((k.get("identifier"), k.get("properties") or {}, kinder))
        aus.extend(_knoten(kinder))
    return aus


class _TextUndLinks(HTMLParser):
    """Text und Links aus einem `text`-Feld (enthaelt `<a>` und `<br>`)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.teile: list[str] = []
        self.links: list[dict[str, str]] = []
        self._link: dict[str, str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "br":
            self.teile.append(" ")
        elif tag == "a":
            a = dict(attrs)
            self._link = {
                "href": a.get("href") or "",
                "label": a.get("aria-label") or "",
                "text": "",
            }

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._link is not None:
            self._link["text"] = " ".join(self._link["text"].split())
            self.links.append(self._link)
            self._link = None

    def handle_data(self, data: str) -> None:
        self.teile.append(data)
        if self._link is not None:
            self._link["text"] += data


def _lies(html_text: str) -> tuple[str, list[dict[str, str]]]:
    leser = _TextUndLinks()
    leser.feed(html_text or "")
    leser.close()
    return " ".join("".join(leser.teile).split()), leser.links


def _interner_slug(href: str) -> str | None:
    if href.startswith("/de/") and href.count("/") == 2:
        return href[len("/de/") :]
    return None


def _kantone_aus(text: str, links: list[dict[str, str]]) -> tuple[list[str], bool]:
    """Kantonskuerzel aus einem Eintrag im Abschnitt «Kanton», und ob «ueberregional».

    Im Inventar vorkommende Formen (alle 228 Seiten am 7.11.2026 gelesen): ein
    Link mit dem Kuerzel als `aria-label` (die Regel), ein Link mit dem vollen
    Namen («Graubuenden», «Aargau»), Kuerzel als Klartext («BE», «JU NE»,
    «LU NW OW SZ UR ZG»), «CH» oder «Schweiz» fuer die ganze Schweiz, und als
    Platzhalter ein Link «Traditionen nach Kantone» oder der Text «Traditionen
    Liste».

    Ueberregional heisst: «CH», «Schweiz» oder einer der Platzhalter. Die 20
    Traditionen, auf die das zutrifft, sind am 7.11.2026 genau die 20, die die
    Seite unter «Schweiz» fuehrt — kein Fall in die eine oder andere Richtung.
    """
    kuerzel: list[str] = []
    ueberregional = False
    for link in links:
        for wert in (link["label"], link["text"]):
            if wert in KANTONE:
                kuerzel.append(wert)
                break
            if wert in _NAME_ZU_KUERZEL:
                kuerzel.append(_NAME_ZU_KUERZEL[wert])
                break
            if wert in _GANZE_SCHWEIZ or wert in _PLATZHALTER:
                ueberregional = True
                break
    if not links:
        if text in _NAME_ZU_KUERZEL:
            kuerzel.append(_NAME_ZU_KUERZEL[text])
        elif text in _PLATZHALTER:
            ueberregional = True
        else:
            woerter = text.replace(",", " ").split()
            kuerzel.extend(w for w in woerter if w in KANTONE)
            ueberregional = any(w in _GANZE_SCHWEIZ for w in woerter)
    return kuerzel, ueberregional


def parse_liste(seite: dict) -> dict:
    """Die Traditionen aus `alle-traditionen.json`, mit der Obergrenze der Komponente."""
    teaser = [
        (props, kinder)
        for ident, props, kinder in _knoten(seite.get("content") or [])
        if ident == "dynamic-page-teaser"
    ]
    if len(teaser) != 1:
        raise TraditionenLeseError(
            f"Uebersicht: {len(teaser)} Listen-Komponenten (dynamic-page-teaser) statt genau einer"
        )
    props, kinder = teaser[0]
    eintraege = []
    for k in kinder:
        if k.get("identifier") != "teaser-item":
            continue
        p = k.get("properties") or {}
        slug = _interner_slug(p.get("slug") or "")
        name, unesco = _titel(p.get("title") or "")
        if not slug or not name:
            raise TraditionenLeseError(f"Uebersicht: Eintrag ohne Titel oder Slug: {p!r:.200}")
        eintraege.append(
            {
                "name": name,
                "slug": slug,
                "url": seiten_url(slug),
                "unesco_repraesentative_liste": unesco,
            }
        )
    if not eintraege:
        raise TraditionenLeseError("Uebersicht: keine einzige Tradition gefunden")
    eintraege.sort(key=lambda e: _sortierschluessel(e["name"]))
    max_elements = props.get("maxElements")
    return {
        "traditionen": eintraege,
        "max_elements": max_elements if isinstance(max_elements, int) else None,
        "aktualisiert": seite.get("updatedAt"),
    }


def parse_detail(seite: dict, slug: str) -> dict:
    """Eine Detailseite: Text, Kantone, Kategorien, Verwandte, PDF."""
    meta = seite.get("metadata") or {}
    titel, unesco = _titel(meta.get("title") or "")
    absaetze: list[str] = []
    kategorien: list[str] = []
    kantone: list[str] = []
    verwandte: list[dict[str, str]] = []
    pdf: str | None = None
    unesco_vermerk = False
    ueberregional = False
    gesehen: set[str] = set()

    def besuche(baum: list, abschnitt: str | None, akkordeon: str | None) -> str | None:
        nonlocal pdf, unesco_vermerk, ueberregional
        for k in baum or []:
            ident = k.get("identifier")
            p = k.get("properties") or {}
            kinder = k.get("nestedContent") or []
            if akkordeon is None and ident == "title":
                continue
            if akkordeon is None and ident in ("heading-h2", "heading-h3", "heading-h4"):
                label = (p.get("label") or "").strip()
                if ident == "heading-h2" or label in _ABSCHNITTSNAMEN:
                    abschnitt = label
                    gesehen.add(label)
                    continue
            if ident == "accordion-container":
                # Ein Akkordeon schliesst den laufenden Abschnitt ab: Was danach
                # kommt, gehoert nicht mehr zu «Kanton» oder «Kategorie».
                besuche(kinder, None, None)
                abschnitt = None
                continue
            if ident == "accordion-item":
                titel_item = ((p.get("accordionItems") or {}).get("title") or "").strip()
                besuche(kinder, None, titel_item)
                continue
            texte = []
            if ident == "p":
                texte = [p.get("text") or ""]
            elif ident == "list":
                texte = [i.get("text") or "" for i in p.get("listItems") or []]
            for roh in texte:
                text, links = _lies(roh)
                if akkordeon == _VERWANDTE:
                    for link in links:
                        s = _interner_slug(link["href"])
                        if s:
                            verwandte.append({"name": _titel(link["text"])[0], "slug": s})
                elif akkordeon is not None:
                    continue
                elif abschnitt is None:
                    if text.lstrip("* ").startswith(UNESCO_VERMERK):
                        unesco_vermerk = True
                    elif text:
                        absaetze.append(text)
                elif abschnitt == "Kategorie":
                    kategorien.extend(link["text"] for link in links if link["text"])
                elif abschnitt == "Kanton":
                    gefunden, marke = _kantone_aus(text, links)
                    kantone.extend(gefunden)
                    ueberregional = ueberregional or marke
            if ident == "manual-download-list" and abschnitt == "Detailbeschreibung":
                for item in p.get("listItems") or []:
                    url = ((item.get("asset") or {}).get("url") or "").strip()
                    if url and pdf is None:
                        pdf = url
            if kinder and ident not in ("p", "list"):
                abschnitt = besuche(kinder, abschnitt, akkordeon)
        return abschnitt

    besuche(seite.get("content") or [], None, None)
    if not titel:
        raise TraditionenLeseError(f"Detailseite {slug}: kein Titel in den Metadaten")
    kantone = list(dict.fromkeys(kantone))
    fehlend = [a for a in ERWARTETE_ABSCHNITTE if a not in gesehen]
    if "Kanton" in gesehen and not kantone and not ueberregional:
        # Ein Abschnitt «Kanton», aus dem weder ein Kanton noch «ganze Schweiz»
        # zu lesen ist, ist nicht lesbar — nicht ueberregional.
        fehlend.append("Kanton")
    ergebnis: dict = {
        "slug": slug,
        "titel": titel,
        "unesco_repraesentative_liste": unesco or unesco_vermerk,
        "beschreibung": absaetze,
        "kategorien": list(dict.fromkeys(kategorien)),
        "kantone": [{"kuerzel": k, "name": KANTONE[k]} for k in kantone],
        "ueberregional": not kantone and ueberregional,
        "verwandte_traditionen": list({v["slug"]: v for v in verwandte}.values()),
        "detailbeschreibung_pdf": pdf,
        "url": seiten_url(slug),
        "aktualisiert": seite.get("updatedAt"),
        "fehlende_abschnitte": fehlend,
    }
    if ergebnis["ueberregional"]:
        ergebnis["kantone_hinweis"] = (
            "Kein einzelner Kanton: Die Quelle fuehrt diese Tradition unter «Schweiz»."
        )
    return ergebnis
