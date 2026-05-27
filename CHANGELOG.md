# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Security
- **SEC-003**: Streamable-HTTP-Transport bindet nun standardmässig auf `127.0.0.1`. Öffentliches Binding nur mit explizitem `MCP_HOST=0.0.0.0` + `MCP_ALLOW_PUBLIC_BIND=true` und dem dokumentierten Hinweis auf vorgelagerten Auth-Proxy.
- **SEC-004**: RSS-Parsing nutzt `defusedxml.ElementTree` statt `xml.etree.ElementTree` — schützt vor XXE und Billion-Laughs.
- **SEC-005**: `TraditionDetailInput.slug` validiert Pydantic-Regex `^[a-z0-9][a-z0-9\-]+$` (verhindert Pfad-Traversal). Zusätzlich Host-Allowlist (`_assert_host_allowed`) auf alle HTTP-Antworten — Open-Redirects auf nicht-erlaubte Hosts werden abgelehnt.
- **SEC-006**: `_handle_error` propagiert keinen Upstream-Response-Body mehr an den LLM. Volle Diagnose nur noch im Log.

### Performance
- **SCALE-001**: Modulweiter `httpx.AsyncClient` mit Connection-Pooling statt Client-Erstellung pro Request.
- **SCALE-002**: `bak_isos_statistics` führt die 7 Kanton-Abfragen jetzt parallel via `asyncio.gather` aus (~7× Speed-up).

### Added
- **OBS-001**: Strukturierte JSON-Logs auf stderr via `logging`-Stdlib. Log-Level via `LOG_LEVEL`-Env (Default `INFO`). Server-Start, Upstream-HTTP-Fehler, Timeouts, Connect-Errors und blockierte Hosts werden geloggt.
- Neue Env-Vars: `MCP_HOST`, `MCP_ALLOW_PUBLIC_BIND`, `LOG_LEVEL`.
- Neue Dependency: `defusedxml>=0.7.1`.
- 14 zusätzliche Tests (50 statt 36): Hardening von `main()`, Anti-Leak, Slug-Regex (4 Tests), Host-Allowlist (2), Defused-XML (1), Connection-Pool-Singleton (2).

## [1.0.0] - 2026-03-11

### Added
- 10 Tools für BAK-Kulturdaten (ISOS, Kulturpreise, Lebendige Traditionen, News, Open Data)
- 3 Resources: `bak://isos/kantone`, `bak://isos/kategorien`, `bak://kulturpreise/uebersicht`
- ISOS-Suche: `bak_search_isos`, `bak_isos_by_kanton`, `bak_get_isos_detail`, `bak_isos_by_kategorie`, `bak_isos_statistics`
- BAK-News und Preise: `bak_get_news`, `bak_get_kulturpreise`
- Open Data: `bak_get_opendata` (CKAN/opendata.swiss)
- Lebendige Traditionen: `bak_list_traditions`, `bak_get_tradition_detail`
- 36 Tests (Unit-Tests mit Mocks + 4 Live-Integrationstests)
- Dualer Transport: stdio (lokal) + Streamable HTTP (Cloud/Render.com)
- Bilinguales README (Deutsch primär, Englisch sekundär)
- Pydantic v2 Input-Validierung für alle Tools
- Einheitliche, handlungsorientierte Fehlermeldungen auf Deutsch
- Kantons-Validierung mit vollständiger Schweizer Kantonsliste (26 Kantone)
