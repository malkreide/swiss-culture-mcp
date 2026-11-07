# Herkunft der Fixtures

**Erzeugt von `scripts/record_fixtures.py`. Nicht von Hand pflegen.**

Aufgezeichnet am **2026-11-07**.

Ohne Datum ist «gemessen» nach zwei Jahren von «angenommen» nicht mehr
zu unterscheiden — die Datei sieht gleich aus.

## Dieser Server braucht keine Zugangsdaten

Damit ist seine gesamte Adressliste pruefbar. Aufgezeichnet ist
deshalb, ob jede Adresse, die er baut oder als Quelle ausgibt,
tatsaechlich etwas liefert.

## Vier Kontrollen

| Kontrolle | Antwort | Was sie traegt |
|---|---|---|
| erfundener geo.admin.ch-Dienst | 404 | die Dienstnamen sind echt |
| erfundener BAK-Pfad | 404 | der 404 der Baukultur-Seite ist echt |
| erfundene News-Organisationsnummer | kleinerer Feed | `org-nr=314` filtert wirklich |
| erfundener Tradition-Slug | 404 | die Slug-Antworten sind echt |

## Ein Beinahe-Fehlbefund, der hierher gehoert

Der erste Testabruf einer Traditionsseite schlug fehl, weil ein Slug
geraten worden war. Dieses Skript zieht die Slugs deshalb aus der Liste.

## Der Umbau von lebendige-traditionen.ch

Die fruehere Listenseite `/tradition/de/home/liste/liste.html` antwortet
seit dem Umbau mit 404 (festgestellt am 3.11.2026, am 16.8.2026 noch 200).
Die Website laedt ihre Inhalte als JSON von `/api/collector/de/<slug>.json`;
gemessen und aufgezeichnet wird jetzt diese Schnittstelle. Die
`*.json.gz` sind ihre Antworten, unveraendert — keine von Hand
geschriebenen Fixtures mehr.

Das Skript bricht ab, wenn eine Kontrolle nicht mehr traegt, wenn eine
lebende Adresse stirbt oder wenn die tote zurueckkehrt.

## `adressen.json`

- **Quelle:** `api3.geo.admin.ch, opendata.swiss, bak.admin.ch, lebendige-traditionen.ch`
- **Aufgezeichnet:** 2026-11-07
- **Auswahl:** Statuscode, Content-Type und Groesse je Adresse, die dieser Server baut oder ausgibt — samt vier Kontrollen mit erfundenen Werten (Dienst, Pfad, Organisationsnummer, Tradition-Slug). Die Traditions-Slugs stammen aus der Liste und nicht aus einem Einfall: Ein geratener Slug erzeugte beim ersten Versuch einen 404, der wie ein Befund aussah und keiner war
- **Groesse:** 5238 B
- **SHA-256:** `4050148b2dc47107b4bae471acf98226952803b78651b6e955c14bb4f267170e`

## `traditionen_liste.json.gz`

- **Quelle:** `https://www.lebendige-traditionen.ch/api/collector/de/alle-traditionen.json`
- **Aufgezeichnet:** 2026-11-07
- **Auswahl:** Die Antwort der Traditionsliste, unveraendert: 228 Traditionen. Unkomprimiert 137581 B
- **Groesse:** 15657 B
- **SHA-256:** `79c941c370d4dbad51b106c28b5f555549c573e05066860a98b54ece739d341b`

## `tradition_basler-fasnacht.json.gz`

- **Quelle:** `https://www.lebendige-traditionen.ch/api/collector/de/basler-fasnacht.json`
- **Aufgezeichnet:** 2026-11-07
- **Auswahl:** Die Antwort der Detailseite basler-fasnacht, unveraendert. Unkomprimiert 15604 B
- **Groesse:** 4565 B
- **SHA-256:** `eaa2320d156a1ddd17f401662bbed0fcb7a727d91a4fe9e1c31173f40d8d1913`

## `tradition_alphorn-und-buechelspiel.json.gz`

- **Quelle:** `https://www.lebendige-traditionen.ch/api/collector/de/alphorn-und-buechelspiel.json`
- **Aufgezeichnet:** 2026-11-07
- **Auswahl:** Die Antwort der Detailseite alphorn-und-buechelspiel, unveraendert. Unkomprimiert 18490 B
- **Groesse:** 4853 B
- **SHA-256:** `00e44f7bcb45fc3cebe0461535b111b1e6780226cffddb461c1c24a5a6e18a43`

## `tradition_gebaerdensprachen.json.gz`

- **Quelle:** `https://www.lebendige-traditionen.ch/api/collector/de/gebaerdensprachen.json`
- **Aufgezeichnet:** 2026-11-07
- **Auswahl:** Die Antwort der Detailseite gebaerdensprachen, unveraendert. Unkomprimiert 11198 B
- **Groesse:** 3300 B
- **SHA-256:** `58a3390aa87bd5bfb8a08668173d73d1d6f0c8631bb9b81ef453cde0d467d6b4`
