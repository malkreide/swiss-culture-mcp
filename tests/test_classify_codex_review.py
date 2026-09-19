"""Was das Codex-Gate belegt — und was es bewusst nicht belegt.

Die gefaehrlichen Faelle sind hier nicht die roten, sondern die gruenen:
Ein Gate, das «geprueft» meldet, ohne dass geprueft wurde, ist schlimmer als
keines. Es traegt den Haken, den #56 bis #60 nicht tragen konnten, und
niemand sieht ihm an, dass er leer ist.

Drei solche Faelle stehen unten je einzeln:

* Die Kontingent-Meldung sieht aus wie Stille und ist eine Absage.
* Ein Review-Objekt aus einem FRUEHEREN Commit belegt nichts ueber den, der
  gemergt wird.
* Die Statustabelle («Running») ist kein Urteil — und darf umgekehrt auch
  nicht als unbekannter Text das Gate sofort rot faerben.

HERKUNFT DER FIXTURES
---------------------
Die Statuskommentare kommen aus `tests/fixtures/codex_kommentare.json` und
sind woertliche Antwortkoerper der GitHub-API dieses Repos, aufgezeichnet am
19.09.2026: die `Completed`-Tabellen von PR #56, #61 und #62, die
Environment-Meldung vom Draft-Stand des PR #62, und — als einziges Paar —
derselbe Kommentar auf #62 einmal waehrend und einmal nach dem Lauf.

Dass dieses Paar existiert, ist selbst ein Befund: Hier stand eine Fassung
lang, der laufende Zustand sei gar nicht aufzuzeichnen, weil Codex die
Tabelle in Ort fortschreibt. Aufzuzeichnen ist er sehr wohl — nur eben
waehrend des Laufs. Fuer die `Running`-Tabelle stand deshalb zuerst eine
fremde Aufnahme aus einem anderen Repo hier; sie ist ersetzt.

Die uebrigen Meldungstexte (Befundlos, Kontingent) stehen woertlich in
CLAUDE.md, aufgezeichnet am 21.8., 22.8. und 23.8.2026.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from classify_codex_review import (  # noqa: E402
    CLEAR,
    ENVIRONMENT,
    PENDING,
    PROVEN,
    QUOTA,
    REVIEWED,
    RUNNING,
    UNKNOWN,
    classify,
)

_WURZEL = Path(__file__).resolve().parents[1]
_SKRIPT = _WURZEL / "scripts" / "classify_codex_review.py"
_FIXTURE = _WURZEL / "tests" / "fixtures" / "codex_kommentare.json"

CODEX = {"login": "chatgpt-codex-connector[bot]"}
MENSCH = {"login": "malkreide"}

# Ein Head, zu dem es in keiner Fixture eine Tabellenzeile gibt — fuer die
# Faelle, in denen nur ein Meldungstext geprueft wird.
HEAD = "162f2b6b3ebc9b615179e4a02855f3bf1f736cda"
FRUEHER = "bfe7ab705ecc2a7beae94cc9bbeba4cc732bebd6"


def _aufgezeichnet() -> dict[str, dict]:
    """Die aufgezeichneten Statuskommentare, nach Zustand und Quelle."""
    daten = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    return {k["_quelle"].split(",")[0]: k for k in daten["kommentare"]}


_ROH = _aufgezeichnet()

# PR #56 dieses Repos, Head b503b48 — die Tabelle stand um 06:36:00 auf
# «Running» und um 06:38:03 auf «Completed», bei unveraenderter Kommentar-ID.
FERTIG = _ROH["malkreide/swiss-culture-mcp PR #56"]["body"]
HEAD_56 = "b503b48654912edb38a81e47178b5f1143e9debb"
# PR #61 desselben Repos — zweite Aufzeichnung, anderer Commit.
FERTIG_61 = _ROH["malkreide/swiss-culture-mcp PR #61"]["body"]
HEAD_61 = "9a035dee86de48e355a93f6676253a313def1d75"
# PR #62 dieses Repos: derselbe Kommentar 56 Sekunden vor und nach dem Ende
# des Laufs. Gleiche ID, `created_at` unveraendert, `updated_at` gewandert.
LAEUFT = _ROH["malkreide/swiss-culture-mcp PR #62 (laufend)"]["body"]
FERTIG_62 = _ROH["malkreide/swiss-culture-mcp PR #62 (fertig)"]["body"]
HEAD_62 = "f09a9e0c88a7276ff9a4e2d629a1b5c80f2a6b69"

# PR #62 dieses Repos, 19.09.2026 09:06:06Z — woertlich aus der Fixture,
# samt Markdown-Link mitten im Satz.
ENVIRONMENT_MELDUNG = _ROH["malkreide/swiss-culture-mcp PR #62 (Draft)"]["body"]


def kommentar(body: str, *, user=CODEX, created_at="2026-09-19T07:00:00Z") -> dict:
    return {"user": user, "body": body, "created_at": created_at}


def review(commit_id: str, *, user=CODEX) -> dict:
    return {"user": user, "commit_id": commit_id, "state": "COMMENTED"}


def _statustabelle(status: str, commit: str) -> str:
    """Die Tabelle mit ausgetauschter Statuszelle — Geruest aus der Fixture.

    Kopf- und Trennzeile stehen dabei bewusst drin: Sie sind der Grund, warum
    die Commit-Spalte auf eine Hex-Form geprueft wird und nicht auf eine
    Spaltennummer. Ein Parser, der sie mitzaehlt, liest «Commit» als Commit.
    """
    return (
        "<!-- codex-pull-request-review-summary -->\n\n## Codex Review Summary\n\n"
        "| Review | Status | Commit | Review trigger |\n| --- | --- | --- | --- |\n"
        f"| 📝 **Code Review** | {status} | `{commit}` | Draft marked ready |\n"
    )


# ─────────────────────── Die Fixture ist, was sie zu sein behauptet ───────────


def test_die_fixture_traegt_echte_aufgezeichnete_koerper() -> None:
    """Sichert alles darunter gegen eine stillschweigend leere Fixture ab.

    Faellt die Datei weg oder wechselt ihr Aufbau, waeren `FERTIG` und
    `LAEUFT` leere Strings — und jeder Tabellen-Test unten liefe gegen
    `pending`, ohne dass jemand sieht, dass nichts geprueft wurde.
    """
    daten = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    assert daten["_herkunft"]["aufgezeichnet_am"] == "2026-09-19"
    assert len(daten["kommentare"]) == 6
    for koerper in (FERTIG, FERTIG_61, FERTIG_62, LAEUFT):
        assert "<!-- codex-pull-request-review-summary -->" in koerper
        assert "| Review | Status | Commit | Review trigger |" in koerper
    # Die Environment-Meldung ist gerade KEINE Tabelle — sonst liefe der
    # Test unten, der sie gegen eine Tabelle antreten laesst, ins Leere.
    assert "codex-pull-request-review-summary" not in ENVIRONMENT_MELDUNG


# ─────────────────────────── Die belegenden Faelle ─────────────────────────────


def test_ein_review_objekt_zum_head_belegt_die_pruefung() -> None:
    state, _ = classify([review(HEAD)], [], HEAD)
    assert state == REVIEWED
    assert state in PROVEN


def test_die_befundlos_meldung_belegt_die_pruefung_ebenso() -> None:
    """Der Fall, den ein Gate am leichtesten falsch zaehlt.

    Ein befundloser Lauf erzeugt KEIN Review-Objekt, sondern einen
    gewoehnlichen Issue-Kommentar. Wer nur das Objekt gelten laesst, haelt
    jeden sauberen Lauf fuer ungeprueft und blockiert genau die PRs, an denen
    nichts auszusetzen war.
    """
    state, _ = classify([], [kommentar("Codex Review: Didn't find any major issues. Swish!")], HEAD)
    assert state == CLEAR
    assert state in PROVEN


@pytest.mark.parametrize(
    "schlusssatz",
    ["Swish!", "Delightful!", "Keep it up!", "More of your lovely PRs please."],
)
def test_der_wechselnde_schlusssatz_aendert_nichts(schlusssatz: str) -> None:
    """Stabil ist nur der Satz davor; der Schluss wechselt bei jedem Lauf.

    Ohne diesen Fall waere ein Marker denkbar, der zufaellig auf «Swish!»
    passt und beim naechsten Lauf ins Leere greift — das Gate haette dann
    einen sauberen Review als ungeprueft blockiert.
    """
    body = f"Codex Review: Didn't find any major issues. {schlusssatz}"
    assert classify([], [kommentar(body)], HEAD)[0] == CLEAR


def test_der_typografische_apostroph_aendert_nichts() -> None:
    """«Didn't» traegt je nach Zeichensatz ' oder ’ — gematcht wird ohne."""
    body = "Codex Review: Didn’t find any major issues. Swish!"
    assert classify([], [kommentar(body)], HEAD)[0] == CLEAR


# ─────────────────── Die Faelle, die gruen aussehen und es nicht sind ──────────


def test_die_kontingent_meldung_ist_kein_freispruch() -> None:
    """Die gefaehrlichste Verwechslung: eine Absage, die wie Stille aussieht.

    Am 21.8.2026 sind portfolioweit 32 PRs mit formal erfuelltem Haekchen
    gemergt worden, waehrend das Kontingent weg war, am 22.8. noch einmal 43.
    Faellt dieser Fall auf `pending` oder gar `clear`, baut dieses Gate
    denselben Fehlalarm nach.
    """
    body = "You have reached your Codex usage limits for code reviews."
    state, reason = classify([], [kommentar(body)], HEAD)
    assert state == QUOTA
    assert state not in PROVEN
    assert "geprueft" in reason


def test_die_fehlende_environment_ist_auch_kein_freispruch() -> None:
    """Der vierte Grund — er kam erst zum Vorschein, als der dritte wegfiel."""
    body = "To use Codex here, create an environment for this repo."
    state, reason = classify([], [kommentar(body)], HEAD)
    assert state == ENVIRONMENT
    assert state not in PROVEN
    assert "je Repo" in reason


def test_die_environment_meldung_woertlich_mit_markdown_link() -> None:
    """So, wie Codex sie wirklich gesetzt hat — der Link steht mitten im Satz."""
    state, _ = classify([], [kommentar(ENVIRONMENT_MELDUNG)], HEAD)
    assert state == ENVIRONMENT
    assert state not in PROVEN


def test_ein_review_aus_einem_frueheren_commit_belegt_den_head_nicht() -> None:
    """Sonst deckte ein Review von gestern den Commit von heute mit ab.

    Genau das ist die Luecke, die ein Gate ohne Commit-Bindung haette: Codex
    laeuft auf «Draft marked ready», ein spaeterer Push aendert den Head, und
    der alte Haken gilt weiter.
    """
    state, _ = classify([review(FRUEHER)], [], HEAD)
    assert state == PENDING
    assert state not in PROVEN


def test_ein_kommentar_von_vor_dem_stichtag_zaehlt_nicht() -> None:
    alt = kommentar(
        "Codex Review: Didn't find any major issues.", created_at="2026-09-18T06:00:00Z"
    )
    state, _ = classify([], [alt], HEAD, since="2026-09-19T06:00:00Z")
    assert state == PENDING


def test_ein_mensch_kann_das_gate_nicht_gruen_schreiben() -> None:
    """Ohne Autor-Pruefung genuegte ein Kommentar mit dem richtigen Satz."""
    body = "Codex Review: Didn't find any major issues. Swish!"
    assert classify([], [kommentar(body, user=MENSCH)], HEAD)[0] == PENDING
    assert classify([review(HEAD, user=MENSCH)], [], HEAD)[0] == PENDING


def test_auch_die_statustabelle_zaehlt_nur_von_codex() -> None:
    """Sonst schriebe ein Mensch die Tabelle ab und das Gate glaubte ihr."""
    assert classify([], [kommentar(FERTIG, user=MENSCH)], HEAD_56)[0] == PENDING


# ─────────────────────── Die Statustabelle als Urteil ──────────────────────────


def test_eine_abgeschlossene_tabelle_ohne_review_objekt_heisst_keine_befunde() -> None:
    """Der Fall, der ein Gate ohne Tabellen-Lesen widerlegt.

    Auf #56 bis #61 dieses Repos war die Tabelle das EINZIGE Artefakt: kein
    Review-Objekt, keine Review-Threads, keine Befundlos-Meldung, keine
    Reaktion. Ein Gate, das sie ueberspringt, blockierte jeden sauberen PR
    zwanzig Minuten und meldete ihn dann rot.
    """
    state, _ = classify([], [kommentar(FERTIG)], HEAD_56)
    assert state == CLEAR
    assert state in PROVEN


def test_die_zweite_aufzeichnung_wird_genauso_gelesen() -> None:
    """Zwei Koerper, zwei Commits — sonst haengt alles an einer Aufnahme."""
    assert classify([], [kommentar(FERTIG_61)], HEAD_61)[0] == CLEAR
    # Und ueber Kreuz darf es gerade nicht passen.
    assert classify([], [kommentar(FERTIG_61)], HEAD_56)[0] == PENDING


def test_clear_behauptet_nicht_mehr_als_gemessen_ist() -> None:
    """`✅ Completed` heisst «Lauf zu Ende», nicht «nichts gefunden».

    Alle sechs Beobachtungen (#56 bis #61) fielen auf PRs, die beim Lauf
    schon gemergt waren; ob ein Befund dort ueberhaupt noch geschrieben wird,
    ist offen. Der Begruendungstext muss das sagen — ein Gate, das «keine
    Befunde» behauptet, wo es nur «angesehen» gemessen hat, ist genau der
    Haken, gegen den es gebaut ist.
    """
    _, reason = classify([], [kommentar(FERTIG)], HEAD_56)
    assert "nicht gegenprobiert" in reason


def test_eine_laufende_tabelle_ist_kein_urteil() -> None:
    state, _ = classify([], [kommentar(LAEUFT)], HEAD_62)
    assert state == RUNNING
    assert state not in PROVEN


def test_laufend_und_gar_nichts_sind_zwei_verschiedene_zustaende() -> None:
    """Beides heisst «noch kein Urteil» und bedeutet Verschiedenes.

    Bei `running` ist eines unterwegs, Warten lohnt. Bei `pending` ist nichts
    in der Luft, und Warten kostet nur Laufzeit. Am 19.09.2026 auf PR #64
    fiel der Unterschied auf: Der Gate-Job schoepfte seine kurze Frist von
    180 s aus, waehrend ein Lauf seit 136 s arbeitete — ein Codex-Lauf
    braucht bis 187 s. Eine Frist, die kuerzer ist als der Lauf, meldet
    «kein Urteil» ueber ein Urteil, das gerade entsteht.

    Solange beide Faelle denselben Namen tragen, kann der Workflow sie nicht
    auseinanderhalten.
    """
    assert RUNNING != PENDING
    assert RUNNING not in PROVEN
    assert classify([], [kommentar(LAEUFT)], HEAD_62)[0] == RUNNING
    assert classify([], [], HEAD_62)[0] == PENDING


def test_die_statustabelle_ist_auch_kein_unbekannter_text() -> None:
    """Die Gegenrichtung, und sie schadet genauso.

    Als Urteil gelesen waere jeder frisch getriggerte PR sofort «geprueft».
    Als unbekannter Text gelesen waere er sofort rot.
    """
    state, reason = classify([], [kommentar(LAEUFT)], HEAD_62)
    assert state not in (UNKNOWN, CLEAR)
    assert "laeuft noch" in reason


def test_die_tabelle_bindet_an_den_commit_nicht_an_die_zeit() -> None:
    """Die Tabelle wird in Ort fortgeschrieben — ihr `created_at` altert.

    Auf #62 ist das Paar aufgezeichnet: dieselbe Kommentar-ID 5740705055,
    `created_at` beide Male 09:15:14, der Koerper um 09:15:14 auf `Running`
    und um 09:16:11 auf `Completed`. Ein `since`-Filter auf `created_at`
    wuerde das fertige Urteil wegwerfen, sobald der Head-Commit juenger ist
    als der erste Tabellen-Post.
    """
    alt = kommentar(FERTIG_62, created_at="2026-09-19T09:15:14Z")
    assert classify([], [alt], HEAD_62, since="2026-09-19T09:16:00Z")[0] == CLEAR


def test_derselbe_kommentar_traegt_nacheinander_zwei_urteile() -> None:
    """Das Paar aus #62, beide Koerper echt, gleiche Kommentar-ID.

    Es ist der Beleg fuer den Satz in CLAUDE.md, den Kommentarkoerper NEU zu
    holen statt ihn zu erinnern: Wer den um 09:15:14 gelesenen Text behaelt,
    haelt einen fertigen Lauf fuer einen laufenden.
    """
    assert classify([], [kommentar(LAEUFT)], HEAD_62)[0] == RUNNING
    assert classify([], [kommentar(FERTIG_62)], HEAD_62)[0] == CLEAR


def test_eine_tabelle_zu_einem_anderen_commit_belegt_den_head_nicht() -> None:
    state, _ = classify([], [kommentar(_statustabelle("✅ **Completed**", "0df577e"))], HEAD_56)
    assert state == PENDING


def test_ein_unbekannter_tabellen_status_wird_zitiert() -> None:
    state, reason = classify([], [kommentar(_statustabelle("💥 **Exploded**", "b503b48"))], HEAD_56)
    assert state == UNKNOWN
    assert "Exploded" in reason


def test_laeuft_schlaegt_fertig_wenn_beides_dasteht() -> None:
    """Zwei Reviews zum selben Commit, einer noch offen — dann wird gewartet.

    Sonst gaebe ein abgeschlossener Code-Review gruenes Licht, waehrend der
    Security-Review noch laeuft. Codex nennt «@codex security review» in
    seinem eigenen Infokasten als zweiten Ausloeser.
    """
    zwei = _statustabelle("✅ **Completed**", "b503b48") + (
        "| 🔒 **Security Review** | 🔄 **Running** | `b503b48` | Draft marked ready |\n"
    )
    assert classify([], [kommentar(zwei)], HEAD_56)[0] == RUNNING


def test_eine_fertige_tabelle_schlaegt_eine_environment_meldung() -> None:
    """Die Reihenfolge, und sie ist in DIESEM Repo gemessen begruendet.

    Am 19.09.2026 um 07:41 lief auf PR #61 ein regulaerer Review durch —
    Statustabelle samt Infokasten «Your team has set up Codex to review pull
    requests in this repo». Um 09:06, 85 Minuten spaeter, kam auf dem
    frisch angelegten Draft-PR #62 die Environment-Meldung. Eine Environment
    war also da; die Meldung belegt ihr Fehlen nicht.

    Deshalb darf sie eine `Completed`-Tabelle zum Head nicht ueberstimmen.
    Ohne diese Reihenfolge faerbte ein einzelner solcher Kommentar das Gate
    rot, obwohl der Lauf nachweislich stattgefunden hat.
    """
    state, _ = classify([], [kommentar(ENVIRONMENT_MELDUNG), kommentar(FERTIG)], HEAD_56)
    assert state == CLEAR


def test_ohne_tabellenzeile_zum_head_gilt_die_environment_meldung() -> None:
    """Die Gegenrichtung — sonst waere der Test darueber ein Freifahrtschein."""
    fremd = _statustabelle("✅ **Completed**", "0df577e")
    state, _ = classify([], [kommentar(ENVIRONMENT_MELDUNG), kommentar(fremd)], HEAD_56)
    assert state == ENVIRONMENT


def test_die_kopfzeile_der_tabelle_ist_keine_statuszeile() -> None:
    """Ohne Head-SHA gibt es keine Commit-Bindung — dann traegt die Hex-Pruefung.

    Mit gesetztem Head filtert schon die Commit-Bindung jede Kopf- und
    Trennzeile heraus (`head_sha.startswith("Commit")` ist nie wahr); die
    Pruefung auf Hex-Ziffern sieht dort nur so aus, als tue sie etwas.

    `--head-sha` ist optional und meint «alles zeigen, was Codex gesagt hat».
    Genau dort wuerde eine Kopfzeile sonst als Status «Status» gelesen und
    die Einordnung auf `unknown` werfen.
    """
    state, _ = classify([], [kommentar(FERTIG)], "")
    assert state == CLEAR


# ─────────────────────────── Unbekanntes und Stille ───────────────────────────


def test_die_konto_absage_wird_zitiert_statt_einsortiert() -> None:
    """Der fuenfte Meldungstext, woertlich aufgezeichnet — und der Beleg,
    dass der Entwurf «unbekanntes zitieren» im Feld getragen hat.

    Am 19.09.2026 auf PR #64 setzte der Gate-Job den `@codex review`-Anstoss
    mit HTTP 201 ab. Codex antwortete vier Sekunden spaeter:

        To use Codex here, create a Codex account and connect to github.

    Der Anstoss ERREICHT Codex also; abgelehnt wird das Konto des Absenders,
    `github-actions[bot]`. Das ist weder Kontingent noch Environment noch
    Befundlosigkeit — und der Klassifizierer hat es im Lauf korrekt als
    `unknown` gemeldet und woertlich zitiert, statt es in die naechstbeste
    Schublade zu zwingen.

    Er bekommt bewusst KEINEN eigenen Marker: Ein Zustand mehr hiesse, das
    Gate koenne dann gruen werden, wenn es ihn erkennt — kann es nicht, es
    wurde nichts geprueft. `unknown` mit Zitat ist die richtige Antwort.
    """
    body = _ROH["malkreide/swiss-culture-mcp PR #64 (Konto)"]["body"]
    state, reason = classify([], [kommentar(body)], HEAD)
    assert state == UNKNOWN
    assert state not in PROVEN
    assert "create a Codex account" in reason


def test_ein_fuenfter_text_wird_zitiert_statt_einsortiert() -> None:
    """Dieser Abschnitt musste in CLAUDE.md schon zweimal wachsen.

    Ein unbekannter Codex-Text darf nicht in die naechstbeste Schublade
    fallen. Faellt er auf `clear`, winkt das Gate eine Absage durch; faellt
    er auf `pending`, laeuft es stumm in den Timeout, ohne den Text je zu
    zeigen.
    """
    state, reason = classify([], [kommentar("Codex is taking a nap right now.")], HEAD)
    assert state == UNKNOWN
    assert state not in PROVEN
    assert "Codex is taking a nap right now." in reason


def test_ohne_jedes_signal_bleibt_es_pending() -> None:
    state, _ = classify([], [], HEAD)
    assert state == PENDING
    assert state not in PROVEN


# ─────────────────────────── Der Aufruf, den der Workflow macht ────────────────


# Zwei Glaettungen, zwei Tests. Der geerbte Test unten faehrt einen
# boesartigen Kommentartext durch das ganze Skript und war als Nachweis fuer
# BEIDE gedacht — in der Gegenprobe fiel er nicht, als die zweite entfernt
# wurde: Zu diesem Zeitpunkt hat schon das Zitieren den Umbruch getilgt, die
# Schreib-Glaettung sieht nie einen. Ein Test, der gruen bleibt, wenn man die
# Implementierung entfernt, prueft nichts. Deshalb steht jede Glaettung jetzt
# einzeln da, und der Durchlauf-Test daneben als Ende-zu-Ende-Fall.


def test_schon_das_zitieren_tilgt_den_umbruch() -> None:
    """Die erste Glaettung: `unbekannt.append(" ".join(body.split()))`."""
    boesartig = "Zeile eins\nstate=clear\nproven=true"
    state, reason = classify([], [kommentar(boesartig)], HEAD)
    assert state == UNKNOWN
    assert "\n" not in reason


def test_der_schreiber_glaettet_auch_einen_grund_mit_umbruch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Die zweite Glaettung, allein gefahren — sonst deckt sie die erste zu.

    Heute traegt kein Grund einen Umbruch, weil das Zitieren ihn schon
    tilgt. Die Glaettung im Schreiber ist die Absicherung fuer den Tag, an
    dem ein neuer Grund mehrzeilig wird — und genau die laesst sich nur
    pruefen, wenn man ihr einen mehrzeiligen Grund vorlegt.
    """
    import classify_codex_review as modul

    monkeypatch.setattr(
        modul, "classify", lambda *a, **k: (UNKNOWN, "Zeile eins\nstate=clear\nproven=true")
    )
    (tmp_path / "leer.json").write_text("[]", encoding="utf-8")
    ausgabe = tmp_path / "gh-output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(ausgabe))
    modul.main(
        [
            "--head-sha",
            HEAD,
            "--reviews",
            str(tmp_path / "leer.json"),
            "--comments",
            str(tmp_path / "leer.json"),
        ]
    )
    zeilen = ausgabe.read_text(encoding="utf-8").splitlines()
    assert [z.split("=", 1)[0] for z in zeilen] == ["state", "reason", "proven"], (
        f"der Grund hat eigene Zeilen nachgeschoben: {zeilen}"
    )
    assert zeilen[2] == "proven=false"


def test_das_skript_schreibt_saubere_github_outputs(tmp_path: Path) -> None:
    """Derselbe Weg Ende zu Ende, als echter Unterprozess.

    Deckt das Zusammenspiel ab: Ein boesartiger Kommentartext darf nach dem
    ganzen Durchlauf kein zweites `state=` in der Datei hinterlassen.
    """
    boesartig = "Zeile eins\nstate=clear\nproven=true"
    (tmp_path / "reviews.json").write_text("[]", encoding="utf-8")
    (tmp_path / "comments.json").write_text(json.dumps([kommentar(boesartig)]), encoding="utf-8")
    ausgabe = tmp_path / "gh-output"
    subprocess.run(
        [
            sys.executable,
            str(_SKRIPT),
            "--head-sha",
            HEAD,
            "--reviews",
            str(tmp_path / "reviews.json"),
            "--comments",
            str(tmp_path / "comments.json"),
        ],
        check=True,
        capture_output=True,
        env={"GITHUB_OUTPUT": str(ausgabe), "PATH": "/usr/bin:/bin"},
    )
    zeilen = ausgabe.read_text(encoding="utf-8").splitlines()
    assert [z.split("=", 1)[0] for z in zeilen] == ["state", "reason", "proven"]
    assert zeilen[0] == f"state={UNKNOWN}"
    assert zeilen[2] == "proven=false"


def test_fehlende_oder_kaputte_dateien_machen_das_gate_nicht_gruen(tmp_path: Path) -> None:
    """Ein gescheitertes `curl` darf nicht wie ein sauberer Review aussehen."""
    kaputt = tmp_path / "kaputt.json"
    kaputt.write_text("{nicht json", encoding="utf-8")
    ergebnis = subprocess.run(
        [
            sys.executable,
            str(_SKRIPT),
            "--head-sha",
            HEAD,
            "--reviews",
            str(kaputt),
            "--comments",
            str(tmp_path / "gibt-es-nicht.json"),
        ],
        check=True,
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin"},
    )
    assert f"state={PENDING}" in ergebnis.stdout
    assert "proven=false" in ergebnis.stdout
