[🇬🇧 English Version](README_EN.md)

# swiss-culture-mcp

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![Tests](https://img.shields.io/badge/tests-36%20bestanden-brightgreen)

> MCP-Server für Schweizer Kulturdaten des Bundesamts für Kultur (BAK) — ISOS, Lebendige Traditionen, Kulturpreise, Medienmitteilungen. Kein API-Schlüssel erforderlich.

## Übersicht

`swiss-culture-mcp` macht die Kulturdaten des Bundesamts für Kultur (BAK) für KI-Assistenten zugänglich. Der Server verbindet LLMs wie Claude mit dem nationalen Kulturerbe der Schweiz: von schützenswerten Ortsbildern über lebendige Traditionen bis hin zu aktuellen Kulturpreisen.

**Quellen:** geo.admin.ch REST API · news.admin.ch RSS · opendata.swiss CKAN · lebendige-traditionen.ch

**Kein API-Schlüssel erforderlich.** Alle Datenquellen sind öffentlich zugänglich (Open Data / Open Government Data).

## Funktionen

| # | Tool | Beschreibung |
|---|---|---|
| 1 | `bak_search_isos` | ISOS-Ortsbilder nach Ortsname suchen |
| 2 | `bak_isos_by_kanton` | Alle ISOS-Objekte eines Kantons auflisten |
| 3 | `bak_get_isos_detail` | Volldetails eines ISOS-Objekts abrufen |
| 4 | `bak_isos_by_kategorie` | ISOS nach Siedlungstyp filtern (Stadt, Dorf, etc.) |
| 5 | `bak_isos_statistics` | ISOS-Inventarstatistiken (Stichprobe nach Kanton) |
| 6 | `bak_get_news` | Aktuelle BAK-Medienmitteilungen |
| 7 | `bak_get_kulturpreise` | Schweizer Kulturpreise (Filmpreis, Grand Prix Literatur, etc.) |
| 8 | `bak_get_opendata` | BAK-Datensätze auf opendata.swiss |
| 9 | `bak_list_traditions` | Lebendige Traditionen der Schweiz auflisten |
| 10 | `bak_get_tradition_detail` | Tradition im Detail abrufen |

**3 Resources:** `bak://isos/kantone` · `bak://isos/kategorien` · `bak://kulturpreise/uebersicht`

### Datenquellen

| Quelle | API-Typ | Inhalt |
|---|---|---|
| **geo.admin.ch** | REST MapServer | ISOS (Bundesinventar schützenswerte Ortsbilder) |
| **news.admin.ch** | RSS-Feed | BAK-Medienmitteilungen, Kulturpreise |
| **opendata.swiss** | CKAN REST API | BAK Open-Data-Datensätze |
| **lebendige-traditionen.ch** | HTML-Fetch | 228 Einträge immaterielles Kulturerbe |

## Voraussetzungen

- Python 3.11+
- `uv` oder `pip`
- Keine API-Schlüssel erforderlich

## Installation

```bash
# Empfohlen: uvx (kein Installationsschritt nötig)
uvx swiss-culture-mcp

# Alternativ: pip
pip install swiss-culture-mcp
```

## Verwendung

### Claude Desktop

Konfigurationsdatei öffnen:
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "swiss-culture": {
      "command": "uvx",
      "args": ["swiss-culture-mcp"]
    }
  }
}
```

Nach Neustart von Claude Desktop stehen alle Tools zur Verfügung. Beispielfragen:

- «Zeig mir alle schützenswerten Ortsbilder im Kanton Graubünden»
- «Was ist das Alphorn- und Büchelspiel?»
- «Welche Schweizer Kulturpreise wurden 2026 vergeben?»
- «Ist die Altstadt von Stein am Rhein im ISOS-Inventar?»
- «Welche lebendigen Traditionen gibt es im Kanton Appenzell?»

### Lokale Entwicklung

```bash
git clone https://github.com/malkreide/swiss-culture-mcp.git
cd swiss-culture-mcp
pip install -e ".[dev]"

# Tests ausführen
pytest                          # Unit-Tests (Mocks)
pytest --run-live               # + Live-API-Tests

# Server starten
python -m swiss_culture_mcp.server
```

### Cloud-Deployment (Render.com)

```bash
# Streamable HTTP-Transport
MCP_TRANSPORT=streamable_http MCP_PORT=8000 python -m swiss_culture_mcp.server
```

## Konfiguration

| Umgebungsvariable | Standard | Beschreibung |
|---|---|---|
| `MCP_TRANSPORT` | `stdio` | Transport: `stdio` oder `streamable_http` |
| `MCP_PORT` | `8000` | Port für HTTP-Transport |

## Projektstruktur

```
swiss-culture-mcp/
├── src/
│   └── swiss_culture_mcp/
│       ├── __init__.py
│       └── server.py          # Alle 10 Tools, 3 Resources
├── tests/
│   ├── conftest.py            # pytest-Konfiguration
│   └── test_server.py         # 36 Tests (Unit + Live)
├── pyproject.toml
├── CHANGELOG.md
├── LICENSE
└── README.md
```

## Anwendungsbeispiele

### Schulamt / Bildung

```
«Welche schützenswerten Ortsbilder gibt es in den Schulkreisen der Stadt Zürich?»
→ bak_isos_by_kanton(kanton="ZH") + bak_get_isos_detail(...)

«Finde lebendige Traditionen für eine Projektwoche zum Thema Kulturerbe»
→ bak_list_traditions() + bak_get_tradition_detail(slug="...")

«Welche UNESCO-Welterbestätten sind auch im ISOS?»
→ bak_search_isos(query="...") + bak_get_opendata(query="UNESCO")
```

### Stadtverwaltung / Raumplanung

```
«Ist das Gebäude an der Adresse X in einem ISOS-Perimeter?»
→ bak_search_isos(query="Gemeinschaft-/Ortsname")

«Welche BAK-Daten stehen für GIS-Integration zur Verfügung?»
→ bak_get_opendata() → WMS/WFS-URLs für GIS-Software
```

### KI-Fachgruppe / Demos

```
«Zeige aktuelle Kulturpolitik des Bundes»
→ bak_get_news() + bak_get_kulturpreise()
```

## Synergie mit anderen MCP-Servern

`swiss-culture-mcp` lässt sich mit anderen Servern des Portfolios kombinieren:

| Kombination | Anwendungsfall |
|---|---|
| `+ swiss-transport-mcp` | Kulturtourismus: Tagesreisen zu Traditionen mit ÖV |
| `+ zurich-opendata-mcp` | Lokaler Kulturatlas: ISOS + Zürcher Veranstaltungen |
| `+ global-education-mcp` | Kulturelle Bildung im internationalen Vergleich |
| `+ fedlex-mcp` | Kulturgütertransfergesetz + BAK-Vollzugspraxis |
| `+ swiss-statistics-mcp` | Kulturausgaben nach Kanton (BFS-Daten) |

## Changelog

Siehe [CHANGELOG.md](CHANGELOG.md)

## Lizenz

MIT License — siehe [LICENSE](LICENSE)

## Autor

Hayal Oezkan · [malkreide](https://github.com/malkreide) · Schulamt der Stadt Zürich

---

*Öffentliche Verwaltung mit öffentlichem Geld sollte öffentliche Werkzeuge produzieren.*
