# Herkunft der VISOS-Aufnahmen

**Erzeugt von `scripts/record_visos.py`. Nicht von Hand pflegen.**

Aufgezeichnet am **2026-11-03** (Stichtag Europe/Zurich).

Die Sollwert-Quelle des ISOS-Live-Tests: Anhang 1 der VISOS (SR 451.12),
gelesen von `scripts/visos_anhang.py`. Keine Adresse, die der Server
baut — deshalb nicht in `adressen.json` und nicht in der Allowlist.

## Kontrolle

Dieselbe Abfrage mit der erfundenen ELI `https://fedlex.data.admin.ch/eli/cc/2019/99999` lieferte keine
Fassung. Ohne das belegte die Fassungsliste nichts.

## Aufgezeichnete Fassung

- **ELI:** `https://fedlex.data.admin.ch/eli/cc/2019/673/20261101`
- **Gueltig ab:** 2026-11-01
- **Gueltig bis:** offen
- **Anhang 1:** 1255 Eintraege

| AG | AI | AR | BE | BL | BS | FR | GE | GL | GR | JU | LU | NE | NW | OW | SG | SH | SO | SZ | TG | TI | UR | VD | VS | ZG | ZH |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 61 | 2 | 9 | 180 | 33 | 3 | 45 | 20 | 10 | 107 | 32 | 32 | 29 | 7 | 8 | 62 | 17 | 36 | 18 | 66 | 137 | 12 | 141 | 101 | 14 | 73 |

## `visos_fassungen.json`

- **Quelle:** `https://fedlex.data.admin.ch/sparqlendpoint`
- **Groesse:** 5495 B
- **SHA-256:** `9c14ad78bb11327a0237fc30c0dda6ec4120529445d96ecfe6b7e3003a9c892b`

## `visos_anhang1_20261101.html.gz`

- **Quelle:** `https://fedlex.data.admin.ch/filestore/fedlex.data.admin.ch/eli/cc/2019/673/20261101/de/html/fedlex-data-admin-ch-eli-cc-2019-673-20261101-de-html-2.html`
- **Groesse:** 28380 B (gzip, unkomprimiert 543639 B)
- **SHA-256:** `13e762a4aefbbd4849fecc3c015d23da132b11f4605e5b28b13eaba7c633c371`
