# Use Cases & Examples — swiss-culture-mcp

Real-world queries by audience. Indicate per example whether an API key is required.

## 🏫 Bildung & Schule
Lehrpersonen, Schulbehörden, Fachreferent:innen

**Projektwoche Immaterielles Kulturerbe**
«Welche lebendigen Traditionen gibt es in der Schweiz, die mit Musik zu tun haben, und was genau ist das Alphorn- und Büchelspiel?»
→ `bak_list_traditions()`
→ `bak_get_tradition_detail(slug="alphorn--und-buechelspiel")`
Warum nützlich: Erlaubt Lehrpersonen, gezielt nach kulturellen Traditionen für den Unterricht zu suchen und detailliertes Material für Projektwochen aufzubereiten. (Kein API-Key erforderlich)

**Lokalgeschichte im Unterricht**
«Gibt es in der Stadt Winterthur schützenswerte Ortsbilder und wie lautet die Inventarnummer?»
→ `bak_search_isos(query="Winterthur", limit=10)`
→ `bak_get_isos_detail(feature_id="...")`
Warum nützlich: Unterstützt Lehrpersonen dabei, Exkursionen vor Ort zu planen und Schülerinnen und Schülern die lokale Architekturgeschichte anhand offizieller Register greifbar zu machen. (Kein API-Key erforderlich)

## 👨👩👧 Eltern & Schulgemeinde
Elternräte, interessierte Erziehungsberechtigte

**Kulturelle Ausflugsziele für Familien**
«Wir planen einen Familienausflug in den Kanton Graubünden. Welche Dörfer sind dort als schützenswerte Ortsbilder verzeichnet?»
→ `bak_isos_by_kategorie(kategorie="Dorf", kanton="GR", limit=20)`
Warum nützlich: Gibt Familien Inspiration für Wochenendausflüge zu historisch bedeutsamen und malerischen Orten in der Schweiz. (Kein API-Key erforderlich)

**Traditionen für Kinder**
«Worum geht es bei der Basler Fasnacht genau und welche Traditionen werden da gepflegt?»
→ `bak_get_tradition_detail(slug="fasnacht-basel")`
Warum nützlich: Hilft Eltern, Kindern komplexe und historisch gewachsene Schweizer Traditionen verständlich zu erklären und kulturelle Anlässe gemeinsam vorzubereiten. (Kein API-Key erforderlich)

## 🗳️ Bevölkerung & öffentliches Interesse
Allgemeine Öffentlichkeit, politisch und gesellschaftlich Interessierte

**Überblick über Kulturförderung und Preise**
«Wer hat in den letzten Jahren den Schweizer Filmpreis gewonnen und welche Filme wurden ausgezeichnet?»
→ `bak_get_kulturpreise(sparte="Film", limit=10)`
Warum nützlich: Schafft Transparenz über die staatliche Kulturförderung und ermöglicht Kulturinteressierten, sich über ausgezeichnetes Schweizer Schaffen zu informieren. (Kein API-Key erforderlich)

**Informieren über aktuelle Kulturpolitik**
«Gibt es aktuelle Neuigkeiten oder Medienmitteilungen des Bundesamts für Kultur zum Thema Denkmalpflege?»
→ `bak_get_news(keyword="Denkmalpflege", limit=5)`
Warum nützlich: Bietet politisch Interessierten einen schnellen und gezielten Zugriff auf aktuelle kulturpolitische Entscheidungen und Stellungnahmen des Bundes. (Kein API-Key erforderlich)

**Zustand des nationalen Kulturerbes**
«Wie viele schützenswerte Ortsbilder gibt es aktuell im Kanton Bern im Vergleich zur Gesamtschweiz?»
→ `bak_isos_statistics()`
→ `bak_isos_by_kanton(kanton="BE", limit=500)`
Warum nützlich: Fördert das öffentliche Verständnis für den Umfang und die regionale Verteilung des geschützten baukulturellen Erbes der Schweiz. (Kein API-Key erforderlich)

## 🤖 KI-Interessierte & Entwickler:innen
MCP-Enthusiast:innen, Forscher:innen, Prompt Engineers, öffentliche Verwaltung

**Integration von Geodaten und Kultur**
«Finde das ISOS-Ortsbild von Stein am Rhein und suche dann nach verfügbaren Open-Data-Datensätzen des BAK zu diesem Ort.»
→ `bak_search_isos(query="Stein am Rhein", limit=5)`
→ `bak_get_opendata(query="Stein am Rhein")`
Warum nützlich: Zeigt Entwicklerinnen und Entwicklern, wie sie REST-basierte Geodaten mit CKAN-Katalogen kombinieren können, um umfassende Dossiers zu spezifischen Orten zu generieren. (Kein API-Key erforderlich)

**Multi-Server: Kulturausflug mit dem ÖV planen**
«Suche mir schützenswerte Dörfer im Kanton Tessin und prüfe anschliessend die nächste Zugverbindung von Zürich HB dorthin.»
→ `bak_isos_by_kategorie(kategorie="Dorf", kanton="TI", limit=5)` (via swiss-culture-mcp)
→ `get_connections(from_station="Zürich HB", to_station="Morcote")` (via [swiss-transport-mcp](https://github.com/malkreide/swiss-transport-mcp))
Warum nützlich: Demonstriert das Potenzial von Agentic Workflows, bei denen Kulturdaten nahtlos in Reise- oder Logistikplanungen übersetzt werden. (Kein API-Key erforderlich)

**Multi-Server: Kulturgüter und Gesetze**
«Suche aktuelle BAK-News zum Thema Kulturgütertransfer und finde im Fedlex das entsprechende Gesetz dazu.»
→ `bak_get_news(keyword="Kulturgütertransfer", limit=5)` (via swiss-culture-mcp)
→ `fedlex_search(query="Kulturgütertransfer")` (via [fedlex-mcp](https://github.com/malkreide/fedlex-mcp))
Warum nützlich: Erlaubt Forscherinnen und Forschern, aktuelle kulturpolitische Ereignisse direkt mit den geltenden rechtlichen Grundlagen des Bundes zu verknüpfen. (Kein API-Key erforderlich)

---

## 🔧 Technische Referenz: Tool-Auswahl nach Anwendungsfall

| Ich möchte… | Tool(s) | Auth nötig? |
|-------------|---------|-------------|
| **einen bestimmten Ort im Inventar der schützenswerten Ortsbilder finden** | `bak_search_isos` | Nein |
| **alle geschützten Ortsbilder eines bestimmten Kantons auflisten** | `bak_isos_by_kanton` | Nein |
| **alle Details, Koordinaten und Links zu einem ISOS-Ortsbild abrufen** | `bak_get_isos_detail` | Nein |
| **Ortsbilder nach einem Siedlungstyp (z.B. Dorf, Stadt) filtern** | `bak_isos_by_kategorie` | Nein |
| **statistische Kennzahlen zum nationalen ISOS-Inventar sehen** | `bak_isos_statistics` | Nein |
| **die neusten Meldungen des Bundesamts für Kultur lesen** | `bak_get_news` | Nein |
| **wissen, wer kürzlich Schweizer Kulturpreise gewonnen hat** | `bak_get_kulturpreise` | Nein |
| **im Open-Data-Katalog des BAK nach spezifischen Datensätzen suchen** | `bak_get_opendata` | Nein |
| **das Verzeichnis der lebendigen Traditionen der Schweiz durchsuchen** | `bak_list_traditions` | Nein |
| **die detaillierte Beschreibung einer lebendigen Tradition abrufen** | `bak_get_tradition_detail` | Nein |
