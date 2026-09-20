> 🇨🇭 **Teil des [Swiss Public Data MCP Portfolios](https://github.com/malkreide)**

# 🏛️ swiss-culture-mcp

![Version](https://img.shields.io/badge/version-1.2.0-blue)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-purple)](https://modelcontextprotocol.io/)
[![Datenquelle](https://img.shields.io/badge/Daten-BAK%20Open%20Data-red)](https://opendata.swiss/)
![CI](https://github.com/malkreide/swiss-culture-mcp/actions/workflows/ci.yml/badge.svg)

🌐 **[English](README.md)** | **Deutsch**

> MCP-Server für Schweizer Kulturdaten des Bundesamts für Kultur (BAK) — ISOS-Ortsbilder, Lebendige Traditionen, Kulturpreise, Medienmitteilungen. Kein API-Schlüssel erforderlich.

<p align="center">
  <img src="assets/demo-flow.svg" alt="Demo: Claude fragt ISOS-Ortsbilder via MCP Tool Call ab" width="780">
</p>

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
| `MCP_TRANSPORT` | `stdio` | Transport: `stdio` oder `streamable_http` (`streamable-http` wird ebenso angenommen). Die Aera `2026-07-28` ist nur ueber den HTTP-Transport erreichbar. |
| `MCP_HOST` | `127.0.0.1` | Bind-Host für HTTP-Transport (per Default loopback) |
| `MCP_PORT` | `8000` | Port für HTTP-Transport |
| `MCP_ALLOW_PUBLIC_BIND` | `false` | Wenn `true`, erlaubt Binding auf `0.0.0.0` ohne Auth. **Nur** hinter authentifizierendem Reverse-Proxy setzen (z. B. Cloudflare Access, oauth2-proxy). |
| `MCP_ALLOWED_HOSTS` | *(leer)* | Kommagetrennte Hostnamen, unter denen dieser Server antwortet, **ohne Schema** (`mcp.example.ch`). Speist die Host-/Origin-Pruefung des HTTP-Transports. **Bei jedem Nicht-Loopback-Deployment setzen** — siehe Warnung unten. Loopback bleibt in jedem Fall erlaubt, damit der Healthcheck des Containers weiter funktioniert. |
| `ALLOWED_ORIGINS` | *(leer)* | Kommagetrennte CORS-Origins, mit Schema (`https://claude.ai`). Leer heisst: kein browserbasierter MCP-Client zugelassen; stdio und Nicht-Browser-Clients sind nicht betroffen. `*` ist moeglich, wird aber als Warnung protokolliert. |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` — strukturierte JSON-Logs auf stderr |

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

Die Connector-URL ist immer der Host des Deployments plus der Transportpfad:
**`https://<host>/mcp`**. Eintragen in claude.ai unter Settings → MCP Servers.

**Render.com (empfohlen):**
1. Repository auf GitHub pushen/forken
2. Auf [render.com](https://render.com): New Web Service → GitHub-Repo verbinden
3. Umgebungsvariablen im Render-Dashboard setzen — darunter
   `MCP_ALLOWED_HOSTS=your-app.onrender.com`
4. In claude.ai unter Settings → MCP Servers eintragen: `https://your-app.onrender.com/mcp`

**Docker.** Das Repository liefert ein mehrstufiges [`Dockerfile`](Dockerfile)
(`python:3.13-slim`, non-root, TCP-Healthcheck). Es setzt Transport,
`0.0.0.0`-Binding und `MCP_ALLOW_PUBLIC_BIND=true` vor, weil im Container der
Edge-Proxy der Plattform der einzige Weg hinein ist. `MCP_ALLOWED_HOSTS` bleibt
im Image bewusst ungesetzt — der Hostname hängt davon ab, wohin deployt wird,
und ein geratener wiese jede echte Anfrage mit HTTP 421 ab:

```bash
docker build -t swiss-culture-mcp .
docker run -p 8000:8000 -e MCP_ALLOWED_HOSTS=mcp.example.ch swiss-culture-mcp
```

```bash
# Lokaler HTTP-Modus (nur loopback — sicherer Default, keine Allowlist nötig)
MCP_TRANSPORT=streamable_http MCP_PORT=8000 python -m swiss_culture_mcp.server

# Öffentliches Binding (GEFÄHRLICH — nur hinter authentifizierendem Reverse-Proxy)
MCP_TRANSPORT=streamable_http MCP_HOST=0.0.0.0 MCP_ALLOW_PUBLIC_BIND=true \
    MCP_ALLOWED_HOSTS=mcp.example.ch python -m swiss_culture_mcp.server
```

> ⚠️ **Sicherheit:** Der Server selbst hat keine Authentifizierung. Ein Binding
> auf eine öffentliche Schnittstelle ohne vorgelagerten Auth-Layer macht ihn zum
> offenen Proxy für die Bundesdaten-Quellen. Vor `0.0.0.0`-Deployments immer
> einen authentifizierenden Reverse-Proxy (Cloudflare Access, oauth2-proxy,
> nginx + auth_request) vorschalten.

> ⚠️ **Bei öffentlichem Binding `MCP_ALLOWED_HOSTS` setzen.** Ohne sie werden
> `Host` und `Origin` **überhaupt nicht geprüft**, und der Server steht offen
> für DNS-Rebinding: Ein Angreifer lässt den Browser des Opfers auf ihn zeigen
> und spricht ihn unter fremdem `Host` an. Der Server protokolliert bei jedem
> solchen Start `dns_rebinding_protection_off` — diese Zeile ist das Symptom,
> keine Formalie. Ein Loopback-Binding braucht keine Allowlist; das SDK leitet
> dort selbst eine aus dem Bind-Host ab.

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
├── CONTRIBUTING.md            # Beitragsleitfaden (Englisch)
├── CONTRIBUTING.de.md         # Beitragsleitfaden (Deutsch)
├── SECURITY.md               # Sicherheitsrichtlinie & -posture (Englisch)
├── SECURITY.de.md            # Sicherheitsrichtlinie & -posture (Deutsch)
├── LICENSE
├── README.md                  # Englische Hauptversion
└── README.de.md               # Diese Datei (Deutsch)
```

---

## MCP-Protokollversion

Dieser Server bedient **zwei Protokoll-Aeren** ueber denselben Endpunkt. Die
erste Anfrage einer Verbindung entscheidet, welche gilt; ein spaeterer Anspruch
aus der jeweils anderen Aera wird abgewiesen.

| Aera | Revision | Wer sie erreicht |
|---|---|---|
| `initialize`-Handshake | `2024-11-05` … **`2025-11-25`** | Was heutige Clients sprechen. Der Server antwortet mit der angefragten Revision — oder mit der Obergrenze `2025-11-25`, wenn die Anfrage etwas Neueres verlangt. |
| Pro-Request-Envelope | **`2026-07-28`** | Eine Anfrage mit dem `2026-07-28`-`_meta`-Envelope oeffnet eine moderne Verbindung. |

Beide Revisionen sind in
[`tests/test_protocol_version.py`](tests/test_protocol_version.py) gepinnt und
werden gegen das installierte SDK geprueft; ein Dependabot-Bump von `mcp` kann
also keine der beiden still verschieben.

Zu beachten: `LATEST_PROTOCOL_VERSION` im SDK ist ein Alias auf die **moderne**
Aera, nicht auf die Handshake-Aera — wer nur dagegen pinnt, laesst genau die
Aera frei wandern, die heutige Clients tatsaechlich aushandeln.

**Die moderne Aera ist gemessen, nicht geschlossen.**
[`tests/test_modern_era.py`](tests/test_modern_era.py) baut die echte ASGI-App
dieses Servers und schickt Anfragen durch: einen `2026-07-28`-Envelope, einen
`initialize`-Handshake und jede der fehlerhaften Varianten. Geprueft wird, dass
eine moderne Anfrage beantwortet wird, dass die beiden Aeren getrennt bleiben
(`initialize` ist auf dem modernen Draht keine Methode; der Handshake deckelt
bei `2025-11-25` statt `2026-07-28` herauszugeben), dass `server/discover`
genau die gepinnte Revision nennt, dass eine fremde Revision mit `-32022`
abgewiesen wird und dabei die angefragte UND die unterstuetzte benennt, und
dass `ttlMs`/`cacheScope` sowie `serverInfo` als Drahtfelder ankommen.

Das ist nicht dasselbe wie ein Test ueber einen In-Process-Client: Die moderne
Aera existiert **nur** auf dem Streamable-HTTP-Einstieg — stdio und die
In-Process-Clients sprechen den `initialize`-Handshake und sonst nichts. Wer
die Spec durch einen In-Process-Client prueft, prueft die Handler und nicht die
Aera. Diese Luecke verbarg einen Fehler von einem Zeichen: `main()` startete
den HTTP-Transport als `streamable_http`, wo `run()` im SDK `streamable-http`
verlangt. Der Transport brach mit `ValueError` ab, der Server bediente die Spec
also gar nicht — und alles blieb gruen, weil die Tests `mcp.run` patchten und
den String gegen eine handgeschriebene Kopie desselben Tippfehlers hielten.

**Identitaet des Servers.** Spec `2026-07-28` fuehrt `serverInfo` im `_meta`
**jeder** Antwort mit, nicht einmal pro Sitzung wie die Handshake-Aera. Dieser
Server fuellt es mit Name, Titel, Beschreibung, Projektadresse und der Version
aus den Paket-Metadaten (`importlib.metadata` — dieselbe Quelle wie der
ausgehende `User-Agent`); eine von Hand gepflegte Nummer weist
`scripts/check_version_sync.py` zurueck.

Der Name lautet `swiss-culture-mcp` — dieselbe Schreibweise wie Distribution,
Konsolenskript, Registry-Eintrag und ausgehender `User-Agent`. Bis zum
20.9.2026 stand dort `swiss_culture_mcp`; eine Identitaet, die sich je nach
Blickwinkel anders schreibt, ist keine. `tests/test_servername.py` haelt die
Quellen zusammen, statt ein Literal gegen sich selbst zu pruefen. Der
Python-**Logger** behaelt den Unterstrich mit Absicht: Das ist ein
Logger-Name und keine Server-Identitaet, ihn mitzuziehen braeche jede
Logkonfiguration beim Betreiber, ohne irgendetwas anzugleichen.

**Update-Politik.** Faellt das Gate, die Konstante nicht blind nachziehen: erst
das Spec-Changelog zwischen den beiden Revisionen lesen, pruefen, ob sich der
Server weiterhin richtig verhaelt, dann Konstante, diesen Abschnitt, `README.md`
und [`CHANGELOG.md`](CHANGELOG.md) gemeinsam bewegen.

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
→ Weitere Anwendungsbeispiele nach Zielgruppe →
```

---

## Sicherheit & Grenzen

| Aspekt | Details |
|--------|---------|
| **Zugriff** | Nur lesend — der Server kann keine Daten verändern oder löschen |
| **Personendaten** | Keine Personendaten — alle Quellen sind aggregierte, öffentliche Kulturdaten |
| **Abfragelimits** | Eingebaute Obergrenzen pro Abfrage (z.B. max. 100 ISOS-Resultate, 50 News-Einträge, 200 Kategorieeinträge) |
| **Timeout** | 20 Sekunden pro API-Aufruf |
| **Authentifizierung** | Keine API-Schlüssel erforderlich — alle 4 Datenquellen sind öffentlich zugänglich |
| **Lizenzen** | Alle Daten unter offenen Lizenzen (Open Government Data): geo.admin.ch, opendata.swiss, news.admin.ch |
| **Nutzungsbedingungen** | Es gelten die Nutzungsbedingungen der jeweiligen Datenquellen: [geo.admin.ch](https://www.geo.admin.ch/de/geo-dienstleistungen/geodienste/terms-of-use.html), [opendata.swiss](https://opendata.swiss/de/terms-of-use), [news.admin.ch](https://www.admin.ch/gov/de/start/rechtliches.html), [lebendige-traditionen.ch](https://www.lebendige-traditionen.ch/) |

---

## Bekannte Einschränkungen

- **ISOS-Statistiken:** Stichprobenbasiert pro Kanton (nicht erschöpfend für alle Kantone)
- **Lebendige Traditionen:** HTML-Scraping – kann brechen, wenn lebendige-traditionen.ch seine Struktur ändert
- **BAK-Neuigkeiten/Preise:** RSS-Feed auf die neuesten Einträge beschränkt
- **opendata.swiss CKAN:** Volltextsuche kann Resultate anderer Publisher einschliessen
- **Die Adressen, die dieser Server ausgibt, sind gemessen und nicht angenommen.** `scripts/record_fixtures.py` prüft jede bei jedem Lauf neu, samt vier Kontrollen (ein erfundener geo.admin.ch-Dienst, ein erfundener BAK-Pfad, eine erfundene News-Organisationsnummer, ein erfundener Tradition-Slug). Am 2026-08-08 war eine tot: `bak_isos_overview` gab `.../home/kulturerbe/baukultur.html` als BAK-Quelle aus — HTTP 404, ebenso wie der ganze `kulturerbe`-Zweig. Ersetzt wurde sie durch die BAK-Wurzel, die nachweislich mit 200 antwortet — nicht durch eine geratene Adresse.
- **Alles andere trug.** geo.admin.ch, opendata.swiss, gisos, isos, der News-Feed mit `org-nr=314` und die Traditionsseiten liefern echte Inhalte. Dieser Nullbefund ist mit aufgezeichnet: Ohne ihn fängt der nächste Durchgang bei null an.

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

## Beitragen

Beiträge sind willkommen – siehe [CONTRIBUTING.de.md](CONTRIBUTING.de.md).

---

## Sicherheit

Sicherheits-Posture, Hardening-Details und der Prozess für verantwortungsvolle Offenlegung sind in [SECURITY.de.md](SECURITY.de.md) dokumentiert.

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
