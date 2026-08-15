# Beitragen zu swiss-culture-mcp

🌐 **[English](CONTRIBUTING.md)** | **Deutsch**

Vielen Dank für Ihr Interesse an diesem Projekt! Beiträge sind willkommen.

## Wie kann ich beitragen?

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

## Code-Standards

- Python 3.11+, Ruff für Linting
- Docstrings auf Englisch (für internationale Kompatibilität)
- Kommentare und Fehlermeldungen dürfen Deutsch oder Englisch sein
- Alle MCP-Tools müssen `readOnlyHint: True` setzen (nur lesender Zugriff)
- Pydantic-Modelle für alle Tool-Inputs

## Datenquellen-Richtlinie

Dieser Server verwendet ausschliesslich **offizielle Open Government Data (OGD)**-Quellen des Bundes und der Kantone. Neue Datenquellen müssen:

- Öffentlich zugänglich sein (kein Login, kein API-Key als Pflichtbedingung)
- Aus offiziellen Schweizer Behörden oder öffentlichen Institutionen stammen
- Den Nutzungsbedingungen für OGD entsprechen (z. B. Open Data Licence, CC BY)

## Tests

Die Testsuite unterscheidet zwischen Unit-Tests (Mocks, kein Netzwerk) und Live-Tests (echte API-Aufrufe):

```bash
# Unit-Tests (immer ausführbar, kein Internet erforderlich)
PYTHONPATH=src pytest tests/ -m "not live"

# Live-Tests (Internet und erreichbare APIs erforderlich)
PYTHONPATH=src pytest tests/ -m "live"
```

Live-Tests sind mit `@pytest.mark.live` markiert und werden in der CI-Pipeline ausgeschlossen.

## Sicherheit

Wenn Sie eine Sicherheitslücke entdecken, folgen Sie bitte dem Prozess für verantwortungsvolle Offenlegung in [SECURITY.de.md](SECURITY.de.md), anstatt ein öffentliches Issue zu eröffnen.

## Die Live-Suite: wann sie läuft, und wer ein rotes Ergebnis sieht

**Kadenz:** jeden Montag um 04:53 UTC, dazu jederzeit von Hand über *Actions → Live-Tests → Run
workflow*. Siehe [`.github/workflows/live-tests.yml`](.github/workflows/live-tests.yml).

**Wer es sieht:** Ein roter Lauf öffnet ein Issue mit dem Label `upstream` und dem stabilen Titel «Live-Tests gegen api3.geo.admin.ch rot (<Datum>)». Ein zweiter roter Lauf erkennt das offene Issue am Titelanfang und hängt sich an denselben Thread, statt ein zweites aufzumachen. Wird die Suite wieder grün, schliesst sich das Issue selbst.

**Drei Antworten, nicht zwei.** `scripts/classify_live_run.py` liest das JUnit-XML statt des
Exit-Codes und unterscheidet: `clear` (gelaufen, grün), `finding` (gelaufen,
etwas gefallen) und `unknown` (nicht gelaufen — Installation gescheitert, null
Tests eingesammelt, alle übersprungen). Ein `unknown` schliesst nie ein Issue:
Zuzumachen hiesse zu behaupten, der Vergleich sei gelaufen.

**Ein roter Live-Lauf heisst nicht zwingend «unser Fehler».** Er heisst: Der
Vertrag mit der Quelle hat sich geändert, oder die Quelle ist gerade aus. Beides
gehört gesehen, nur das Erste gehört gefixt. Bitte den Lauf lesen, bevor der Job
deaktiviert wird — so stirbt dieser Check, und er ist der einzige im Repo, der
einer falschen Grundannahme über api3.geo.admin.ch widersprechen kann. Jeder andere Test
prüft gegen eine Fixture, und die Fixture ist aus derselben Annahme geschrieben
wie der Code.

## Lizenz

Mit Ihrem Beitrag erklären Sie sich damit einverstanden, dass Ihre Beiträge unter der MIT-Lizenz stehen – siehe [LICENSE](LICENSE).
