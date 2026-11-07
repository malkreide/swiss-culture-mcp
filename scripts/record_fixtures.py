#!/usr/bin/env python3
"""Misst, ob die Adressen, die dieser Server baut, etwas liefern.

    python scripts/record_fixtures.py

WARUM ES DAS GIBT. Ein handgeschriebener Mock kodiert die Annahme seines
Autors und kann sie deshalb prinzipiell nicht widerlegen: Produktivcode und
Fixture stammen aus demselben Kopf, derselben Stunde, derselben Lektuere der
Doku. Wo beide irren, irren beide gleich, und die Suite bleibt gruen.

Dieser Server braucht keine Zugangsdaten. Damit ist seine gesamte Adressliste
pruefbar — und genau das war nie geschehen.

WAS DER ERSTE VERGLEICH AM 2026-08-08 ERGAB.

* **Eine ausgegebene Quelle war tot.** `bak_isos_overview` gab
  `.../home/kulturerbe/baukultur.html` als BAK-Website aus; die Seite
  antwortet mit HTTP 404, und der ganze Zweig `.../home/kulturerbe.html`
  ebenfalls.

* **Alles andere trug.** geo.admin.ch, opendata.swiss, gisos, isos,
  schweizerkulturpreise, der News-Service-Feed mit `org-nr=314` und die
  Traditionsseiten liefern echte Inhalte. Das ist ein Nullbefund und gehoert
  trotzdem aufgezeichnet: Ohne ihn faengt der naechste Durchgang bei null an.

EIN BEINAHE-FEHLBEFUND, DER HIERHER GEHOERT. Der erste Testabruf einer
Traditionsseite schlug fehl, weil ICH einen Slug geraten hatte — ein 404, der
wie ein Befund aussah und keiner war. Deshalb zieht dieses Skript die Slugs
aus der Liste, statt sie sich auszudenken.

DER UMBAU VON LEBENDIGE-TRADITIONEN.CH. Am 3.11.2026 brach dieses Skript ab:
Die Listenseite `/tradition/de/home/liste/liste.html` antwortete mit 404, am
16.8.2026 noch mit 200. Die Website ist eine Nuxt-Anwendung geworden und laedt
ihre Inhalte als JSON von `/api/collector/de/<slug>.json`. Das Skript misst
jetzt diese Adressen, haelt fest, dass die alte Liste tot bleibt, und zeichnet
echte Antworten auf: die Liste, eine Tradition mit Kanton und UNESCO-Eintrag
(Basler Fasnacht), eine ueberregionale (Alphorn- und Buechelspiel) und eine,
deren Abschnitt «Kanton» als h4 steht (Gebaerdensprachen). Die frueheren Fixtures dazu waren von Hand geschrieben — sie
hielten die Unit-Tests gruen, waehrend beide Werkzeuge produktiv scheiterten.

OHNE KONTROLLEN BELEGT DAS NICHTS. Zu jeder Messung gehoert ein frei
erfundenes Gegenstueck — ein Pfad, ein Slug, ein Dienst, den es sicher nicht
gibt. Erst der Unterschied macht aus «ich habe eine 404 bekommen» die Aussage
«diese Seite gibt es nicht».

Ohne Aufzeichnungsdatum ist «gemessen» nach zwei Jahren von «angenommen» nicht
mehr zu unterscheiden.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(ROOT / "src"))

# Alle Adressen aus dem Produktivcode. Ein Skript, das andere Adressen fragt
# als der Server baut, misst den falschen Gegenstand — und das faellt niemandem
# auf, weil das Ergebnis plausibel aussieht.
from swiss_culture_mcp.constants import (  # noqa: E402
    BAK_ORG_NR,
    BAK_WEBSITE,
    BAK_WEBSITE_TOT,
    CKAN_BASE,
    GISOS_BASE,
    RSS_BASE,
    TRADITIONEN_LISTE_TOT,
)
from swiss_culture_mcp.traditionen import (  # noqa: E402
    LISTE_SLUG,
    api_url,
    parse_detail,
    parse_liste,
)

# Die Traditionen, deren Antwort als Fixture aufgezeichnet wird: eine mit Kanton
# und UNESCO-Eintrag, eine ueberregionale mit Platzhalter-Link, und eine, auf
# der «Kanton» als h4 statt h2 steht und «CH» die ganze Schweiz meint — drei
# der Formen, die das Inventar am 7.11.2026 tatsaechlich trug.
TRADITIONEN_FIXTURES = ("basler-fasnacht", "alphorn-und-buechelspiel", "gebaerdensprachen")

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; swiss-culture-mcp-fixtures/1.0)"}
GEO = "https://api3.geo.admin.ch/rest/services"


def record() -> int:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    recorded_at = datetime.now(UTC).strftime("%Y-%m-%d")
    entries: list[dict] = []

    def write(name: str, payload: object, url: str, rule: str) -> None:
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        (FIXTURES / name).write_text(text, encoding="utf-8")
        entries.append(
            {
                "name": name,
                "url": url,
                "rule": rule,
                "bytes": len(text.encode("utf-8")),
                "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            }
        )
        print(f"ok  {name:<26} {len(text.encode('utf-8')):>7} B")

    def write_gz(name: str, content: bytes, url: str, rule: str) -> None:
        # Die Antwort unveraendert, gzip mit `mtime=0`: dieselbe Antwort ergibt
        # dieselbe Datei.
        daten = gzip.compress(content, compresslevel=9, mtime=0)
        (FIXTURES / name).write_bytes(daten)
        entries.append(
            {
                "name": name,
                "url": url,
                "rule": f"{rule}. Unkomprimiert {len(content)} B",
                "bytes": len(daten),
                "sha256": hashlib.sha256(daten).hexdigest(),
            }
        )
        print(f"ok  {name:<26} {len(daten):>7} B (gz)")

    with httpx.Client(timeout=90.0, follow_redirects=True, headers=HEADERS) as c:
        sonden = [
            ("geo_mapserver", f"{GEO}/all/MapServer", "die Ebenenliste, aus der ISOS gelesen wird"),
            (
                "geo_searchserver",
                f"{GEO}/api/SearchServer?searchText=Bern&type=locations",
                "die Ortssuche",
            ),
            (
                "kontrolle_geo_erfunden",
                f"{GEO}/all/DiesenDienstGibtEsNicht",
                "KONTROLLE: erfundener Dienst",
            ),
            ("ckan", f"{CKAN_BASE}/package_search?q=kultur&rows=1", "die CKAN-Suche"),
            ("gisos", GISOS_BASE.rsplit("/", 1)[0], "das GIS-Portal, auf das verwiesen wird"),
            ("bak_wurzel", BAK_WEBSITE, "die BAK-Website, die ausgegeben wird"),
            ("bak_baukultur_tot", BAK_WEBSITE_TOT, "die frueher ausgegebene BAK-Seite"),
            (
                "kontrolle_bak_erfunden",
                "https://www.bak.admin.ch/bak/de/home/kulturerbe/diesen-pfad-gibt-es-nicht.html",
                "KONTROLLE: erfundener BAK-Pfad",
            ),
            (
                "rss",
                f"{RSS_BASE}?lang=de&org-nr={BAK_ORG_NR}",
                f"der News-Feed mit org-nr={BAK_ORG_NR}",
            ),
            (
                "kontrolle_rss_erfunden",
                f"{RSS_BASE}?lang=de&org-nr=999999",
                "KONTROLLE: erfundene Organisationsnummer",
            ),
            ("traditionen_liste", api_url(LISTE_SLUG), "die Traditionsliste (JSON)"),
            (
                "traditionen_liste_tot",
                TRADITIONEN_LISTE_TOT,
                "die fruehere Listenseite, seit dem Umbau 404",
            ),
        ]
        adressen: dict[str, dict] = {}
        for label, url, warum in sonden:
            r = c.get(url)
            # Auch festhalten, WO die Anfrage geendet hat. Nur den Status
            # aufzuschreiben machte die Aufzeichnung blind fuer genau den Bruch,
            # den sie sehen soll: `opendata.swiss` lenkte auf
            # `ckan.opendata.swiss` um, der Client folgte, die Fixture notierte
            # brav 200 unter dem Ausgangs-Host — waehrend die Allowlist des
            # Servers das Ziel abwies und jeder Aufruf produktiv scheiterte.
            adressen[label] = {
                "url": url,
                "final_url": str(r.url),
                "final_host": r.url.host,
                "umgeleitet": str(r.url) != url,
                "status": r.status_code,
                "content_type": r.headers.get("content-type", ""),
                "bytes": len(r.content),
                "warum": warum,
            }
            pfeil = f"  -> {r.url.host}" if r.url.host != httpx.URL(url).host else ""
            print(f"    {r.status_code}  {label:<24} {len(r.content):>8} B{pfeil}")

        st = {k: v["status"] for k, v in adressen.items()}

        # -- Die Slugs kommen aus der Liste, nicht aus meinem Kopf ----------
        #
        # Der erste Versuch mit einem geratenen Slug ergab 404 und sah nach
        # einem Befund aus. Er war keiner.
        liste_antwort = c.get(api_url(LISTE_SLUG))
        liste_antwort.raise_for_status()
        slugs = [t["slug"] for t in parse_liste(liste_antwort.json())["traditionen"]]
        if len(slugs) < 5:
            raise SystemExit(
                f"Nur {len(slugs)} Slugs in der Liste gefunden. Entweder hat sich "
                "ihre Form geaendert, oder die Liste ist leer — beides gehoert "
                "geprueft, bevor daraus eine Fixture wird."
            )
        fehlend = sorted(set(TRADITIONEN_FIXTURES) - set(slugs))
        if fehlend:
            raise SystemExit(
                f"Die Fixture-Traditionen {fehlend} stehen nicht mehr in der Liste. "
                "Dann gehoert die Auswahl geprueft, nicht still ersetzt."
            )
        proben = {}
        for s in slugs[:3]:
            r = c.get(api_url(s))
            proben[s] = {"status": r.status_code, "bytes": len(r.content)}
        r = c.get(api_url("diesen-slug-gibt-es-nicht"))
        proben["KONTROLLE_erfundener_slug"] = {"status": r.status_code, "bytes": len(r.content)}
        detail_antworten = {}
        for s in TRADITIONEN_FIXTURES:
            r = c.get(api_url(s))
            r.raise_for_status()
            gelesen = parse_detail(r.json(), s)
            if gelesen["fehlende_abschnitte"]:
                raise SystemExit(
                    f"Die Seite {s} traegt die Abschnitte {gelesen['fehlende_abschnitte']} "
                    "nicht mehr. Erst die Quelle ansehen, dann aufzeichnen."
                )
            detail_antworten[s] = r

        # -- Was tragen muss, damit die Befunde ueberhaupt etwas heissen -----
        for label in ("kontrolle_geo_erfunden", "kontrolle_bak_erfunden"):
            if st[label] != 404:
                raise SystemExit(
                    f"Die Kontrolle {label} antwortet mit {st[label]} statt 404 — "
                    "ohne sie belegen die Befunde unten nichts."
                )
        if proben["KONTROLLE_erfundener_slug"]["status"] != 404:
            raise SystemExit("Ein erfundener Tradition-Slug antwortet nicht mehr mit 404.")
        lebend = [
            "geo_mapserver",
            "geo_searchserver",
            "ckan",
            "gisos",
            "bak_wurzel",
            "traditionen_liste",
        ]
        tot = sorted(x for x in lebend if st[x] != 200)
        if tot:
            raise SystemExit(
                f"Diese Adressen antworten nicht mehr mit 200: {tot}. Das gehoert "
                "behoben, nicht aufgezeichnet."
            )
        if any(p["status"] != 200 for k, p in proben.items() if not k.startswith("KONTROLLE")):
            raise SystemExit(f"Eine Traditionsseite antwortet nicht mehr mit 200: {proben}")
        if st["bak_baukultur_tot"] == 200:
            raise SystemExit(
                "Die BAK-Baukultur-Seite ist zurueck — dann gehoert der Link "
                "wiederhergestellt und der Befund gestrichen."
            )
        if st["traditionen_liste_tot"] == 200:
            raise SystemExit(
                "Die fruehere Traditionsliste antwortet wieder mit 200 — dann "
                "gehoert geprueft, welche Adresse die Quelle jetzt meint."
            )
        if adressen["rss"]["bytes"] <= adressen["kontrolle_rss_erfunden"]["bytes"]:
            raise SystemExit(
                "Der Feed mit der konfigurierten org-nr ist nicht groesser als "
                "der mit einer erfundenen. Dann filtert die Nummer nicht mehr, "
                "und `BAK_ORG_NR` gehoert geprueft."
            )

        write(
            "adressen.json",
            {"recorded_at": recorded_at, "adressen": adressen, "traditionen": proben},
            "api3.geo.admin.ch, opendata.swiss, bak.admin.ch, lebendige-traditionen.ch",
            "Statuscode, Content-Type und Groesse je Adresse, die dieser Server "
            "baut oder ausgibt — samt vier Kontrollen mit erfundenen Werten "
            "(Dienst, Pfad, Organisationsnummer, Tradition-Slug). Die "
            "Traditions-Slugs stammen aus der Liste und nicht aus einem "
            "Einfall: Ein geratener Slug erzeugte beim ersten Versuch einen "
            "404, der wie ein Befund aussah und keiner war",
        )
        write_gz(
            "traditionen_liste.json.gz",
            liste_antwort.content,
            api_url(LISTE_SLUG),
            f"Die Antwort der Traditionsliste, unveraendert: {len(slugs)} Traditionen",
        )
        for s, r in detail_antworten.items():
            write_gz(
                f"tradition_{s}.json.gz",
                r.content,
                api_url(s),
                f"Die Antwort der Detailseite {s}, unveraendert",
            )

    _write_provenance(recorded_at, entries)
    print(f"\nPROVENANCE.md geschrieben, Aufzeichnungsdatum {recorded_at}")
    return 0


def _write_provenance(recorded_at: str, entries: list[dict]) -> None:
    lines = [
        "# Herkunft der Fixtures",
        "",
        "**Erzeugt von `scripts/record_fixtures.py`. Nicht von Hand pflegen.**",
        "",
        f"Aufgezeichnet am **{recorded_at}**.",
        "",
        "Ohne Datum ist «gemessen» nach zwei Jahren von «angenommen» nicht mehr",
        "zu unterscheiden — die Datei sieht gleich aus.",
        "",
        "## Dieser Server braucht keine Zugangsdaten",
        "",
        "Damit ist seine gesamte Adressliste pruefbar. Aufgezeichnet ist",
        "deshalb, ob jede Adresse, die er baut oder als Quelle ausgibt,",
        "tatsaechlich etwas liefert.",
        "",
        "## Vier Kontrollen",
        "",
        "| Kontrolle | Antwort | Was sie traegt |",
        "|---|---|---|",
        "| erfundener geo.admin.ch-Dienst | 404 | die Dienstnamen sind echt |",
        "| erfundener BAK-Pfad | 404 | der 404 der Baukultur-Seite ist echt |",
        "| erfundene News-Organisationsnummer | kleinerer Feed | `org-nr=314` filtert wirklich |",
        "| erfundener Tradition-Slug | 404 | die Slug-Antworten sind echt |",
        "",
        "## Ein Beinahe-Fehlbefund, der hierher gehoert",
        "",
        "Der erste Testabruf einer Traditionsseite schlug fehl, weil ein Slug",
        "geraten worden war. Dieses Skript zieht die Slugs deshalb aus der Liste.",
        "",
        "## Der Umbau von lebendige-traditionen.ch",
        "",
        "Die fruehere Listenseite `/tradition/de/home/liste/liste.html` antwortet",
        "seit dem Umbau mit 404 (festgestellt am 3.11.2026, am 16.8.2026 noch 200).",
        "Die Website laedt ihre Inhalte als JSON von `/api/collector/de/<slug>.json`;",
        "gemessen und aufgezeichnet wird jetzt diese Schnittstelle. Die",
        "`*.json.gz` sind ihre Antworten, unveraendert — keine von Hand",
        "geschriebenen Fixtures mehr.",
        "",
        "Das Skript bricht ab, wenn eine Kontrolle nicht mehr traegt, wenn eine",
        "lebende Adresse stirbt oder wenn die tote zurueckkehrt.",
        "",
    ]
    for e in entries:
        lines += [
            f"## `{e['name']}`",
            "",
            f"- **Quelle:** `{e['url']}`",
            f"- **Aufgezeichnet:** {recorded_at}",
            f"- **Auswahl:** {e['rule']}",
            f"- **Groesse:** {e['bytes']} B",
            f"- **SHA-256:** `{e['sha256']}`",
            "",
        ]
    (FIXTURES / "PROVENANCE.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    try:
        raise SystemExit(record())
    except httpx.HTTPError as exc:
        print(f"FEHLER: Quelle nicht erreichbar: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
