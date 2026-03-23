> 🇨🇭 **Part of the [Swiss Public Data MCP Portfolio](https://github.com/malkreide)**

# 🏛️ swiss-culture-mcp

![Version](https://img.shields.io/badge/version-1.0.0-blue)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-purple)](https://modelcontextprotocol.io/)
[![Data Source](https://img.shields.io/badge/Data-BAK%20Open%20Data-red)](https://opendata.swiss/)
![CI](https://github.com/malkreide/swiss-culture-mcp/actions/workflows/ci.yml/badge.svg)

> MCP server for Swiss cultural heritage data from the Federal Office of Culture (BAK) — ISOS townscapes, Living Traditions, cultural prizes, press releases. No API key required.

[🇩🇪 Deutsche Version](README.de.md)

---

## Overview

**swiss-culture-mcp** makes Swiss cultural data accessible to AI assistants. The server connects LLMs like Claude with Switzerland's national cultural heritage: from protected townscapes (ISOS) to living traditions of intangible cultural heritage and current cultural awards.

**Sources:** geo.admin.ch REST API · news.admin.ch RSS · opendata.swiss CKAN · lebendige-traditionen.ch

**No API key required.** All data sources are publicly available (Open Government Data).

**Anchor demo query:** *"Which protected townscapes are there in the school districts of the city of Zurich, and what living traditions are practised there?"*

---

## Features

- 🏘️ **ISOS search** – Federal Inventory of Swiss Townscapes Worth Protecting by name, canton or settlement type
- 📜 **Living Traditions** – 228 entries of Swiss intangible cultural heritage
- 🏆 **Cultural prizes** – Swiss Film Prize, Grand Prix Literature, Music Prize and more
- 📰 **BAK press releases** – current news from the Federal Office of Culture
- 📦 **Open data catalogue** – BAK datasets on opendata.swiss
- ☁️ **Dual transport** – stdio for Claude Desktop, Streamable HTTP for cloud deployment

| # | Tool | Description |
|---|---|---|
| 1 | `bak_search_isos` | Search ISOS townscapes by place name |
| 2 | `bak_isos_by_kanton` | List all ISOS objects in a canton |
| 3 | `bak_get_isos_detail` | Get full details of an ISOS object |
| 4 | `bak_isos_by_kategorie` | Filter ISOS by settlement type (Stadt, Dorf, etc.) |
| 5 | `bak_isos_statistics` | ISOS inventory statistics (sampled by canton) |
| 6 | `bak_get_news` | Current BAK press releases |
| 7 | `bak_get_kulturpreise` | Swiss cultural prizes (Film Prize, Grand Prix Literature, etc.) |
| 8 | `bak_get_opendata` | BAK datasets on opendata.swiss |
| 9 | `bak_list_traditions` | List Switzerland's Living Traditions |
| 10 | `bak_get_tradition_detail` | Get detailed description of a tradition |

**3 Resources:** `bak://isos/kantone` · `bak://isos/kategorien` · `bak://kulturpreise/uebersicht`

---

## Data Sources

| Source | API Type | Content |
|---|---|---|
| **geo.admin.ch** | REST MapServer | ISOS (Federal Inventory of Swiss Townscapes) |
| **news.admin.ch** | RSS Feed | BAK press releases, cultural prizes |
| **opendata.swiss** | CKAN REST API | BAK open data datasets |
| **lebendige-traditionen.ch** | HTML Fetch | 228 entries of intangible cultural heritage |

---

## Prerequisites

- Python 3.11+
- `uv` or `pip`
- No API keys required

---

## Installation

```bash
# Recommended: uvx (no install step needed)
uvx swiss-culture-mcp

# Alternative: pip
pip install swiss-culture-mcp
```

---

## Quickstart

```bash
# Start the server (stdio mode for Claude Desktop)
uvx swiss-culture-mcp
```

Try it immediately in Claude Desktop:

> *"Show me all protected townscapes in the canton of Graubünden"*
> *"Which living traditions are practised in canton Appenzell?"*
> *"Which Swiss cultural prizes were awarded in 2026?"*

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `MCP_TRANSPORT` | `stdio` | Transport: `stdio` or `streamable_http` |
| `MCP_PORT` | `8000` | Port for HTTP transport |

### Claude Desktop Configuration

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

**Config file locations:**
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

After restarting Claude Desktop, all tools are available. Example queries:

- "Show me all protected townscapes in the canton of Graubünden"
- "What is the Alphorn and Büchelspiel tradition?"
- "Which Swiss cultural prizes were awarded in 2026?"
- "Is the old town of Stein am Rhein in the ISOS inventory?"
- "Which living traditions are practised in canton Appenzell?"

### Cloud Deployment (Streamable HTTP)

For use via **claude.ai in the browser** (e.g. on managed workstations without local software):

**Render.com (recommended):**
1. Push/fork the repository to GitHub
2. On [render.com](https://render.com): New Web Service → connect GitHub repo
3. Set environment variables in the Render dashboard
4. In claude.ai under Settings → MCP Servers, add: `https://your-app.onrender.com/mcp`

```bash
# Docker / local HTTP mode
MCP_TRANSPORT=streamable_http MCP_PORT=8000 python -m swiss_culture_mcp.server
```

---

## Architecture

```
┌─────────────────┐     ┌──────────────────────────┐     ┌──────────────────────────┐
│   Claude / AI   │────▶│   Swiss Culture MCP      │────▶│  geo.admin.ch REST       │
│   (MCP Host)    │◀────│   (MCP Server)           │◀────│  news.admin.ch RSS       │
└─────────────────┘     │                          │     │  opendata.swiss CKAN     │
                        │  10 Tools · 3 Resources  │     │  lebendige-traditionen   │
                        │  Stdio | Streamable HTTP  │     └──────────────────────────┘
                        └──────────────────────────┘
```

---

## Project Structure

```
swiss-culture-mcp/
├── src/
│   └── swiss_culture_mcp/
│       ├── __init__.py
│       └── server.py          # All 10 tools, 3 resources
├── tests/
│   ├── conftest.py            # pytest configuration
│   └── test_server.py         # 36 tests (unit + live)
├── pyproject.toml
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── README.md                  # This file (English)
└── README.de.md               # German version
```

---

## Testing

```bash
# Unit tests (no API key required)
PYTHONPATH=src pytest tests/ -m "not live"

# Integration tests (live API calls)
PYTHONPATH=src pytest tests/ -m "live"
```

---

## Example Use Cases

### Schools / Education

```
"Which protected townscapes are there in the school districts of the city of Zurich?"
→ bak_isos_by_kanton(kanton="ZH") + bak_get_isos_detail(...)

"Find living traditions for a project week on the theme of cultural heritage"
→ bak_list_traditions() + bak_get_tradition_detail(slug="...")

"Which UNESCO World Heritage Sites are also in ISOS?"
→ bak_search_isos(query="...") + bak_get_opendata(query="UNESCO")
```

### City Administration / Spatial Planning

```
"Is the building at address X within an ISOS perimeter?"
→ bak_search_isos(query="community/place name")

"Which BAK datasets are available for GIS integration?"
→ bak_get_opendata() → WMS/WFS URLs for GIS software
```

### AI Working Group / Demos

```
"Show current cultural policy of the federal government"
→ bak_get_news() + bak_get_kulturpreise()
```

---

## Known Limitations

- **ISOS statistics:** Sample-based per canton (not exhaustive for all cantons)
- **Living Traditions:** HTML scraping – may break if lebendige-traditionen.ch changes its structure
- **BAK news/prizes:** RSS feed limited to the most recent entries
- **opendata.swiss CKAN:** Full-text search may return results from other publishers

---

## Synergies with Other MCP Servers

`swiss-culture-mcp` can be combined with other servers in the portfolio:

| Combination | Use Case |
|---|---|
| `+ swiss-transport-mcp` | Cultural tourism: day trips to traditions by public transport |
| `+ zurich-opendata-mcp` | Local cultural atlas: ISOS + Zurich city events |
| `+ global-education-mcp` | Cultural education in international comparison |
| `+ fedlex-mcp` | Cultural property transfer act + BAK enforcement practice |
| `+ swiss-statistics-mcp` | Cultural expenditure by canton (BFS data) |

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md)

---

## License

MIT License — see [LICENSE](LICENSE)

---

## Author

Hayal Oezkan · [malkreide](https://github.com/malkreide)

---

## Credits & Related Projects

- **Data:** [Bundesamt für Kultur (BAK)](https://www.bak.admin.ch/) – Federal Office of Culture
- **ISOS:** [geo.admin.ch](https://geo.admin.ch/) – Federal Office of Topography swisstopo
- **Traditions:** [lebendige-traditionen.ch](https://www.lebendige-traditionen.ch/) – BAK living traditions registry
- **Protocol:** [Model Context Protocol](https://modelcontextprotocol.io/) – Anthropic / Linux Foundation
- **Related:** [zurich-opendata-mcp](https://github.com/malkreide/zurich-opendata-mcp) – MCP server for Zurich city open data
- **Portfolio:** [Swiss Public Data MCP Portfolio](https://github.com/malkreide)
