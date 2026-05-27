"""Konstanten und Referenzdaten für swiss-culture-mcp."""

# ---------------------------------------------------------------------------
# Upstream-Endpunkte
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

# Clark-Notation für `nsb:id`-Attribut im News-Service-Bund-RSS
NSB_ID = "{https://www.news.admin.ch/rss}id"

# ---------------------------------------------------------------------------
# Schweizer Kantone — vollständige offizielle Liste (26/26)
# ---------------------------------------------------------------------------

KANTONE = {
    "AG": "Aargau",
    "AI": "Appenzell Innerrhoden",
    "AR": "Appenzell Ausserrhoden",
    "BE": "Bern",
    "BL": "Basel-Landschaft",
    "BS": "Basel-Stadt",
    "FR": "Freiburg",
    "GE": "Genf",
    "GL": "Glarus",
    "GR": "Graubünden",
    "JU": "Jura",
    "LU": "Luzern",
    "NE": "Neuenburg",
    "NW": "Nidwalden",
    "OW": "Obwalden",
    "SG": "St. Gallen",
    "SH": "Schaffhausen",
    "SO": "Solothurn",
    "SZ": "Schwyz",
    "TG": "Thurgau",
    "TI": "Tessin",
    "UR": "Uri",
    "VD": "Waadt",
    "VS": "Wallis",
    "ZG": "Zug",
    "ZH": "Zürich",
}

# Alle gültigen Siedlungskategorien im ISOS
SIEDLUNGSKATEGORIEN = [
    "Stadt",
    "Kleinstadt/Flecken",
    "Dorf",
    "Weiler/Einzelsiedlung",
    "Spezialfall",
    "cas particulier",
    "villaggio",
    "cas spécial",
]
