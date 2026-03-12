# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
