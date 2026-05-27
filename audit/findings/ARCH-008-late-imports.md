# ARCH-008 — Lazy `import re` innerhalb von Tool-Funktionen

> **✅ CLOSED in Run-2** — behoben durch PR #3 (commit a154335). `import re` ist jetzt am Modulkopf (`server.py:17`).

- **Severity:** LOW
- **Kategorie:** ARCH
- **Status:** open

## Befund

`re` wird zwei Mal in Funktionsrümpfen importiert, statt einmal am Modulkopf.

## Evidenz

`src/swiss_culture_mcp/server.py:1057`

```python
async def bak_list_traditions(params: TraditionListInput) -> str:
    try:
        html = await _get_text(f"{TRADITIONS_BASE}/liste/liste.html")
        import re
```

`src/swiss_culture_mcp/server.py:1146`

```python
async def bak_get_tradition_detail(params: TraditionDetailInput) -> str:
    try:
        import re
```

## Empfehlung

`import re` an den Modulkopf verschieben (zu den anderen `import`-Statements bei Zeile 13–19). Ruff `I` (isort) sollte das beim nächsten `ruff check --fix` ohnehin anzeigen — aktuell ist es nicht moniert, weil der lokale Scope syntaktisch erlaubt ist.
