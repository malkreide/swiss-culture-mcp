# SEC-006 — Upstream-Response-Leak in Fehlermeldungen

> **✅ CLOSED in Run-2** — behoben durch PR #2 (commit 391e093). Verifiziert durch `test_handle_error_no_upstream_body_leak`. `_handle_error` gibt nur noch Statuscode an LLM; voller Body geht ins Log.

- **Severity:** MEDIUM
- **Kategorie:** SEC
- **Status:** open

## Befund

`_handle_error` schreibt 200 Zeichen des Upstream-Response-Body in die an den LLM/Client zurückgegebene Fehlermeldung. Bei fehlkonfigurierten Upstreams können dort interne Hostnames, Stack-Traces oder Cookie-/Header-Echos auftauchen.

## Evidenz

`src/swiss_culture_mcp/server.py:137`

```python
return f"Fehler: HTTP {code} – {e.response.text[:200]}"
```

## Risiko

- Information Disclosure → der LLM/Host sieht Upstream-Internals (z. B. ASP.NET-Stack-Trace, JSON mit interner IP).
- Prompt-Injection-Vektor: bösartiger Upstream könnte Anweisungen in einen Fehlertext schmuggeln, die der LLM ausführt.

## Empfehlung

```python
return f"Fehler: HTTP {code} (Upstream gemeldet)."
```

Und den vollständigen Body in den Logger schreiben (siehe OBS-001), nicht in die LLM-Antwort.
