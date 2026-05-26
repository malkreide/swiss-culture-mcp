# Audit-Report — swiss-culture-mcp

| Feld | Wert |
|---|---|
| Audit-Skill | [malkreide/mcp-audit-skill](https://github.com/malkreide/mcp-audit-skill) (Katalog ~68 Checks, Spec 2025-06-18) |
| Run-ID | `2026-05-26-swiss-culture-mcp` |
| Zielcommit | `14edf2bf2208a6f4344f4ee7215ec856e88b51b4` (Branch `claude/magical-hawking-wZO9W`) |
| Datum | 2026-05-26 |
| Auditor | claude-opus-4-7 (automatisiert, Methodik gemäss Skill) |

---

## 1. Executive Summary

`swiss-culture-mcp` ist ein **gut strukturierter, read-only Open-Government-Data-MCP-Server** mit klarer Pydantic-Validierung, vollständigen MCP-Tool-Annotations, einer CI-Pipeline und solider Test-Abdeckung (36 Tests, 100 % grün). Das Risikoprofil ist **niedrig**, weil keine personenbezogenen Daten verarbeitet werden und der Defaulttransport stdio ist.

Production-Ready-Verdict: **Nicht für ungeschütztes HTTP-Deployment freigegeben.** Für stdio-Verwendung in Claude Desktop / claude.ai ist der Server einsatzbereit; die HIGH-Befunde adressieren spezifisch den Cloud-/HTTP-Pfad sowie fehlende Observability.

```
Checks:    68 Katalog · 41 anwendbar · 33 pass · 8 fail · 27 n/a
Findings:  0 critical · 2 high · 5 medium · 1 low
```

Blocking für HTTP-Production: `SEC-003`, `OBS-001`.
Stdio-Deployment-Blocker: nur `OBS-001` (operativ wünschbar, nicht zwingend).

---

## 2. Profil (anwendbarkeitsbestimmend)

| Feld | Wert |
|---|---|
| Transport | stdio (Default) + streamable_http (optional) |
| Auth | keine |
| Datenklasse | Public OGD |
| Schreibzugriff | none (alle 10 Tools `readOnlyHint=true`) |
| Deployment | local stdio · Render.com / Docker |
| Datenquellen | geo.admin.ch, news.admin.ch (RSS), opendata.swiss (CKAN), lebendige-traditionen.ch (HTML) |

Folgewirkung auf Applicability: OAuth-/RBAC-/HITL-/PII-Checks weitgehend **n/a** (27 von 68). Audit-Fokus auf SEC (HTTP-Pfad, Parsing, Error-Hygiene), SCALE, OBS, ARCH.

---

## 3. Findings (8 offen)

| ID | Severity | Kategorie | Kurzbeschreibung | Pfad |
|---|---|---|---|---|
| `SEC-003` | **HIGH** | SEC | Streamable-HTTP bindet `0.0.0.0` ohne Auth | server.py:1252 |
| `OBS-001` | **HIGH** | OBS | Kein Logging im gesamten Server | server.py (gesamt) |
| `SEC-004` | MEDIUM | SEC | `xml.etree.ElementTree` parst untrusted RSS (XXE/Billion-Laughs) | server.py:15, 166 |
| `SEC-005` | MEDIUM | SEC | `slug` ungesichert in URL + Redirects aktiv (Pfad-/SSRF-Risiko) | server.py:319, 1148 |
| `SEC-006` | MEDIUM | SEC | Upstream-Response-Body wird in LLM-Fehlertext geleakt | server.py:137 |
| `SCALE-001` | MEDIUM | SCALE | Pro Request neuer `httpx.AsyncClient` (kein Pooling) | server.py:103-122 |
| `SCALE-002` | MEDIUM | SCALE | 7 Kanton-Calls in `bak_isos_statistics` sequenziell | server.py:659-683 |
| `SEC-019` | MEDIUM* | SEC/ARCH | Regex-HTML-Parsing von Drittanbieter-DOM | server.py:1059, 1156 |
| `ARCH-005` | LOW | ARCH | Monolithische `server.py` (1259 Zeilen) | server.py |
| `ARCH-008` | LOW | ARCH | `import re` lazy in Funktionen | server.py:1057, 1146 |

\* SEC-019 ist eigenständig LOW; in Kombination mit SEC-005 MEDIUM.

Vollständige Findings (Evidenz + Fix-Vorschläge) unter `audit/findings/<ID>.md`.

---

## 4. Was sauber ist (33 passes — Highlights)

- **MCP-SDK-Hygiene**: FastMCP korrekt instanziiert, vollständige Tool-Annotations (`readOnlyHint`, `idempotentHint`, `destructiveHint`, `openWorldHint`) — `server.py:88-96, 348-1185`.
- **Pydantic v2 strikt**: `extra="forbid"`, `validate_assignment=True`, `min_length`/`max_length`/`ge`/`le`, Kantons-Whitelist mit `field_validator` — `server.py:187-340`.
- **Einheitliches Error-Handling** (`_handle_error`) mit handlungsorientierten DE-Meldungen für 404/403/429/5xx/Timeout/ConnectError — `server.py:125-142`.
- **Keine Secrets**, keine API-Keys, keine `eval`/`exec`/`shell=True`.
- **Schweizer Compliance**: Vollständige 26-Kanton-Liste, LV03-Koordinaten benannt, ToS-Links für alle vier Quellen im README dokumentiert.
- **CI**: Matrix Python 3.11/3.12/3.13, Ruff-Lint, py_compile, Import-Smoketest, 36 Unit-Tests — alle grün.
- **PyPI-Release**: OIDC Trusted Publisher (kein API-Token im Repo).
- **Doku**: README de+en, EXAMPLES.md, CHANGELOG (Keep a Changelog), CONTRIBUTING mit Datenquellen-Richtlinie.
- **Resources**: 3 Resources liefern statische Referenzdaten (Kantone, Kategorien, Preise) → reduziert unnötige Tool-Calls.

---

## 5. Priorisierte Roadmap

### P0 — Vor HTTP-Production (Blocker)

1. **SEC-003** Default-Bind `127.0.0.1`, Auth oder explizite Override-Env-Var; Cloud-Deployment-Anleitung mit Auth-Reverse-Proxy ergänzen.
2. **OBS-001** Strukturiertes Logging (`logging.basicConfig` + JSON-Formatter) + Tool-Call-Logger.

### P1 — Defense in Depth (Medium)

3. **SEC-004** `defusedxml` statt `xml.etree.ElementTree`.
4. **SEC-005** Slug-Regex (`^[a-z0-9][a-z0-9\-]+$`) + Redirect-Hostvalidierung.
5. **SEC-006** Upstream-Response-Body NUR ins Log, nicht in LLM-Antwort.
6. **SCALE-001** Modulweiter `httpx.AsyncClient` über FastMCP-Lifespan.
7. **SCALE-002** `asyncio.gather` für die 7 Kanton-Calls.

### P2 — Wartbarkeit (Low)

8. **ARCH-005** Modul-Split nach Datenquelle.
9. **ARCH-008** `import re` an Modulkopf.
10. **SEC-019** Live-HTML-Fixture als Schema-Regression-Test in CI nehmen (Mocks existieren bereits).

---

## 6. Release-Empfehlung

| Pfad | Verdict |
|---|---|
| stdio-Deployment (Claude Desktop / claude.ai stdio-Bridge) | **OK** mit Hinweis auf OBS-001. Aktueller Tag `v1.0.0` bleibt gültig. |
| HTTP-Deployment (Render.com, Docker, claude.ai HTTP-Integration) | **Nicht freigegeben** bis SEC-003 + OBS-001 behoben. |

Vorgeschlagener nächster Release: `v1.1.0` mit Tag-Notes „security & observability hardening" nach Abschluss der P0+P1-Items. CHANGELOG-Eintrag-Template:

```
## [1.1.0] - YYYY-MM-DD
### Security
- Streamable HTTP bindet nun standardmässig auf 127.0.0.1; öffentliches Binding nur mit explizitem MCP_HOST + Auth (#audit SEC-003)
- defusedxml für RSS-Parsing (#audit SEC-004)
- Slug-Regex-Validierung für Lebendige-Traditionen (#audit SEC-005)
- Upstream-Response-Body nicht mehr in LLM-Fehlertext (#audit SEC-006)
### Added
- Structured JSON logging mit LOG_LEVEL-Env-Var (#audit OBS-001)
### Performance
- HTTP-Connection-Pool über FastMCP-Lifespan (#audit SCALE-001)
- Parallele Kanton-Abfragen in bak_isos_statistics (#audit SCALE-002)
```

---

## 7. Reproduzierbarkeit

| Artefakt | Pfad |
|---|---|
| Audit-Meta | `audit/audit-meta.json` |
| Profil | `audit/profile.json` |
| Verification-Ergebnisse (alle 68 Checks) | `audit/verification-results.json` |
| Single Source of Truth | `audit/summary.json` |
| Findings | `audit/findings/<ID>.md` |
| Manifest des Katalogs | `audit/raw/MANIFEST.txt` |

Alle Zahlen in diesem Report stammen aus `summary.json` (siehe Skill-Prinzip „Single Source of Truth").
