# Herkunft der Fixtures

**Erzeugt von `scripts/record_fixtures.py`. Nicht von Hand pflegen.**

Aufgezeichnet am **2026-08-16**.

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
| erfundener Tradition-Slug | 404 | die Slug-Seiten sind echt |

## Ein Beinahe-Fehlbefund, der hierher gehoert

`TRADITIONS_BASE` allein antwortet mit 404 — dem Stamm fehlt ein
`.html`. Daraus folgt **nichts**: Der Server ruft den Stamm nie allein
auf, sondern nur `/liste/liste.html` und `/traditionen/<slug>.html`,
und beide antworten mit 200. Der erste Testabruf schlug fehl, weil ein
Slug geraten worden war. Dieses Skript zieht die Slugs deshalb aus der
Listenseite.

Das Skript bricht ab, wenn eine Kontrolle nicht mehr traegt, wenn eine
lebende Adresse stirbt oder wenn die tote zurueckkehrt.

## `adressen.json`

- **Quelle:** `api3.geo.admin.ch, opendata.swiss, bak.admin.ch, lebendige-traditionen.ch`
- **Aufgezeichnet:** 2026-08-16
- **Auswahl:** Statuscode, Content-Type und Groesse je Adresse, die dieser Server baut oder ausgibt — samt vier Kontrollen mit erfundenen Werten (Dienst, Pfad, Organisationsnummer, Tradition-Slug). Die Traditions-Slugs stammen aus der Listenseite und nicht aus einem Einfall: Ein geratener Slug erzeugte beim ersten Versuch einen 404, der wie ein Befund aussah und keiner war
- **Groesse:** 4777 B
- **SHA-256:** `5b2cf8c72d7487b83e3acbae37da6298b4d68215853f7ae3df43b463c4528552`
