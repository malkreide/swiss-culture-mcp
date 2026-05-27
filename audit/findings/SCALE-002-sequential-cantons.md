# SCALE-002 — Sequenzielle Kanton-Calls in `bak_isos_statistics`

> **✅ CLOSED in Run-2** — behoben durch PR #3 (commit a154335). `asyncio.gather` in `server.py:455-477`. ~7× Latenz-Reduktion.

- **Severity:** MEDIUM
- **Kategorie:** SCALE
- **Status:** open

## Befund

`bak_isos_statistics` ruft 7 Kanton-Endpunkte sequenziell in einer `for`-Schleife auf. Bei 250 ms Latenz pro Call summiert sich das auf ≈1.75 s, statt mit `asyncio.gather` parallel ≈250 ms zu erreichen.

## Evidenz

`src/swiss_culture_mcp/server.py:659-683`

```python
sample_kantone = ["ZH", "BE", "GR", "VS", "VD", "AG", "SO"]
per_kanton = {}
for kanton in sample_kantone:
    try:
        data = await _get(...)
        ...
```

## Risiko

Reine Performance/UX. Kein Sicherheits-Impact, aber direkt fühlbarer Latenz-Hit in Demos.

## Empfehlung

```python
import asyncio

async def _fetch_kanton(kanton: str) -> tuple[str, dict]:
    try:
        data = await _get(...)
        ...
    except Exception:
        return kanton, {"kanton_name": KANTONE[kanton], "objekte": None}

results = await asyncio.gather(*[_fetch_kanton(k) for k in sample_kantone])
per_kanton = dict(results)
```
