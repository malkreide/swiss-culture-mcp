# SEC-004 — XXE/Billion-Laughs-Risiko durch ElementTree

> **✅ CLOSED in Run-2** — behoben durch PR #3 (commit a154335). `defusedxml.ElementTree` ersetzt stdlib. Verifiziert durch `test_defusedxml_blocks_billion_laughs`.

- **Severity:** MEDIUM
- **Kategorie:** SEC
- **Status:** open

## Befund

`xml.etree.ElementTree.fromstring` parst die RSS-Antwort des News Service Bund. Standard-ET in CPython 3.11 deaktiviert externe Entities zwar weitgehend, schützt aber NICHT zuverlässig vor Entity-Expansion-Angriffen (Billion Laughs). Da der Upstream-Inhalt nicht unter eigener Kontrolle steht (Bundesservice + möglicher MITM bei kompromittiertem Pfad), gilt der `defusedxml`-Standard.

## Evidenz

`src/swiss_culture_mcp/server.py:15`

```python
import xml.etree.ElementTree as ET
```

`src/swiss_culture_mcp/server.py:166`

```python
def _parse_rss_items(xml_text: str, max_items: int = 20) -> list[dict]:
    root = ET.fromstring(xml_text)
```

## Risiko

- DoS via maliziösen Feed (entity expansion blows memory).
- Niedrig, weil Quelle vertrauenswürdig + TLS, aber kein Verteidigungs-in-die-Tiefe.

## Empfehlung

```python
import defusedxml.ElementTree as ET
```

Abhängigkeit `defusedxml>=0.7` zu `pyproject.toml` hinzufügen.
