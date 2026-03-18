# Beitragen / Contributing

> 🇩🇪 [Deutsch](#deutsch) · 🇬🇧 [English](#english)

---

## Deutsch

Vielen Dank für Ihr Interesse an diesem Projekt! Beiträge sind willkommen.

### Wie kann ich beitragen?

**Fehler melden:** Erstellen Sie ein [Issue](../../issues) mit einer klaren Beschreibung des Problems, Schritten zur Reproduktion und der erwarteten vs. tatsächlichen Ausgabe.

**Feature vorschlagen:** Beschreiben Sie den Use Case, idealerweise mit einem Bezug zum Schweizer Kulturkontext (Schulprojekte, Raumplanung, Kulturtourismus, KI-Demos etc.).

**Code beitragen:**

1. Forken Sie das Repository
2. Erstellen Sie einen Feature-Branch: `git checkout -b feature/mein-feature`
3. Installieren Sie die Dev-Abhängigkeiten: `pip install -e ".[dev]"`
4. Schreiben Sie Tests für Ihre Änderungen
5. Lint prüfen: `ruff check src/ tests/`
6. Commit mit aussagekräftiger Nachricht: `git commit -m "feat: Tradition-Suche nach Kanton hinzufügen"`
7. Pull Request erstellen

### Code-Standards

- Python 3.11+, Ruff für Linting
- Docstrings auf Englisch (für internationale Kompatibilität)
- Kommentare und Fehlermeldungen dürfen Deutsch oder Englisch sein
- Alle MCP-Tools müssen `readOnlyHint: True` setzen (nur lesender Zugriff)
- Pydantic-Modelle für alle Tool-Inputs

### Datenquellen-Richtlinie

Dieser Server verwendet ausschliesslich **offizielle Open Government Data (OGD)**-Quellen des Bundes und der Kantone. Neue Datenquellen müssen:

- Öffentlich zugänglich sein (kein Login, kein API-Key als Pflichtbedingung)
- Aus offiziellen Schweizer Behörden oder öffentlichen Institutionen stammen
- Den Nutzungsbedingungen für OGD entsprechen (z. B. Open Data Licence, CC BY)

### Tests

Die Testsuite unterscheidet zwischen Unit-Tests (Mocks, kein Netzwerk) und Live-Tests (echte API-Aufrufe):

```bash
# Unit-Tests (immer ausführbar, kein Internet erforderlich)
PYTHONPATH=src pytest tests/ -m "not live"

# Live-Tests (Internet und erreichbare APIs erforderlich)
PYTHONPATH=src pytest tests/ -m "live"
```

Live-Tests sind mit `@pytest.mark.live` markiert und werden in der CI-Pipeline ausgeschlossen.

---

## English

Thank you for your interest in this project! Contributions are welcome.

### How can I contribute?

**Report bugs:** Create an [Issue](../../issues) with a clear description, reproduction steps, and expected vs. actual output.

**Suggest features:** Describe the use case, ideally with a reference to Swiss cultural context (school projects, spatial planning, cultural tourism, AI demos, etc.).

**Contribute code:**

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Install dev dependencies: `pip install -e ".[dev]"`
4. Write tests for your changes
5. Run linter: `ruff check src/ tests/`
6. Commit with clear message: `git commit -m "feat: add tradition search by canton"`
7. Create a Pull Request

### Code Standards

- Python 3.11+, Ruff for linting
- Docstrings in English (for international compatibility)
- Comments and error messages may be in German or English
- All MCP tools must set `readOnlyHint: True` (read-only access)
- Pydantic models for all tool inputs

### Data Source Policy

This server uses exclusively **official Open Government Data (OGD)** sources from the Swiss federal government and cantons. New data sources must:

- Be publicly accessible (no login, no mandatory API key)
- Originate from official Swiss government bodies or public institutions
- Comply with OGD terms of use (e.g. Open Data Licence, CC BY)

### Tests

The test suite distinguishes between unit tests (mocked, no network) and live tests (real API calls):

```bash
# Unit tests (always runnable, no internet required)
PYTHONPATH=src pytest tests/ -m "not live"

# Live tests (internet and reachable APIs required)
PYTHONPATH=src pytest tests/ -m "live"
```

Live tests are marked with `@pytest.mark.live` and excluded from the CI pipeline.

---

## Lizenz / License

MIT – see [LICENSE](LICENSE)
