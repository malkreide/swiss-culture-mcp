# SEC-019 — Regex-Parsing von Drittanbieter-HTML

> **✅ CLOSED in Run-2** — adressiert durch PR #4 (commit 932247f) als Regression-Schutz. Versionierte HTML-Fixtures unter `tests/fixtures/` + `TestHtmlFixtures` (4 Tests). Regex-Parser selbst beibehalten (kein neues Dep nötig), Frühwarnsystem bricht bei DOM-Änderungen.

- **Severity:** MEDIUM (kombiniert mit SEC-005); LOW eigenständig
- **Kategorie:** SEC / ARCH
- **Status:** open

## Befund

`bak_list_traditions` und `bak_get_tradition_detail` parsen HTML mit regulären Ausdrücken. Bei lebendige-traditionen.ch ist die DOM-Struktur Drittanbieter-kontrolliert; bei strukturellen Änderungen brechen Tools still, bei pathologischem HTML droht ReDoS (vorhandene Patterns sind allerdings simpel und backtracking-arm).

## Evidenz

`src/swiss_culture_mcp/server.py:1059`

```python
links = re.findall(r'href="(/tradition/de/home/traditionen/([^"]+\.html))"', html)
```

`src/swiss_culture_mcp/server.py:1156-1160`

```python
title_match = re.search(r"<title>([^<|]+)", html)
desc_match  = re.search(r'<meta name="description" content="([^"]+)"', html)
p_tags      = re.findall(r"<p[^>]*>([^<]{50,})</p>", html)
```

`README.md:257` erkennt die Fragilität bereits an.

## Risiko

- Stiller Funktionsausfall bei DOM-Änderung.
- ReDoS-Risiko aktuell gering, könnte bei Erweiterungen zunehmen.

## Empfehlung

- `selectolax` oder `beautifulsoup4` für robusteres Parsing.
- Bei Aufgabentreue zu „kein zusätzliches Dep“: Patterns dokumentieren + Schema-Regression-Test gegen ein eingefrorenes HTML-Fixture in `tests/` (existiert bereits als Mock — als CI-Fixture nutzbar).
