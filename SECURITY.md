# Security Policy & Posture

🌐 **English** | **[Deutsch](SECURITY.de.md)**

`swiss-culture-mcp` was hardened against the internal MCP best-practice audit
catalogue ([`mcp-audit-skill`](https://github.com/malkreide/mcp-audit-skill),
~68 checks, spec 2025-06-18). This document summarises the security posture and
records the **accepted-risk** decisions for controls that are deliberately
handled at the portfolio/gateway layer rather than inside this single server.

## Reporting a vulnerability

Please open a private security advisory on the GitHub repository, or contact the
maintainer listed in `README.md`. Do not file public issues for exploitable
vulnerabilities.

## Posture summary

This is a **read-only**, **no-PII**, **public-open-data** MCP server. All 10
tools only issue HTTP GET requests against a fixed set of Swiss federal
open-data endpoints (geo.admin.ch REST, news.admin.ch RSS, opendata.swiss CKAN,
lebendige-traditionen.ch — see `README.md`). Hardening already in place:

| Area | Control |
|---|---|
| Egress | HTTPS to a fixed allow-list of federal / partner hosts; no user-controlled URLs are constructed (SEC-005) |
| TLS | Certificate verification on by default (httpx default); never disabled |
| Binding | stdio transport by default; the optional `streamable_http` transport binds to `127.0.0.1` and refuses to bind `0.0.0.0` unless `MCP_ALLOW_PUBLIC_BIND=true` is set explicitly (SEC-003) |
| Input | Pydantic v2 validation on every tool input model; ISOS detail slugs are regex-validated before use (SEC-005) |
| XML | RSS parsing uses `defusedxml.ElementTree` — protects against XXE and Billion-Laughs (SEC-004) |
| HTML | Untrusted HTML from lebendige-traditionen.ch is parsed defensively; regression fixtures guard the scraper (SEC-019) |
| Tools | Every tool sets `readOnlyHint: True`; no write, mutate, or delete paths exist |
| Secrets | None required — the server uses no API key or credentials; nothing secret is stored or logged |
| Errors | Upstream error bodies are logged to stderr only; the model receives a generic, non-leaking message (SEC-006) |
| Logging | Structured JSON logs pinned to stderr; stdout is reserved for the JSON-RPC stream (OBS-001) |
| Resilience | A 20s per-request timeout bounds every upstream call; per-query result caps limit response size (SCALE-001/002) |

The audit (`audit/audit-report.md`) and its rerun — 2 High, 5 Medium and 1 Low —
are **fully closed** as of `v1.1.0`, each backed by a regression test (54 tests,
CI matrix 3.11/3.12/3.13). See `CHANGELOG.md` for the hardening history.

> ⚠️ The server itself has **no authentication**. Binding to a public interface
> without an upstream auth layer turns it into an open proxy for the federal data
> sources. Always run an authenticating reverse proxy (Cloudflare Access,
> oauth2-proxy, nginx + auth_request) in front of any `0.0.0.0` deployment.

## Accepted risks (portfolio-level controls)

The following audit checks are **not** implemented inside this server by design.
They are portfolio-wide concerns best enforced at an MCP gateway / host layer,
and the residual risk here is low because the server is read-only and only
reaches a small set of trusted public-data providers.

- **Tool allow-listing via an MCP gateway** — a per-tool allow-list belongs to
  the MCP host/gateway that aggregates multiple servers, not to an individual
  server that exposes a fixed, read-only tool set.
- **Pre-flight tool-poisoning detection** — this server's tool definitions are
  version-controlled, authored in-repo, and reviewed via PR; there is no dynamic
  or remote tool registration. Cross-server poisoning detection remains a
  gateway/host responsibility tracked at the portfolio level.
- **Multi-tenant observability (request/correlation IDs)** — only relevant if
  the server is ever run in a multi-tenant HTTP mode; not applicable to the
  current single-tenant stdio / single-user HTTP profile.

## Re-evaluation triggers

These acceptances should be revisited if the server ever:

- gains **write** capability or starts processing **PII**, or
- adds an **authentication** model (then implement bound, TTL'd,
  server-side-invalidated session IDs and re-audit before merge), or
- registers tools **dynamically** / from remote sources, or
- is aggregated behind a shared MCP gateway (then enable the gateway's tool
  allow-listing and tool-poisoning detection).
