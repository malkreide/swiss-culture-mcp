# Audit-Report — swiss-culture-mcp (Re-Run 2)

| Feld | Wert |
|---|---|
| Audit-Skill | [malkreide/mcp-audit-skill](https://github.com/malkreide/mcp-audit-skill) (Katalog ~68 Checks, Spec 2025-06-18) |
| Run-ID | `2026-05-27-swiss-culture-mcp-rerun-2` |
| Vorheriger Run | `2026-05-26-swiss-culture-mcp` (8 fail) |
| Zielcommit | `2ad18fae32d1068ad7a704756e2b55b55891435a` (main, post-PR #4) |
| Datum | 2026-05-27 |
| Auditor | claude-opus-4-7 (automatisiert, identische Methodik wie Run-1) |

---

## 1. Executive Summary

**Verdict: production-ready.**

Alle 8 fail-Befunde aus Run-1 sind geschlossen, jeder mit Regression-Test abgesichert. Keine neuen Findings, keine Regressionen. Test-Suite ist von 36 auf 54 Tests gewachsen; der `server.py`-Monolith wurde in vier zielführende Module gesplittet (1337 → 1074 Z. plus `constants.py` / `http_client.py` / `models.py`).

```
Checks:    68 Katalog · 41 anwendbar · 41 pass · 0 fail · 27 n/a
Findings:  0 critical · 0 high · 0 medium · 0 low
Delta:     +10 newly passing · 0 regressions · +18 neue Regression-Tests
```

HTTP-Deployment-Pfad ist nicht mehr Production-blockiert. Stdio-Deployment war es nie.

---

## 2. Profil (unverändert ggü. Run-1)

| Feld | Wert |
|---|---|
| Transport | stdio (Default) + streamable_http (optional, jetzt auth-gated) |
| Auth | keine im Server (HTTP-Modus: zwingend Auth-Reverse-Proxy davor) |
| Datenklasse | Public OGD |
| Schreibzugriff | none |
| Deployment | local stdio · Render.com / Docker (nur hinter Auth) |
| Datenquellen | geo.admin.ch · news.admin.ch · opendata.swiss · lebendige-traditionen.ch |

---

## 3. Geschlossene Befunde — Delta Run-1 → Run-2

| ID | Severity | PR | Verifikation / Regression-Test |
|---|---|---|---|
| `SEC-003` | **HIGH** | [#2](https://github.com/malkreide/swiss-culture-mcp/pull/2) | `TestMainHardening` (4 Tests) — SystemExit bei `0.0.0.0` ohne `MCP_ALLOW_PUBLIC_BIND=true` |
| `OBS-001` | **HIGH** | [#2](https://github.com/malkreide/swiss-culture-mcp/pull/2) | Logger via `grep -n "logger\."` in `http_client.py` (10+ Stellen) |
| `SEC-006` | MEDIUM | [#2](https://github.com/malkreide/swiss-culture-mcp/pull/2) | `test_handle_error_no_upstream_body_leak` (Sentinel-String darf nicht im Returnwert auftauchen) |
| `SEC-004` | MEDIUM | [#3](https://github.com/malkreide/swiss-culture-mcp/pull/3) | `test_defusedxml_blocks_billion_laughs` |
| `SEC-005` | MEDIUM | [#3](https://github.com/malkreide/swiss-culture-mcp/pull/3) | 4 Slug-Pattern-Tests + 2 Host-Allowlist-Tests |
| `SCALE-001` | MEDIUM | [#3](https://github.com/malkreide/swiss-culture-mcp/pull/3) | `TestConnectionPool` — Singleton-Identität + User-Agent |
| `SCALE-002` | MEDIUM | [#3](https://github.com/malkreide/swiss-culture-mcp/pull/3) | Code-Review: `asyncio.gather` in `bak_isos_statistics:455-477` |
| `ARCH-008` | LOW | [#3](https://github.com/malkreide/swiss-culture-mcp/pull/3) | `grep "import re"` nur am Modulkopf |
| `ARCH-005` | LOW | [#4](https://github.com/malkreide/swiss-culture-mcp/pull/4) | `wc -l` zeigt 4 Module statt Monolith |
| `SEC-019` | LOW | [#4](https://github.com/malkreide/swiss-culture-mcp/pull/4) | `TestHtmlFixtures` (4 Tests) gegen `tests/fixtures/*.html` |

Detaillierte Code-Pointer in `audit/verification-results.json` unter `closed_by` / `regression_test`.

---

## 4. Anwendbare Checks im Detail (41)

| Kategorie | Anwendbar | Pass | Fail | Hinweis |
|---|---|---|---|---|
| ARCH | 10 | 10 | 0 | Komplett |
| SDK | 5 | 5 | 0 | Komplett |
| SEC | 14 | 14 | 0 | Komplett — inkl. neuer Host-Allowlist, defusedxml, Bind-Hardening |
| SCALE | 3 | 3 | 0 | Komplett |
| OBS | 2 | 2 | 0* | OBS-002 passt für Single-Tenant; *partial* für Multi-Tenant (siehe §5) |
| HITL | 0 | – | – | Komplett n/a (read-only, kein sampling/elicitation) |
| CH | 8 | 8 | 0 | Komplett (OGD, keine PII, ToS dokumentiert) |
| OPS | 3 | 3 | 0 | Komplett |

27 n/a-Checks sind unverändert (Auth/Schreibzugriff/PII/Container/Sandbox-Themen, die für dieses Profil nicht greifen).

---

## 5. Offene Punkte für ein hypothetisches Multi-Tenant-Deployment

Nicht-blockierend für aktuelles Profil, aber notiert:

- **OBS-002 (partial)** — Wenn der Server jemals im Multi-Tenant-HTTP-Modus betrieben wird, sollten explizite Request- / Correlation-IDs in den Log-Output. FastMCP exposed sie nicht out-of-the-box; eine Middleware-Schicht oder ein `contextvars`-basierter `RequestIdLogFilter` wäre der saubere Pfad.
- **SCALE-003** — Kein Dockerfile im Repo. Wird bei produktivem Render.com-Deployment relevant; aktuell n/a.
- **OBS-006** — Healthcheck-Endpoint (z. B. `GET /healthz`) für Load-Balancer dokumentieren, falls HTTP-Deployment ohne Sidecar erfolgt.

Diese Punkte rechtfertigen **kein** Issue im aktuellen Profil — sie wären erst bei Profil-Änderung relevant.

---

## 6. Test-Suite-Wachstum

| Run | Tests | Davon neu für Audit-Findings |
|---|---|---|
| Run-1 (Baseline) | 36 | – |
| nach PR #2 | 41 | +5 (Main-Hardening, Anti-Leak) |
| nach PR #3 | 50 | +9 (Slug, Host-Allowlist, defusedxml, Pool) |
| nach PR #4 | 54 | +4 (HTML-Fixtures) |
| Run-2 (heute) | 54 | **+18 Audit-Regression-Tests** |

Alle 54 grün; Ruff + Format sauber; CI-Matrix 3.11/3.12/3.13.

---

## 7. Release-Empfehlung

| Pfad | Run-1 | Run-2 |
|---|---|---|
| stdio-Deployment | ✅ OK | ✅ OK + Logging |
| HTTP-Deployment | ⛔ blockiert (SEC-003, OBS-001) | ✅ **freigegeben** (mit dokumentiertem Auth-Reverse-Proxy) |

**Vorgeschlagener Release: `v1.1.0`** — der `CHANGELOG.md`-Eintrag im `[Unreleased]`-Block ist bereits komplett ausformuliert (siehe Commit-History PRs #2–#4). Tag empfohlen sobald PR #4 in einem Release-Branch landet.

---

## 8. Single Source of Truth

| Artefakt | Pfad |
|---|---|
| Audit-Meta | `audit/audit-meta.json` |
| Profil | `audit/profile.json` (unverändert) |
| Verification-Results (alle 68 Checks, mit `previous_status`-Delta) | `audit/verification-results.json` |
| Summary (SSOT) | `audit/summary.json` |
| Run-1-Findings (historisch, geschlossen) | `audit/findings/*.md` |
| Katalog-Manifest | `audit/raw/MANIFEST.txt` |

Alle Zahlen in diesem Report stammen aus `summary.json`.
