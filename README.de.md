[🇬🇧 English Version](README.md)

> 🇨🇭 **Teil des [Swiss Public Data MCP Portfolios](https://github.com/malkreide)**

# 🏛️ swiss-culture-mcp

![Version](https://img.shields.io/badge/version-1.0.0-blue)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-purple)](https://modelcontextprotocol.io/)
[![Datenquelle](https://img.shields.io/badge/Daten-BAK%20Open%20Data-red)](https://opendata.swiss/)
![CI](https://github.com/malkreide/swiss-culture-mcp/actions/workflows/ci.yml/badge.svg)

> MCP-Server für Schweizer Kulturdaten des Bundesamts für Kultur (BAK) — ISOS-Ortsbilder, Lebendige Traditionen, Kulturpreise, Medienmitteilungen. Kein API-Schlüssel erforderlich.

---

## Übersicht

**swiss-culture-mcp** macht die Kulturdaten des Bundesamts für Kultur (BAK) für KI-Assistenten zugänglich. Der Server verbindet LLMs wie Claude mit dem nationalen Kulturerbe der Schweiz: von schützenswerten Ortsbildern (ISOS) über lebendige Traditionen des immateriellen Kulturerbes bis hin zu aktuellen Kulturpreisen.

**Quellen:** geo.admin.ch REST API · news.admin.ch RSS · opendata.swiss CKAN · lebendige-traditionen.ch

**Kein API-Schlüssel erforderlich.** Alle Datenquellen sind öffentlich zugänglich (Open Government Data).

**Anker-Demo-Abfrage:** *«Welche schützenswerten Ortsbilder gibt es in den Schulkreisen der Stadt Zürich, und welche lebendigen Traditionen werden dort gepflegt?»*

---

## Funktionen

- 🏘️ **ISOS-Suche** – Bundesinventar schützenswerter Ortsbilder nach Name, Kanton oder Siedlungstyp
- 📜 **Lebendige Traditionen** – 228 Einträge des immateriellen Kulturerbes der Schweiz
- 🏆 **Kulturpreise** – Schweizer Filmpreis, Grand Prix Literatur, Musikpreis und weitere
- 📰 **BAK-Medienmitteilungen** – aktuelle Meldungen des Bundesamts für Kultur
- 📦 **Open-Data-Katalog** – BAK-Datensätze auf opendata.swiss
- ☁️ **Dual Transport** – stdio für Claude Desktop, Streamable HTTP für Cloud-Deployment

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

---

## Datenquellen

| Quelle | API-Typ | Inhalt |
|---|---|---|
| **geo.admin.ch** | REST MapServer | ISOS (Bundesinventar schützenswerter Ortsbilder) |
| **news.admin.ch** | RSS-Feed | BAK-Medienmitteilungen, Kulturpreise |
| **opendata.swiss** | CKAN REST API | BAK Open-Data-Datensätze |
| **lebendige-traditionen.ch** | HTML-Fetch | 228 Einträge immaterielles Kulturerbe |

---

## Voraussetzungen

- Python 3.11+
- `uv` oder `pip`
- Keine API-Schlüssel erforderlich

---

## Installation

```bash
# Empfohlen: uvx (kein Installationsschritt nötig)
uvx swiss-culture-mcp

# Alternativ: pip
pip install swiss-culture-mcp
```

---

## Schnellstart

```bash
# Server starten (stdio-Modus für Claude Desktop)
uvx swiss-culture-mcp
```

Sofort in Claude Desktop ausprobieren:

> *«Zeig mir alle schützenswerten Ortsbilder im Kanton Graubünden»*
> *«Welche lebendigen Traditionen gibt es im Kanton Appenzell?»*
> *«Welche Schweizer Kulturpreise wurden 2026 vergeben?»*

---

## Konfiguration

### Umgebungsvariablen

| Umgebungsvariable | Standard | Beschreibung |
|---|---|---|
| `MCP_TRANSPORT` | `stdio` | Transport: `stdio` oder `streamable_http` |
| `MCP_PORT` | `8000` | Port für HTTP-Transport |

### Claude Desktop Konfiguration

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

**Pfad zur Konfigurationsdatei:**
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

Nach Neustart von Claude Desktop stehen alle Tools zur Verfügung. Beispielfragen:

- «Zeig mir alle schützenswerten Ortsbilder im Kanton Graubünden»
- «Was ist das Alphorn- und Büchelspiel?»
- «Welche Schweizer Kulturpreise wurden 2026 vergeben?»
- «Ist die Altstadt von Stein am Rhein im ISOS-Inventar?»
- «Welche lebendigen Traditionen gibt es im Kanton Appenzell?»

### Cloud-Deployment (Streamable HTTP)

Für den Einsatz via **claude.ai im Browser** (z. B. auf verwalteten Arbeitsplätzen ohne lokale Software-Installation):

**Render.com (empfohlen):**
1. Repository auf GitHub pushen/forken
2. Auf [render.com](https://render.com): New Web Service → GitHub-Repo verbinden
3. Umgebungsvariablen im Render-Dashboard setzen
4. In claude.ai unter Settings → MCP Servers eintragen: `https://your-app.onrender.com/mcp`

```bash
# Docker / lokaler HTTP-Modus
MCP_TRANSPORT=streamable_http MCP_PORT=8000 python -m swiss_culture_mcp.server
```

---

## Architektur

```
┌─────────────────┐     ┌──────────────────────────┐     ┌──────────────────────────┐
│   Claude / KI   │────▶│   Swiss Culture MCP      │────▶│  geo.admin.ch REST       │
│   (MCP Host)    │◀────│   (MCP Server)           │◀────│  news.admin.ch RSS       │
└─────────────────┘     │                          │     │  opendata.swiss CKAN     │
                        │  10 Tools · 3 Resources  │     │  lebendige-traditionen   │
                        │  Stdio | Streamable HTTP  │     └──────────────────────────┘
                        └──────────────────────────┘
```

---

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
├── CONTRIBUTING.md
├── LICENSE
├── README.md                  # Englische Hauptversion
└── README.de.md               # Diese Datei (Deutsch)
```

---

## Tests

```bash
# Unit-Tests (kein API-Key erforderlich)
PYTHONPATH=src pytest tests/ -m "not live"

# Integrationstests (Live-API-Aufrufe)
PYTHONPATH=src pytest tests/ -m "live"
```

---

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
→ bak_search_isos(query="Gemeinde-/Ortsname")

«Welche BAK-Daten stehen für GIS-Integration zur Verfügung?»
→ bak_get_opendata() → WMS/WFS-URLs für GIS-Software
```

### KI-Fachgruppe / Demos

```
«Zeige aktuelle Kulturpolitik des Bundes»
→ bak_get_news() + bak_get_kulturpreise()
```

---

## Bekannte Einschränkungen

- **ISOS-Statistiken:** Stichprobenbasiert pro Kanton (nicht erschöpfend für alle Kantone)
- **Lebendige Traditionen:** HTML-Scraping – kann brechen, wenn lebendige-traditionen.ch seine Struktur ändert
- **BAK-Neuigkeiten/Preise:** RSS-Feed auf die neuesten Einträge beschränkt
- **opendata.swiss CKAN:** Volltextsuche kann Resultate anderer Publisher einschliessen

---

## Synergie mit anderen MCP-Servern

`swiss-culture-mcp` lässt sich mit anderen Servern des Portfolios kombinieren:

| Kombination | Anwendungsfall |
|---|---|
| `+ swiss-transport-mcp` | Kulturtourismus: Tagesreisen zu Traditionen mit ÖV |
| `+ zurich-opendata-mcp` | Lokaler Kulturatlas: ISOS + Zürcher Veranstaltungen |
| `+ global-education-mcp` | Kulturelle Bildung im internationalen Vergleich |
| `+ fedlex-mcp` | Kulturgütertransfergesetz + BAK-Vollzugspraxis |
| `+ swiss-statistics-mcp` | Kulturausgaben nach Kanton (BFS-Daten) |

---

## Changelog

Siehe [CHANGELOG.md](CHANGELOG.md)

---

## Lizenz

MIT-Lizenz – siehe [LICENSE](LICENSE)

---

## Autor

Hayal Oezkan · [malkreide](https://github.com/malkreide)

---

## Credits & Verwandte Projekte

- **Daten:** [Bundesamt für Kultur (BAK)](https://www.bak.admin.ch/) – Federal Office of Culture
- **ISOS:** [geo.admin.ch](https://geo.admin.ch/) – Bundesamt für Landestopografie swisstopo
- **Traditionen:** [lebendige-traditionen.ch](https://www.lebendige-traditionen.ch/) – BAK-Register lebendiger Traditionen
- **Protokoll:** [Model Context Protocol](https://modelcontextprotocol.io/) – Anthropic / Linux Foundation
- **Verwandt:** [zurich-opendata-mcp](https://github.com/malkreide/zurich-opendata-mcp) – MCP-Server für Zürcher Stadtdaten
- **Portfolio:** [Swiss Public Data MCP Portfolio](https://github.com/malkreide)
