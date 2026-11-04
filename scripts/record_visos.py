#!/usr/bin/env python3
"""Zeichnet die Sollwert-Quelle des ISOS-Live-Tests auf: Anhang 1 der VISOS.

    python scripts/record_visos.py

WAS ES AUFZEICHNET. Die Fassungsliste der VISOS (SR 451.12) aus der
SPARQL-Schnittstelle von Fedlex und die deutsche HTML-Ausgabe der Fassung, die
heute gilt. Dagegen ist `scripts/visos_anhang.py` geschrieben, und
`tests/test_visos_anhang.py` prueft den Leser offline gegen diese Aufnahme.

WARUM EIN EIGENES SKRIPT. `scripts/record_fixtures.py` misst die Adressen, die
der Server baut, und bricht ab, sobald eine davon stirbt — mit Absicht, denn
dann gehoert der Server behoben und nicht die Aufnahme erneuert. Fedlex ist
keine solche Adresse, sondern der Massstab des Live-Tests. Haengt seine
Aufnahme am selben Lauf, kann man sie nicht erneuern, solange irgendeine
fremde Website kaputt ist. Am 3.11.2026 war genau das der Fall:
lebendige-traditionen.ch war umgebaut, der Recorder brach ab, und die
VISOS-Aufnahme waere nie entstanden.

DIE KONTROLLE. Dieselbe Abfrage mit einer erfundenen ELI muss leer bleiben.
Sonst belegt die Fassungsliste nichts: Eine Abfrage, die immer etwas liefert,
liefert auch fuer die VISOS etwas.

Das Skript bricht ab, wenn die Kontrolle nicht traegt, wenn am Stichtag nicht
genau eine Fassung gilt, oder wenn Anhang 1 nicht alle 26 Kantone nennt.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import visos_anhang

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
PROVENANCE = FIXTURES / "PROVENANCE_VISOS.md"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; swiss-culture-mcp-fixtures/1.0)"}
ELI_ERFUNDEN = f"{visos_anhang.ELI.rsplit('/', 1)[0]}/99999"


def record() -> int:
    # Schweizer Zeit: Eine Fassung tritt um Mitternacht in Zuerich in Kraft.
    stichtag = datetime.now(ZoneInfo("Europe/Zurich")).date()
    sparql = {"Accept": "application/sparql-results+json"}

    with httpx.Client(timeout=90.0, follow_redirects=True, headers=HEADERS) as c:

        def fassungen_von(eli: str) -> dict:
            r = c.get(
                visos_anhang.SPARQL, params={"query": visos_anhang.abfrage(eli)}, headers=sparql
            )
            r.raise_for_status()
            return json.loads(r.text)

        kontrolle = fassungen_von(ELI_ERFUNDEN)["results"]["bindings"]
        if kontrolle:
            raise SystemExit(
                f"KONTROLLE: Die erfundene ELI {ELI_ERFUNDEN} liefert {len(kontrolle)} "
                "Fassung(en). Dann belegt die Fassungsliste der VISOS nichts."
            )
        antwort = fassungen_von(visos_anhang.ELI)
        fassung = visos_anhang.gueltige_fassung(visos_anhang.parse_fassungen(antwort), stichtag)
        r = c.get(fassung.html[0])
        r.raise_for_status()
        html = r.content

    eintraege = visos_anhang.parse_anhang1(html.decode("utf-8"))
    kantone = {e.kanton for e in eintraege}
    if len(kantone) != 26:
        raise SystemExit(
            f"Anhang 1 der Fassung {fassung.kennung} nennt {len(kantone)} Kantone statt 26. "
            "Erst die Quelle ansehen, dann aufzeichnen."
        )

    FIXTURES.mkdir(parents=True, exist_ok=True)
    fassungen_text = json.dumps(antwort, ensure_ascii=False, indent=2) + "\n"
    (FIXTURES / "visos_fassungen.json").write_text(fassungen_text, encoding="utf-8")
    # Nur die Ausgabe der gueltigen Fassung bleibt liegen: Eine aeltere ohne
    # Eintrag in PROVENANCE_VISOS.md waere eine Aufnahme ohne Herkunft.
    for alt in FIXTURES.glob("visos_anhang1_*.html.gz"):
        alt.unlink()
    anhang_name = f"visos_anhang1_{fassung.kennung}.html.gz"
    # `mtime=0`, damit dieselbe Antwort dieselbe Datei ergibt.
    anhang_gz = gzip.compress(html, compresslevel=9, mtime=0)
    (FIXTURES / anhang_name).write_bytes(anhang_gz)

    je_kanton = {k: sum(e.kanton == k for e in eintraege) for k in sorted(kantone)}
    _write_provenance(
        stichtag=stichtag.isoformat(),
        fassung=fassung,
        eintraege=len(eintraege),
        je_kanton=je_kanton,
        dateien=[
            ("visos_fassungen.json", visos_anhang.SPARQL, fassungen_text.encode("utf-8")),
            (anhang_name, fassung.html[0], anhang_gz),
        ],
        unkomprimiert=len(html),
    )
    print(f"ok  visos_fassungen.json   {len(fassungen_text.encode('utf-8')):>7} B")
    print(f"ok  {anhang_name}  {len(anhang_gz):>7} B (gz, {len(html)} B)")
    print(f"Fassung {fassung.kennung}: {len(eintraege)} Eintraege, Stichtag {stichtag}")
    return 0


def _write_provenance(
    *,
    stichtag: str,
    fassung: visos_anhang.Fassung,
    eintraege: int,
    je_kanton: dict[str, int],
    dateien: list[tuple[str, str, bytes]],
    unkomprimiert: int,
) -> None:
    lines = [
        "# Herkunft der VISOS-Aufnahmen",
        "",
        "**Erzeugt von `scripts/record_visos.py`. Nicht von Hand pflegen.**",
        "",
        f"Aufgezeichnet am **{stichtag}** (Stichtag Europe/Zurich).",
        "",
        "Die Sollwert-Quelle des ISOS-Live-Tests: Anhang 1 der VISOS (SR 451.12),",
        "gelesen von `scripts/visos_anhang.py`. Keine Adresse, die der Server",
        "baut — deshalb nicht in `adressen.json` und nicht in der Allowlist.",
        "",
        "## Kontrolle",
        "",
        f"Dieselbe Abfrage mit der erfundenen ELI `{ELI_ERFUNDEN}` lieferte keine",
        "Fassung. Ohne das belegte die Fassungsliste nichts.",
        "",
        "## Aufgezeichnete Fassung",
        "",
        f"- **ELI:** `{fassung.eli}`",
        f"- **Gueltig ab:** {fassung.ab.isoformat()}",
        f"- **Gueltig bis:** {fassung.bis.isoformat() if fassung.bis else 'offen'}",
        f"- **Anhang 1:** {eintraege} Eintraege",
        "",
        "| " + " | ".join(je_kanton) + " |",
        "|" + "---|" * len(je_kanton),
        "| " + " | ".join(str(n) for n in je_kanton.values()) + " |",
        "",
    ]
    for name, url, inhalt in dateien:
        lines += [
            f"## `{name}`",
            "",
            f"- **Quelle:** `{url}`",
            f"- **Groesse:** {len(inhalt)} B"
            + (f" (gzip, unkomprimiert {unkomprimiert} B)" if name.endswith(".gz") else ""),
            f"- **SHA-256:** `{hashlib.sha256(inhalt).hexdigest()}`",
            "",
        ]
    PROVENANCE.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    try:
        raise SystemExit(record())
    except (httpx.HTTPError, visos_anhang.FedlexLeseError) as exc:
        print(f"FEHLER: Fedlex nicht lesbar: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
