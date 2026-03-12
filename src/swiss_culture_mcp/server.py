"""
swiss-culture-mcp: MCP-Server für Schweizer Kulturdaten des Bundesamts für Kultur (BAK)

Datenquellen:
  - geo.admin.ch REST API: ISOS (Bundesinventar schützenswerte Ortsbilder)
  - news.admin.ch RSS: BAK Medienmitteilungen und Kulturpreise
  - opendata.swiss CKAN API: BAK Open-Data-Datensätze
  - lebendige-traditionen.ch: Immaterielle Kulturgüter (HTML-Fetch)

Kein API-Schlüssel erforderlich. Alle Quellen sind öffentlich zugänglich.
"""

import json
import os
import xml.etree.ElementTree as ET
from enum import Enum
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Konstanten
# ---------------------------------------------------------------------------

GEO_ADMIN_BASE = "https://api3.geo.admin.ch/rest/services/all/MapServer"
GEO_ADMIN_SEARCH = "https://api3.geo.admin.ch/rest/services/api/SearchServer"
ISOS_LAYER = "ch.bak.bundesinventar-schuetzenswerte-ortsbilder"
ISOS_2021_LAYER = "ch.bak.bundesinventar-schuetzenswerte-ortsbilder-ab-2021"

CKAN_BASE = "https://opendata.swiss/api/3/action"
BAK_ORG = "bundesamt-fur-kultur-bak"

RSS_BASE = "https://www.newsd.admin.ch/newsd/feeds/rss"
BAK_ORG_NR = "314"  # BAK-Organisations-ID im News Service Bund

TRADITIONS_BASE = "https://www.lebendige-traditionen.ch/tradition/de/home"

GISOS_BASE = "https://www.gisos.bak.admin.ch/sites"

TIMEOUT = 20.0

# Kantonskürzel → offizieller Name
KANTONE = {
    "AG": "Aargau", "AI": "Appenzell Innerrhoden", "AR": "Appenzell Ausserrhoden",
    "BE": "Bern", "BL": "Basel-Landschaft", "BS": "Basel-Stadt",
    "FR": "Freiburg", "GE": "Genf", "GL": "Glarus",
    "GR": "Graubünden", "JU": "Jura", "LU": "Luzern",
    "NE": "Neuenburg", "NW": "Nidwalden", "OW": "Obwalden",
    "SG": "St. Gallen", "SH": "Schaffhausen", "SO": "Solothurn",
    "SZ": "Schwyz", "TG": "Thurgau", "TI": "Tessin",
    "UR": "Uri", "VD": "Waadt", "VS": "Wallis",
    "ZG": "Zug", "ZH": "Zürich",
}

# Alle gültigen Siedlungskategorien im ISOS
SIEDLUNGSKATEGORIEN = [
    "Stadt", "Kleinstadt/Flecken", "Dorf", "Weiler/Einzelsiedlung",
    "Spezialfall", "cas particulier", "villaggio", "cas spécial",
]

# ---------------------------------------------------------------------------
# Server-Initialisierung
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "swiss_culture_mcp",
    instructions=(
        "MCP-Server für Schweizer Kulturdaten des Bundesamts für Kultur (BAK). "
        "Enthält Tools für ISOS (Bundesinventar schützenswerte Ortsbilder), "
        "BAK Medienmitteilungen, Kulturpreise, Open-Data-Datensätze und "
        "Lebendige Traditionen. Alle Daten sind öffentlich und kein API-Schlüssel nötig."
    ),
)

# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

async def _get(url: str, params: Optional[dict] = None) -> dict:
    """HTTP GET mit einheitlichem Error-Handling."""
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()


async def _get_text(url: str, params: Optional[dict] = None) -> str:
    """HTTP GET, gibt rohen Text zurück (für HTML/XML)."""
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
        response = await client.get(url, params=params, headers={
            "User-Agent": "swiss-culture-mcp/1.0 (https://github.com/malkreide/swiss-culture-mcp)"
        })
        response.raise_for_status()
        return response.text


def _handle_error(e: Exception) -> str:
    """Einheitliche, handlungsorientierte Fehlermeldungen auf Deutsch."""
    if isinstance(e, httpx.HTTPStatusError):
        code = e.response.status_code
        if code == 404:
            return "Fehler: Ressource nicht gefunden. Bitte Suchbegriff oder ID prüfen."
        if code == 403:
            return "Fehler: Zugriff verweigert. Die Ressource ist möglicherweise nicht öffentlich."
        if code == 429:
            return "Fehler: Anfragelimit überschritten. Bitte etwas warten und erneut versuchen."
        if code >= 500:
            return f"Fehler: Server-Fehler (HTTP {code}). Die API ist möglicherweise vorübergehend nicht verfügbar."
        return f"Fehler: HTTP {code} – {e.response.text[:200]}"
    if isinstance(e, httpx.TimeoutException):
        return "Fehler: Zeitüberschreitung. Die API antwortet nicht. Bitte später erneut versuchen."
    if isinstance(e, httpx.ConnectError):
        return "Fehler: Verbindung fehlgeschlagen. Bitte Netzwerkverbindung prüfen."
    return f"Fehler: {type(e).__name__} – {str(e)[:200]}"


def _format_isos_entry(attrs: dict, feature_id: str = "") -> dict:
    """Formatiert ein ISOS-Objekt einheitlich."""
    nummer = attrs.get("nummer", "–")
    return {
        "feature_id": feature_id or attrs.get("id", ""),
        "isos_nummer": nummer,
        "name": attrs.get("name", "–"),
        "kantone": attrs.get("kantone", []),
        "siedlungskategorie": attrs.get("siedlungskategorie", "–"),
        "teil_name": attrs.get("teil_name"),
        "teil_nummer": attrs.get("teil_nummer"),
        "gisos_url": attrs.get("url") or (f"{GISOS_BASE}/{nummer}" if nummer != "–" else ""),
        "isos_url": f"https://www.isos.ch",
    }


NSB_ID = "{https://www.news.admin.ch/rss}id"  # Clark-Notation für nsb:id Attribut


def _parse_rss_items(xml_text: str, max_items: int = 20) -> list[dict]:
    """Parst BAK RSS-Feed und gibt strukturierte Items zurück."""
    root = ET.fromstring(xml_text)
    items = []
    for item in root.findall(".//item")[:max_items]:
        items.append({
            "id": item.attrib.get(NSB_ID, ""),
            "title": item.findtext("title") or "",
            "description": item.findtext("description") or "",
            "link": item.findtext("link") or "",
            "pubDate": item.findtext("pubDate") or "",
            "author": item.findtext("author") or "BAK",
        })
    return items

# ---------------------------------------------------------------------------
# Pydantic Input-Modelle
# ---------------------------------------------------------------------------

class IsosSearchInput(BaseModel):
    """Eingabe für ISOS-Suche nach Ortsname."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    query: str = Field(
        ...,
        description="Ortsname oder Teilname suchen (z.B. 'Zürich', 'Stein am Rhein', 'Bern')",
        min_length=2,
        max_length=100,
    )
    limit: Optional[int] = Field(
        default=20,
        description="Maximale Anzahl Resultate (1–100)",
        ge=1,
        le=100,
    )


class IsosKantonInput(BaseModel):
    """Eingabe für ISOS-Abfrage nach Kanton."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    kanton: str = Field(
        ...,
        description="Kantonskürzel (z.B. 'ZH', 'BE', 'GR'). Gross- oder Kleinschreibung möglich.",
        min_length=2,
        max_length=2,
    )
    limit: Optional[int] = Field(
        default=50,
        description="Maximale Anzahl Resultate (1–500)",
        ge=1,
        le=500,
    )

    @field_validator("kanton")
    @classmethod
    def validate_kanton(cls, v: str) -> str:
        upper = v.upper()
        if upper not in KANTONE:
            raise ValueError(f"Ungültiges Kantonskürzel '{v}'. Gültige Werte: {', '.join(sorted(KANTONE.keys()))}")
        return upper


class IsosDetailInput(BaseModel):
    """Eingabe für ISOS-Detailabfrage."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    feature_id: str = Field(
        ...,
        description="geo.admin.ch Feature-ID des ISOS-Objekts (aus bak_search_isos oder bak_isos_by_kanton)",
        min_length=5,
    )


class IsosKategorieInput(BaseModel):
    """Eingabe für ISOS-Filterung nach Siedlungskategorie."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    kategorie: str = Field(
        ...,
        description=(
            "Siedlungskategorie filtern. Gültige Werte: "
            "'Stadt', 'Kleinstadt/Flecken', 'Dorf', 'Weiler/Einzelsiedlung', 'Spezialfall'"
        ),
    )
    kanton: Optional[str] = Field(
        default=None,
        description="Optional: Kanton einschränken (Kürzel, z.B. 'ZH')",
        min_length=2,
        max_length=2,
    )
    limit: Optional[int] = Field(default=50, ge=1, le=200)


class NewsInput(BaseModel):
    """Eingabe für BAK-Medienmitteilungen."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    limit: Optional[int] = Field(
        default=10,
        description="Anzahl Medienmitteilungen (1–50)",
        ge=1,
        le=50,
    )
    keyword: Optional[str] = Field(
        default=None,
        description="Stichwort für Filterung (z.B. 'Filmpreis', 'Literatur', 'Design')",
        max_length=100,
    )


class KulturpreiseInput(BaseModel):
    """Eingabe für Schweizer Kulturpreise."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    sparte: Optional[str] = Field(
        default=None,
        description=(
            "Kultursparte filtern: 'Film', 'Literatur', 'Design', 'Musik', 'Theater', "
            "'Denkmalpflege' oder leer für alle Preise"
        ),
        max_length=50,
    )
    limit: Optional[int] = Field(default=20, ge=1, le=50)


class OpendataInput(BaseModel):
    """Eingabe für BAK Open-Data-Datensätze."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    query: Optional[str] = Field(
        default=None,
        description="Suchbegriff für BAK-Datensätze auf opendata.swiss (optional)",
        max_length=100,
    )


class TraditionDetailInput(BaseModel):
    """Eingabe für eine spezifische Lebendige Tradition."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    slug: str = Field(
        ...,
        description=(
            "URL-Slug der Tradition (z.B. 'alphorn--und-buechelspiel', 'fasnacht-basel', "
            "'schwingen'). Aus bak_list_traditions oder als bekannte Tradition eingeben."
        ),
        min_length=3,
        max_length=200,
    )


class TraditionListInput(BaseModel):
    """Eingabe für Liste der Lebendigen Traditionen."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    buchstabe: Optional[str] = Field(
        default=None,
        description="Anfangsbuchstabe filtern (A–Z), um Traditionen alphabetisch zu durchsuchen",
        min_length=1,
        max_length=1,
    )


# ---------------------------------------------------------------------------
# Tool 1: ISOS Suche nach Ortsname
# ---------------------------------------------------------------------------

@mcp.tool(
    name="bak_search_isos",
    annotations={
        "title": "ISOS: Ortsbilder nach Name suchen",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def bak_search_isos(params: IsosSearchInput) -> str:
    """Sucht ISOS-Ortsbilder (Bundesinventar der schützenswerten Ortsbilder der Schweiz) nach Ortsname.

    Das ISOS ist das nationale Inventar bedeutender Ortsbilder der Schweiz. Es umfasst
    Städte, Kleinstädte, Dörfer und Weiler von nationaler Bedeutung. Die Daten
    stammen vom Bundesamt für Kultur (BAK) und werden via geo.admin.ch bereitgestellt.

    Args:
        params (IsosSearchInput): Suchparameter mit:
            - query (str): Ortsname oder Teilname
            - limit (int): Maximale Anzahl Resultate (Standard: 20)

    Returns:
        str: JSON mit Liste der gefundenen ISOS-Objekte, je mit:
            - feature_id: ID für bak_get_isos_detail
            - isos_nummer: ISOS-Inventarnummer
            - name: Ortsname
            - kantone: Liste der Kantonskürzel
            - siedlungskategorie: Stadt/Dorf/etc.
            - gisos_url: Link zur GISOS-Detailseite des BAK
    """
    try:
        data = await _get(f"{GEO_ADMIN_BASE}/find", params={
            "layer": ISOS_LAYER,
            "searchText": params.query,
            "searchField": "name",
            "lang": "de",
            "returnGeometry": "false",
        })
        results = data.get("results", [])
        # Deduplizieren nach feature_id
        seen = set()
        unique = []
        for r in results:
            fid = r.get("id") or r.get("featureId", "")
            if fid not in seen:
                seen.add(fid)
                unique.append(r)

        unique = unique[: params.limit]
        formatted = [_format_isos_entry(r.get("attributes", {}), r.get("id", "")) for r in unique]

        return json.dumps(
            {
                "query": params.query,
                "count": len(formatted),
                "total_before_dedup": len(results),
                "results": formatted,
                "hint": "Verwende 'feature_id' mit bak_get_isos_detail für vollständige Details.",
            },
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# Tool 2: ISOS nach Kanton
# ---------------------------------------------------------------------------

@mcp.tool(
    name="bak_isos_by_kanton",
    annotations={
        "title": "ISOS: Ortsbilder eines Kantons",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def bak_isos_by_kanton(params: IsosKantonInput) -> str:
    """Listet alle ISOS-Ortsbilder eines Schweizer Kantons auf.

    Gibt alle im Bundesinventar erfassten schützenswerten Ortsbilder
    des angegebenen Kantons zurück. Kantonskürzel-Format: ZH, BE, GR etc.

    Args:
        params (IsosKantonInput): Parameter mit:
            - kanton (str): Kantonskürzel (z.B. 'ZH', 'GR', 'VS')
            - limit (int): Maximale Anzahl (Standard: 50, max. 500)

    Returns:
        str: JSON mit ISOS-Objekten des Kantons, sortiert nach Name, mit:
            - kanton_name: Vollständiger Kantonsname
            - count: Anzahl gefundener Objekte
            - results: Liste mit feature_id, isos_nummer, name, siedlungskategorie
    """
    try:
        data = await _get(f"{GEO_ADMIN_BASE}/find", params={
            "layer": ISOS_LAYER,
            "searchText": params.kanton,
            "searchField": "kantone",
            "lang": "de",
            "returnGeometry": "false",
        })
        results = data.get("results", [])
        # Deduplizieren
        seen = set()
        unique = []
        for r in results:
            fid = r.get("id") or r.get("featureId", "")
            if fid not in seen:
                seen.add(fid)
                unique.append(r)

        unique_sorted = sorted(
            unique, key=lambda r: r.get("attributes", {}).get("name", "")
        )[: params.limit]

        formatted = [
            _format_isos_entry(r.get("attributes", {}), r.get("id", ""))
            for r in unique_sorted
        ]

        return json.dumps(
            {
                "kanton": params.kanton,
                "kanton_name": KANTONE.get(params.kanton, params.kanton),
                "count": len(formatted),
                "total_in_kanton": len(unique),
                "results": formatted,
            },
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# Tool 3: ISOS Detailabfrage
# ---------------------------------------------------------------------------

@mcp.tool(
    name="bak_get_isos_detail",
    annotations={
        "title": "ISOS: Objekt-Detail abrufen",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def bak_get_isos_detail(params: IsosDetailInput) -> str:
    """Ruft vollständige Details eines ISOS-Ortsbildes anhand der Feature-ID ab.

    Die Feature-ID erhält man aus den Resultaten von bak_search_isos oder
    bak_isos_by_kanton. Liefert alle verfügbaren Attribute des Objekts inkl.
    direktem Link zur GISOS-Dokumentationsseite des BAK.

    Args:
        params (IsosDetailInput): Parameter mit:
            - feature_id (str): geo.admin.ch Feature-ID

    Returns:
        str: JSON mit vollständigen Objekt-Attributen:
            - feature_id, isos_nummer, name, kantone, siedlungskategorie
            - teil_name, teil_nummer (falls vorhanden)
            - gisos_url: Link zur detaillierten BAK-Dokumentation
            - koordinaten: Lage im Schweizer Koordinatensystem (LV03)
    """
    try:
        data = await _get(
            f"{GEO_ADMIN_BASE}/{ISOS_LAYER}/{params.feature_id}",
            params={"lang": "de"},
        )
        feature = data.get("feature", {})
        attrs = feature.get("attributes", {})
        geom = feature.get("geometry", {})

        entry = _format_isos_entry(attrs, feature.get("id", params.feature_id))
        entry["koordinaten_lv03"] = {
            "x": geom.get("x"),
            "y": geom.get("y"),
            "beschreibung": "Schweizer Koordinatensystem LV03 (EPSG:21781)",
        }

        return json.dumps(entry, ensure_ascii=False, indent=2)
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# Tool 4: ISOS nach Siedlungskategorie
# ---------------------------------------------------------------------------

@mcp.tool(
    name="bak_isos_by_kategorie",
    annotations={
        "title": "ISOS: Ortsbilder nach Siedlungskategorie",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def bak_isos_by_kategorie(params: IsosKategorieInput) -> str:
    """Filtert ISOS-Ortsbilder nach Siedlungskategorie (optional kombiniert mit Kanton).

    Ermöglicht die Suche nach spezifischen Siedlungstypen im ISOS-Inventar.
    Kategorien: 'Stadt', 'Kleinstadt/Flecken', 'Dorf', 'Weiler/Einzelsiedlung', 'Spezialfall'.
    Optional kann die Suche auf einen Kanton eingeschränkt werden.

    Args:
        params (IsosKategorieInput): Parameter mit:
            - kategorie (str): Siedlungskategorie
            - kanton (str, optional): Kantonskürzel zur Einschränkung
            - limit (int): Max. Resultate (Standard: 50)

    Returns:
        str: JSON mit gefilterten ISOS-Objekten.
    """
    try:
        # Suche über Siedlungskategorie-Feld
        data = await _get(f"{GEO_ADMIN_BASE}/find", params={
            "layer": ISOS_LAYER,
            "searchText": params.kategorie,
            "searchField": "siedlungskategorie",
            "lang": "de",
            "returnGeometry": "false",
        })
        results = data.get("results", [])

        # Deduplizieren
        seen = set()
        unique = []
        for r in results:
            fid = r.get("id") or r.get("featureId", "")
            if fid not in seen:
                seen.add(fid)
                unique.append(r)

        # Optional: Kanton-Filter
        if params.kanton:
            kanton_upper = params.kanton.upper()
            unique = [
                r for r in unique
                if kanton_upper in (r.get("attributes", {}).get("kantone") or [])
            ]

        unique = unique[: params.limit]
        formatted = [
            _format_isos_entry(r.get("attributes", {}), r.get("id", ""))
            for r in unique
        ]

        return json.dumps(
            {
                "kategorie": params.kategorie,
                "kanton_filter": params.kanton,
                "count": len(formatted),
                "results": formatted,
            },
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# Tool 5: ISOS Statistiken
# ---------------------------------------------------------------------------

@mcp.tool(
    name="bak_isos_statistics",
    annotations={
        "title": "ISOS: Inventar-Statistiken",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def bak_isos_statistics() -> str:
    """Gibt Übersichtsstatistiken zum ISOS-Bundesinventar zurück.

    Zeigt Anzahl ISOS-Objekte pro Kanton sowie Informationen über das Inventar.
    Nützlich für einen schnellen Überblick über den Umfang des Bundesinventars
    der schützenswerten Ortsbilder der Schweiz.

    Returns:
        str: JSON mit:
            - total: Geschätzte Gesamtzahl ISOS-Objekte
            - per_kanton: Objekte pro Kanton (aus repräsentativer Stichprobe)
            - kategorien: Überblick über Siedlungskategorien
            - quellen: Informationen zu Datenquellen und weiterführenden Links
    """
    try:
        # Stichprobe: Zähle Objekte in grossen Kantonen (aus Erfahrungswerten)
        # Vollständige Iteration über alle 26 Kantone wäre 26 API-Calls – zu langsam.
        # Stattdessen: Informationsseite + bekannte Zahlen
        sample_kantone = ["ZH", "BE", "GR", "VS", "VD", "AG", "SO"]
        per_kanton = {}

        for kanton in sample_kantone:
            try:
                data = await _get(f"{GEO_ADMIN_BASE}/find", params={
                    "layer": ISOS_LAYER,
                    "searchText": kanton,
                    "searchField": "kantone",
                    "lang": "de",
                    "returnGeometry": "false",
                })
                results = data.get("results", [])
                seen = set()
                for r in results:
                    seen.add(r.get("id") or r.get("featureId", ""))
                per_kanton[kanton] = {
                    "kanton_name": KANTONE[kanton],
                    "objekte": len(seen),
                }
            except Exception:
                per_kanton[kanton] = {"kanton_name": KANTONE[kanton], "objekte": None}

        return json.dumps(
            {
                "inventar": "ISOS – Bundesinventar der schützenswerten Ortsbilder der Schweiz",
                "betreiber": "Bundesamt für Kultur (BAK)",
                "letzte_aktualisierung": "ISOS wird laufend revidiert (ISOS II ab 2016)",
                "methodologie": "ISOS I (Original) und ISOS II (GIS-Update ab 2016) koexistieren",
                "siedlungskategorien": SIEDLUNGSKATEGORIEN,
                "sample_per_kanton": per_kanton,
                "hinweis": "Stichprobe ausgewählter Kantone. Vollständige Kantone via bak_isos_by_kanton.",
                "links": {
                    "isos_website": "https://www.isos.ch",
                    "gisos_portal": "https://www.gisos.bak.admin.ch",
                    "bak_website": "https://www.bak.admin.ch/bak/de/home/kulturerbe/baukultur.html",
                    "opendata_swiss": f"https://opendata.swiss/de/organization/{BAK_ORG}",
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# Tool 6: BAK Medienmitteilungen
# ---------------------------------------------------------------------------

@mcp.tool(
    name="bak_get_news",
    annotations={
        "title": "BAK: Medienmitteilungen und Aktuelles",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def bak_get_news(params: NewsInput) -> str:
    """Ruft aktuelle Medienmitteilungen des Bundesamts für Kultur (BAK) ab.

    Datenquelle ist der offizielle RSS-Feed des News Service Bund (NSB).
    Enthält Meldungen zu Kulturpreisen, Kulturpolitik, Bundesinventaren,
    Filmförderung, Kulturgütertransfer und weiteren BAK-Themen.

    Args:
        params (NewsInput): Parameter mit:
            - limit (int): Anzahl Meldungen (Standard: 10, max. 50)
            - keyword (str, optional): Stichwort zur Filterung (z.B. 'Filmpreis')

    Returns:
        str: JSON mit Medienmitteilungen, je mit:
            - title: Titel der Meldung
            - description: Kurzbeschreibung
            - pubDate: Datum der Meldung
            - link: URL zur vollständigen Meldung
    """
    try:
        xml_text = await _get_text(RSS_BASE, params={
            "lang": "de",
            "org-nr": BAK_ORG_NR,
        })
        items = _parse_rss_items(xml_text, max_items=params.limit * 3)

        # Keyword-Filter
        if params.keyword:
            keyword_lower = params.keyword.lower()
            items = [
                i for i in items
                if keyword_lower in i["title"].lower()
                or keyword_lower in i["description"].lower()
            ]

        items = items[: params.limit]

        return json.dumps(
            {
                "quelle": "News Service Bund / Bundesamt für Kultur",
                "count": len(items),
                "keyword_filter": params.keyword,
                "items": items,
            },
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# Tool 7: Schweizer Kulturpreise
# ---------------------------------------------------------------------------

@mcp.tool(
    name="bak_get_kulturpreise",
    annotations={
        "title": "BAK: Schweizer Kulturpreise",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def bak_get_kulturpreise(params: KulturpreiseInput) -> str:
    """Ruft Informationen zu Schweizer Kulturpreisen ab.

    Kombiniert aktuelle Preisträger-Meldungen aus dem BAK-RSS-Feed mit
    strukturierten Informationen zu den wichtigsten Kulturpreisen.
    Preise umfassen: Schweizer Filmpreis, Grand Prix Literatur, Grand Prix
    Design, Grand Prix Musik, Prix Meret Oppenheim und weitere.

    Args:
        params (KulturpreiseInput): Parameter mit:
            - sparte (str, optional): 'Film', 'Literatur', 'Design', 'Musik' etc.
            - limit (int): Maximale Anzahl Resultate

    Returns:
        str: JSON mit:
            - aktuelle_preise: Preisträger aus aktuellem/letztem Jahr (aus RSS)
            - preisuebersicht: Statische Übersicht aller BAK-Kulturpreise mit Links
    """
    # Statische Preisübersicht (stabile Referenzdaten)
    preisuebersicht = [
        {
            "name": "Schweizer Filmpreis (Quartz)",
            "sparte": "Film",
            "beschreibung": "Jährlicher Schweizer Filmpreis des BAK für Langfilm, Dokumentarfilm, Kurzfilm, Drehbuch u.a.",
            "url": "https://www.schweizerkulturpreise.ch/de/filmpreis",
            "rhythmus": "jährlich",
        },
        {
            "name": "Schweizer Grand Prix Literatur",
            "sparte": "Literatur",
            "beschreibung": "Höchste Literaturauszeichnung der Schweiz, vergeben vom BAK.",
            "url": "https://www.schweizerkulturpreise.ch/de/literaturpreise",
            "rhythmus": "jährlich",
        },
        {
            "name": "Schweizer Grand Prix Design",
            "sparte": "Design",
            "beschreibung": "Ausgezeichnet werden herausragende Designleistungen auf Empfehlung der Eidg. Designkommission.",
            "url": "https://www.schweizerkulturpreise.ch/de/design",
            "rhythmus": "jährlich",
        },
        {
            "name": "Schweizer Grand Prix Musik",
            "sparte": "Musik",
            "beschreibung": "Höchste Schweizer Auszeichnung für Musiker:innen.",
            "url": "https://www.schweizerkulturpreise.ch/de/musikpreise",
            "rhythmus": "jährlich",
        },
        {
            "name": "Schweizer Grand Prix Theater / Hans-Reinhart-Ring",
            "sparte": "Theater",
            "beschreibung": "Höchste Auszeichnung für Theaterschaffende der Schweiz.",
            "url": "https://www.schweizerkulturpreise.ch/de/theaterpreise",
            "rhythmus": "jährlich",
        },
        {
            "name": "Prix Meret Oppenheim",
            "sparte": "Architektur/Kunst/Kuratieren",
            "beschreibung": "Ausgezeichnet werden Persönlichkeiten aus Architektur, bildender Kunst und Kuratieren.",
            "url": "https://www.schweizerkulturpreise.ch/de/prix-meret-oppenheim",
            "rhythmus": "jährlich",
        },
        {
            "name": "Schweizer Tanzpreis",
            "sparte": "Tanz",
            "beschreibung": "Ausgezeichnet werden Choreograf:innen, Tänzer:innen und Tanzinstitutionen.",
            "url": "https://www.schweizerkulturpreise.ch/de/tanzpreis",
            "rhythmus": "jährlich",
        },
        {
            "name": "Schweizer Kulturpreis Manor",
            "sparte": "Nachwuchs",
            "beschreibung": "Nachwuchsförderpreis, vergeben in Partnerschaft zwischen BAK und Manor AG.",
            "url": "https://www.schweizerkulturpreise.ch",
            "rhythmus": "jährlich",
        },
    ]

    # Sparten-Filter
    if params.sparte:
        sparte_lower = params.sparte.lower()
        preisuebersicht = [
            p for p in preisuebersicht
            if sparte_lower in p["sparte"].lower() or sparte_lower in p["name"].lower()
        ]

    # Aktuelle Preisträger aus RSS
    try:
        xml_text = await _get_text(RSS_BASE, params={"lang": "de", "org-nr": BAK_ORG_NR})
        all_items = _parse_rss_items(xml_text, max_items=50)

        preis_keywords = ["preis", "grand prix", "prix", "filmpreis", "literatur",
                          "design", "musik", "theater", "auszeichnung", "preisträger"]
        if params.sparte:
            preis_keywords.append(params.sparte.lower())

        preis_items = [
            i for i in all_items
            if any(kw in i["title"].lower() or kw in i["description"].lower()
                   for kw in preis_keywords)
        ][:params.limit]

        return json.dumps(
            {
                "preisuebersicht": preisuebersicht,
                "aktuelle_meldungen_aus_rss": preis_items,
                "portal": "https://www.schweizerkulturpreise.ch",
            },
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        # Fallback ohne RSS
        return json.dumps(
            {
                "preisuebersicht": preisuebersicht,
                "aktuelle_meldungen_aus_rss": [],
                "fehler_rss": _handle_error(e),
                "portal": "https://www.schweizerkulturpreise.ch",
            },
            ensure_ascii=False,
            indent=2,
        )


# ---------------------------------------------------------------------------
# Tool 8: BAK Datensätze auf opendata.swiss
# ---------------------------------------------------------------------------

@mcp.tool(
    name="bak_get_opendata",
    annotations={
        "title": "BAK: Open-Data-Datensätze",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def bak_get_opendata(params: OpendataInput) -> str:
    """Listet Open-Data-Datensätze des Bundesamts für Kultur auf opendata.swiss auf.

    Gibt Metadaten zu BAK-Datensätzen zurück, inkl. verfügbare Formate
    (WMS, WFS, API, HTML) und Download-URLs. Relevant für GIS-Integration,
    Datenanalysen und weiterführende Auswertungen.

    Args:
        params (OpendataInput): Parameter mit:
            - query (str, optional): Suchbegriff für Datensätze

    Returns:
        str: JSON mit Datensatz-Metadaten, je mit:
            - name, title, beschreibung
            - formate: Verfügbare Dateiformate
            - ressourcen: URLs für Direktzugriff
            - organisation: BAK
    """
    try:
        ckan_params: dict = {
            "fq": f"organization:{BAK_ORG}",
            "rows": 20,
        }
        if params.query:
            ckan_params["q"] = params.query

        data = await _get(f"{CKAN_BASE}/package_search", params=ckan_params)
        datasets = data.get("result", {}).get("results", [])

        formatted = []
        for ds in datasets:
            ressourcen = [
                {
                    "name": r.get("name", {}).get("de", r.get("name", "")),
                    "format": r.get("format", ""),
                    "url": r.get("download_url") or r.get("access_url") or r.get("url", ""),
                }
                for r in ds.get("resources", [])
                if r.get("download_url") or r.get("access_url") or r.get("url")
            ]
            title = ds.get("title", {})
            if isinstance(title, dict):
                title = title.get("de") or title.get("fr") or next(iter(title.values()), "")

            desc = ds.get("description", {})
            if isinstance(desc, dict):
                desc = desc.get("de") or desc.get("fr") or next(iter(desc.values()), "")

            formatted.append({
                "name": ds.get("name", ""),
                "title": title,
                "beschreibung": (desc or "")[:300],
                "formate": list({r.get("format", "") for r in ds.get("resources", []) if r.get("format")}),
                "ressourcen": ressourcen[:5],
                "opendata_url": f"https://opendata.swiss/de/dataset/{ds.get('name', '')}",
                "letzte_aenderung": ds.get("metadata_modified", ""),
            })

        return json.dumps(
            {
                "organisation": "Bundesamt für Kultur (BAK)",
                "query": params.query,
                "count": len(formatted),
                "total": data.get("result", {}).get("count", len(formatted)),
                "datasets": formatted,
                "portal": f"https://opendata.swiss/de/organization/{BAK_ORG}",
            },
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# Tool 9: Lebendige Traditionen – Übersichtsliste
# ---------------------------------------------------------------------------

@mcp.tool(
    name="bak_list_traditions",
    annotations={
        "title": "BAK: Lebendige Traditionen – Liste",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def bak_list_traditions(params: TraditionListInput) -> str:
    """Listet lebendige Traditionen der Schweiz vom offiziellen BAK-Inventar auf.

    Die «Liste der lebendigen Traditionen der Schweiz» umfasst 228 Einträge
    (Stand 2023) des immateriellen Kulturerbes: Bräuche, Feste, Handwerk,
    Musik, Sprache und weiteres. Optional nach Anfangsbuchstabe filtern.

    Args:
        params (TraditionListInput): Parameter mit:
            - buchstabe (str, optional): Anfangsbuchstabe filtern (A–Z)

    Returns:
        str: JSON mit Liste der Traditionen, je mit:
            - name: Bezeichnung der Tradition
            - slug: URL-Slug für bak_get_tradition_detail
            - url: Direktlink zur BAK-Seite
    """
    try:
        html = await _get_text(f"{TRADITIONS_BASE}/liste/liste.html")
        import re

        links = re.findall(
            r'href="(/tradition/de/home/traditionen/([^"]+\.html))"',
            html
        )
        # Deduplizieren, Slug extrahieren
        seen_slugs = set()
        traditions = []
        for path, slug_html in links:
            slug = slug_html.replace(".html", "")
            if slug in seen_slugs:
                continue
            seen_slugs.add(slug)
            name = slug.replace("--", " – ").replace("-", " ").title()
            traditions.append({
                "slug": slug,
                "name_aus_slug": name,
                "url": f"https://www.lebendige-traditionen.ch{path}",
            })

        # Buchstaben-Filter
        if params.buchstabe:
            letter = params.buchstabe.upper()
            traditions = [t for t in traditions if t["name_aus_slug"].upper().startswith(letter)]

        traditions = sorted(traditions, key=lambda t: t["name_aus_slug"])

        return json.dumps(
            {
                "inventar": "Liste der lebendigen Traditionen der Schweiz",
                "betreiber": "Bundesamt für Kultur (BAK)",
                "aktualisiert": "2023 (228 Einträge)",
                "buchstabe_filter": params.buchstabe,
                "count": len(traditions),
                "traditions": traditions,
                "hinweis": (
                    "Verwende 'slug' mit bak_get_tradition_detail für vollständige Beschreibung. "
                    "Namen aus URL-Slug generiert – offizielle Bezeichnung auf Detailseite prüfen."
                ),
                "portal": "https://www.lebendige-traditionen.ch",
            },
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# Tool 10: Lebendige Tradition – Detailseite
# ---------------------------------------------------------------------------

@mcp.tool(
    name="bak_get_tradition_detail",
    annotations={
        "title": "BAK: Lebendige Tradition – Details",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def bak_get_tradition_detail(params: TraditionDetailInput) -> str:
    """Ruft die Detailbeschreibung einer lebendigen Tradition vom BAK-Inventar ab.

    Holt die offizielle Beschreibung einer Tradition von lebendige-traditionen.ch.
    Den Slug erhält man aus bak_list_traditions oder als bekannte Kurzbezeichnung.

    Bekannte Slugs (Auswahl):
    - 'fasnacht-basel' → Basler Fasnacht
    - 'schwingen' → Schwingen
    - 'alphorn--und-buechelspiel' → Alphorn- und Büchelspiel
    - 'sgrafitto' → Sgrafitto-Technik (GR)
    - 'winzerfest-vevey' → Fête des Vignerons
    - 'appenzeller-silvesterklaus' → Appenzeller Silvesterklaus

    Args:
        params (TraditionDetailInput): Parameter mit:
            - slug (str): URL-Slug der Tradition

    Returns:
        str: JSON mit:
            - titel: Offizieller Name der Tradition
            - beschreibung: Volltext-Beschreibung
            - kantone_mention: Im Text erwähnte Kantone (heuristisch)
            - url: Direktlink zur BAK-Seite
    """
    try:
        import re
        url = f"{TRADITIONS_BASE}/traditionen/{params.slug}.html"
        html = await _get_text(url)

        # Titel extrahieren
        title_match = re.search(r"<title>([^<|]+)", html)
        titel = title_match.group(1).strip() if title_match else params.slug

        # Description Meta-Tag
        desc_match = re.search(r'<meta name="description" content="([^"]+)"', html)
        beschreibung = desc_match.group(1) if desc_match else ""

        # Weitere Textabschnitte aus <p>-Tags
        p_tags = re.findall(r"<p[^>]*>([^<]{50,})</p>", html)
        text_absaetze = [
            re.sub(r"<[^>]+>", "", p).strip()
            for p in p_tags[:5]
            if len(p.strip()) > 50
        ]

        # Kantone heuristisch erkennen
        kanton_namen = list(KANTONE.values())
        content_lower = html.lower()
        erwähnte_kantone = [
            name for name in kanton_namen
            if name.lower() in content_lower
        ]

        return json.dumps(
            {
                "slug": params.slug,
                "titel": titel,
                "meta_beschreibung": beschreibung,
                "text_absaetze": text_absaetze,
                "erwaehnte_kantone": erwähnte_kantone[:10],
                "url": url,
                "inventar": "Liste der lebendigen Traditionen der Schweiz",
                "hinweis": "Beschreibung aus HTML extrahiert. Vollständige Dokumentation auf der Webseite.",
            },
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------

@mcp.resource("bak://isos/kantone")
async def resource_isos_kantone() -> str:
    """Liste aller Schweizer Kantone mit Kürzel und Name für ISOS-Abfragen."""
    return json.dumps(
        {
            "beschreibung": "Gültige Kantonskürzel für bak_isos_by_kanton",
            "kantone": [
                {"kuerzel": k, "name": v}
                for k, v in sorted(KANTONE.items())
            ],
        },
        ensure_ascii=False,
        indent=2,
    )


@mcp.resource("bak://isos/kategorien")
async def resource_isos_kategorien() -> str:
    """Verfügbare Siedlungskategorien im ISOS-Bundesinventar."""
    return json.dumps(
        {
            "beschreibung": "Gültige Siedlungskategorien für bak_isos_by_kategorie",
            "kategorien": SIEDLUNGSKATEGORIEN,
        },
        ensure_ascii=False,
        indent=2,
    )


@mcp.resource("bak://kulturpreise/uebersicht")
async def resource_kulturpreise() -> str:
    """Statische Übersicht aller Schweizer Kulturpreise des BAK."""
    return json.dumps(
        {
            "quelle": "Bundesamt für Kultur (BAK)",
            "portal": "https://www.schweizerkulturpreise.ch",
            "preise": [
                "Schweizer Filmpreis (Quartz)",
                "Schweizer Grand Prix Literatur",
                "Schweizer Grand Prix Design",
                "Schweizer Grand Prix Musik",
                "Schweizer Grand Prix Theater / Hans-Reinhart-Ring",
                "Prix Meret Oppenheim (Architektur, Kunst, Kuratieren)",
                "Schweizer Tanzpreis",
                "Schweizer Kulturpreis Manor (Nachwuchs)",
            ],
        },
        ensure_ascii=False,
        indent=2,
    )


# ---------------------------------------------------------------------------
# Einstiegspunkt
# ---------------------------------------------------------------------------

def main() -> None:
    """Startet den MCP-Server. Transport via Umgebungsvariable konfigurierbar."""
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    port = int(os.getenv("MCP_PORT", "8000"))

    if transport == "streamable_http":
        mcp.run(transport="streamable_http", host="0.0.0.0", port=port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
