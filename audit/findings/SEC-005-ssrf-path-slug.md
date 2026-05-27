# SEC-005 — Pfadinjektion über `slug` in Lebendige-Traditionen-URL

> **✅ CLOSED in Run-2** — behoben durch PR #3 (commit a154335). Slug-Regex `^[a-z0-9][a-z0-9\-]+$` + Host-Allowlist via `_assert_host_allowed`. Verifiziert durch 4 Slug- + 2 Host-Tests.

- **Severity:** MEDIUM
- **Kategorie:** SEC
- **Status:** open

## Befund

`bak_get_tradition_detail` baut die Ziel-URL via f-string mit dem nutzerkontrollierten `slug` zusammen. Pydantic validiert nur Längen (3–200), keinen Slug-Regex. Kombiniert mit `follow_redirects=True` in `_get_text` entsteht eine SSRF-/Path-Traversal-Oberfläche innerhalb der Domain (z. B. `slug = "../../some/admin/path"` oder ein Slug, der über Server-Redirect auf interne Hosts umgelenkt wird).

## Evidenz

`src/swiss_culture_mcp/server.py:319-327` — `slug`-Validierung nur Länge:

```python
slug: str = Field(
    ...,
    min_length=3,
    max_length=200,
)
```

`src/swiss_culture_mcp/server.py:1148`:

```python
url = f"{TRADITIONS_BASE}/traditionen/{params.slug}.html"
html = await _get_text(url)
```

`src/swiss_culture_mcp/server.py:111-122` — Redirects werden gefolgt:

```python
async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
    response = await client.get(url, ...)
```

## Risiko

- Path Traversal innerhalb lebendige-traditionen.ch.
- SSRF via Open-Redirect (kompromittierter Upstream).
- Niedrig in der Praxis, aber Pydantic-Whitelist ist Standard-Defense.

## Empfehlung

```python
slug: str = Field(..., pattern=r"^[a-z0-9][a-z0-9\-]{1,198}$", min_length=2, max_length=200)
```

Zusätzlich: in `_get_text` einen Parameter `allow_redirects: bool = False` einführen und gezielt aktivieren, ODER nach Redirect die finale URL prüfen (`response.url.host == expected_host`).
