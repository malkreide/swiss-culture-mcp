# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Security
- **SEC-003**: Streamable-HTTP-Transport bindet nun standardmässig auf `127.0.0.1`. Öffentliches Binding nur mit explizitem `MCP_HOST=0.0.0.0` + `MCP_ALLOW_PUBLIC_BIND=true` und dem dokumentierten Hinweis auf vorgelagerten Auth-Proxy.
- **SEC-006**: `_handle_error` propagiert keinen Upstream-Response-Body mehr an den LLM. Volle Diagnose nur noch im Log.

### Added
- **OBS-001**: Strukturierte JSON-Logs auf stderr via `logging`-Stdlib. Log-Level via `LOG_LEVEL`-Env (Default `INFO`). Server-Start, Upstream-HTTP-Fehler, Timeouts und Connect-Errors werden geloggt.
- Neue Env-Vars: `MCP_HOST`, `MCP_ALLOW_PUBLIC_BIND`, `LOG_LEVEL`.
- 5 zusätzliche Tests (41 statt 36): Hardening von `main()` + Anti-Leak-Test in `_handle_error`.

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
