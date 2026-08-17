"""Gezaehlt werden Ortsbilder, nicht Features.

Der `find`-Endpunkt von `api3.geo.admin.ch` liefert je ISOS-Objekt mehrere
Features. `bak_isos_by_kanton` deduplizierte nach `id` und meldete deshalb
Features als Objekte: fuer GR 507 statt der 105, die der VISOS-Anhang
festsetzt (SR 451.12, Stand 1.6.2026). Fuer ZH stimmten beide Zaehlweisen
zufaellig ueberein — dort traegt jedes Objekt genau eine Feature-ID.

Diese Datei prueft die Mechanik ohne Netz. Dass die Quelle wirklich mehrere
Features je Objekt liefert, kann sie nicht zeigen — das tut der Live-Test
`test_live_isos_anzahl_je_kanton`, der gegen die amtlichen Zahlen prueft.
"""

from __future__ import annotations

from swiss_culture_mcp.server import _dedup_objekte


def _feature(fid: str, nummer: int | None, name: str = "Ort") -> dict:
    attrs: dict = {"name": name}
    if nummer is not None:
        attrs["nummer"] = nummer
    return {"id": fid, "attributes": attrs}


def test_mehrere_features_eines_objekts_zaehlen_einmal() -> None:
    """Der Fall GR: ein Ortsbild, viele Feature-IDs."""
    results = [_feature(f"id-{i}", 1993, "Cinuos-chel") for i in range(51)]
    assert len(_dedup_objekte(results)) == 1
    # Die alte Zaehlweise als Kontrast — genau sie ergab fuer GR 507.
    assert len({r["id"] for r in results}) == 51


def test_verschiedene_objekte_bleiben_getrennt() -> None:
    """Sonst wuerde die Korrektur untereinander zusammenlegen, was getrennt ist."""
    results = [_feature("a", 5279, "Andelfingen"), _feature("b", 5290, "Bachs")]
    assert len(_dedup_objekte(results)) == 2


def test_das_erste_vorkommen_bleibt_erhalten() -> None:
    """Die Tools formatieren den behaltenen Eintrag — er darf nicht wechseln."""
    results = [
        _feature("zuerst", 5791, "Winterthur"),
        _feature("danach", 5791, "Winterthur"),
    ]
    behalten = _dedup_objekte(results)
    assert [r["id"] for r in behalten] == ["zuerst"]


def test_eintraege_ohne_nummer_fallen_nicht_zusammen() -> None:
    """Der Rueckfall auf `id` muss je Eintrag greifen, nicht global.

    Ein gemeinsamer Schluessel fuer alle nummerlosen Eintraege (etwa `None`)
    liesse sie zu einem einzigen verschmelzen — aus zwei Objekten wuerde
    stillschweigend eines.
    """
    results = [_feature("a", None, "Ohne A"), _feature("b", None, "Ohne B")]
    assert len(_dedup_objekte(results)) == 2


def test_nummer_schlaegt_id_und_id_vermischt_sich_nicht_mit_nummer() -> None:
    """Getrennte Namensraeume: `id` 5279 ist nicht Objekt-Nummer 5279."""
    results = [_feature("5279", None, "Zufaellig gleiche id"), _feature("x", 5279, "Andelfingen")]
    assert len(_dedup_objekte(results)) == 2


def test_leere_eingabe() -> None:
    assert _dedup_objekte([]) == []
