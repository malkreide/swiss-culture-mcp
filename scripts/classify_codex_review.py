#!/usr/bin/env python3
"""Hat Codex diesen Commit angesehen — und was kam dabei heraus?

WARUM ES DIESES GATE GIBT
-------------------------
In diesem Repo wurde am 19.09.2026 an fuenf PRs gemessen, wie viel Zeit
zwischen «ready for review» und Merge lag: 57 s (#56), 4 s (#57), 20 s (#58),
2 s (#59), 63 s (#60). Ein Codex-Lauf braucht 36 bis 124 Sekunden. In keinem
der fuenf Faelle lag beim Merge ein Ergebnis vor; bei #57 und #59 startete der
Lauf erst NACH dem Merge. Die Zeile «Codex-Review beantwortet oder behoben»
in `.github/pull_request_template.md` war damit ein Haken, den niemand haette
setzen koennen. Die Einzelheiten stehen in CLAUDE.md unter «Der Review wird
nicht abgewartet».

Zwei Anlaeufe, das ueber einen vereinbarten Ablauf zu regeln, sind
gescheitert. Was bleibt, ist eine Schranke statt einer Vereinbarung — und
eine Schranke braucht einen Check-Run, auf den Branch Protection warten kann.
Codex erzeugt keinen: Ein Befund ist ein Review-Objekt, ein befundloser Lauf
ein gewoehnlicher Issue-Kommentar, der Laufstatus eine Tabelle in einem
dritten Kommentar. Keines von dreien kann ein Check sein oder «approven».
Damit ueberhaupt jemand darauf warten kann, muss das Urteil erst als Check
ausgegeben werden. Das tut der Workflow, der dieses Skript aufruft.

VIER GRUENDE, WARUM CODEX SCHWEIGT — NUR EINER IST HARMLOS
----------------------------------------------------------
Die Einordnung unten stammt nicht aus einem Ratespiel ueber Statuscodes,
sondern aus den vier in CLAUDE.md dokumentierten Faellen:

  reviewed     Ein Review-OBJEKT zum Head-Commit. Codex hat Befunde. ROT.
  clear        Die Befundlos-Meldung («Didn't find any major issues»). Ein
               gewoehnlicher Issue-Kommentar, KEIN Review-Objekt.
  quota        «You have reached your Codex usage limits for code reviews.»
  environment  «To use Codex here, create an environment for this repo.»

NUR `clear` GIBT DEN PR FREI. `reviewed` heisst: Codex hat hingesehen UND
etwas gefunden — das Gate bleibt rot, bis ein Lauf ohne Befund vorliegt.

Das war bis zum 19.09.2026 anders: `reviewed` zaehlte zu PROVEN, weil das
Gate nur belegen sollte, DASS hingesehen wurde. In der Praxis hiess das, dass
ein PR mit offenen Codex-Befunden gruen durchging — genau die Luecke, gegen
die das Gate gebaut ist, eine Ebene hoeher. Die Entscheidung, `reviewed` rot
zu machen, ist bewusst getroffen worden und kostet etwas: Jede Befundrunde
braucht einen weiteren Codex-Lauf, und der PR wird erst frei, wenn einer
davon nichts mehr findet.

Wer nur das Review-Objekt als Beleg gelten laesst, baut den umgekehrten
Fehlalarm: Dann gilt jeder befundlose Lauf als ungeprueft. Deshalb bleibt
`clear` ein vollwertiger Beleg — die Tabelle auf `Completed` ohne
Review-Objekt ist das, was ein sauberer Lauf hier hinterlaesst.

`quota` und `environment` sind ueberhaupt kein Beleg. Sie sehen aus wie
Stille und sind eine Absage — deshalb faerben sie das Gate rot, statt es
offen zu lassen.

UND EIN FUENFTER TEXT, DEN NOCH NIEMAND GESEHEN HAT
---------------------------------------------------
Dieser Abschnitt musste in CLAUDE.md schon von drei auf vier Gruende wachsen
und dann noch einmal um die Statustabelle. Ein Codex-Kommentar, der in keine
Schublade passt, wird deshalb `unknown` und WOERTLICH zitiert, statt in die
naechstbeste gezwungen zu werden. Ein Gate, das einen unbekannten Text als
«kein Befund» liest, ist schlimmer als keines.

DIE STATUSTABELLE IST DAS URTEIL — GEMESSEN, NICHT ANGENOMMEN
-------------------------------------------------------------
Codex setzt beim Ausloesen einen Kommentar mit dem HTML-Marker
`codex-pull-request-review-summary` und schreibt ihn in Ort fort — gleiche
Kommentar-ID, `created_at` unveraendert, `updated_at` wandert:

    | 📝 **Code Review** | ✅ **Completed** <relative-time ...> | `b503b48` | ... |

Auf #56 bis #61 dieses Repos war diese Tabelle das EINZIGE Artefakt: kein
Review-Objekt (`get_reviews` → `[]`), keine Review-Threads, keine
Befundlos-Meldung, keine Reaktion. Ein Gate, das nur auf einen eigenen
Kommentar wartet, blockierte jeden sauberen PR bis in den Timeout und meldete
ihn dann rot.

Deshalb wird die Tabelle gelesen, und zwar VOR den Einzelkommentaren:

  Completed zum Head  → der Lauf ist zu Ende.
  Running zum Head    → laeuft noch, weiterwarten.
  anderer Status      → `unknown`, woertlich zitiert.

Gebunden wird ueber die Commit-Spalte, nicht ueber den Zeitstempel: Die
Tabelle wird fortgeschrieben, ihr `created_at` ist deshalb aelter als die
Aussage, die sie heute trifft.

WAS `clear` HEISST UND WAS NICHT — DIE OFFENE KONTROLLE
--------------------------------------------------------
`✅ Completed` heisst «Lauf zu Ende», nicht «nichts gefunden». Dass ein
abgeschlossener Lauf ohne Review-Objekt Befundlosigkeit bedeutet, ist die
naheliegende Lesart und in diesem Repo NICHT gegenprobiert: Alle sechs
Beobachtungen (#56 bis #61) fielen auf PRs, die zum Zeitpunkt des Laufs schon
gemergt waren. Ob ein Befund auf einem gemergten PR ueberhaupt noch
geschrieben wird, ist damit offen — sechsmal dasselbe unter denselben
Bedingungen zu sehen ist keine Gegenprobe, sondern dieselbe Messung sechsmal.

Die fehlende Kontrolle ist ein `Completed` auf einem PR, der beim Lauf noch
OFFEN war. Genau die liefert dieses Gate nebenbei, weil es als PR-Check
laeuft, solange der PR offen ist. Bis sie vorliegt, behauptet `clear`
vorsichtshalber nur das Gemessene: Codex hat diesen Commit angesehen und
nichts hinterlassen.

Aufruf:
    python scripts/classify_codex_review.py --head-sha <sha> \
        --reviews reviews.json --comments comments.json --since <ISO-8601>
"""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

CODEX_LOGIN = "chatgpt-codex-connector[bot]"

# Der HTML-Marker der Statustabelle. Woertlich aus den aufgezeichneten
# Kommentaren auf PR #56 und #61 dieses Repos, nicht nachgebaut.
STATUS_MARKER = "codex-pull-request-review-summary"

REVIEWED = "reviewed"
CLEAR = "clear"
QUOTA = "quota"
ENVIRONMENT = "environment"
UNKNOWN = "unknown"
PENDING = "pending"
#: Die Statustabelle nennt zum Head einen Lauf, der noch nicht fertig ist.
#: Von PENDING getrennt, weil beides «noch nichts» heisst und Verschiedenes
#: bedeutet: Bei RUNNING ist ein Urteil unterwegs und Warten lohnt; bei
#: PENDING ist nichts in der Luft, und Warten kostet nur Laufzeit. Am
#: 19.09.2026 auf PR #64 fiel der Unterschied auf, als der Gate-Job seine
#: kurze Frist ausschoepfte, waehrend ein Lauf noch arbeitete.
RUNNING = "running"

#: Zustaende, die den PR freigeben.
#:
#: NUR `clear`. `reviewed` belegt zwar ebenfalls, dass Codex hingesehen hat —
#: aber mit Befunden, und die gehoeren behoben, bevor gemergt wird. Bis zum
#: 19.09.2026 stand `REVIEWED` hier mit drin; dann ging auf PR #64 ein Lauf
#: mit zwei P1-Befunden gruen durch. Das Gate meldete korrekt «angesehen» und
#: liess genau das passieren, wogegen es gebaut ist.
#:
#: Der Preis ist benannt: Jede Befundrunde braucht einen weiteren Codex-Lauf,
#: und frei wird der PR erst, wenn einer nichts mehr findet.
PROVEN = frozenset({CLEAR})

# Nur der stabile Teil der Befundlos-Meldung. Der Schlusssatz wechselt bei
# jedem Lauf («Swish!», «Delightful!», «Keep it up!»), der Satz davor nicht.
# Ohne Apostroph gematcht, weil «Didn't» je nach Zeichensatz ' oder ’ traegt.
_CLEAR_MARKERS = ("find any major issues",)
_QUOTA_MARKERS = ("reached your codex usage limits",)
_ENVIRONMENT_MARKERS = ("create an environment for this repo",)


def _codex_authored(item: dict[str, Any]) -> bool:
    user = item.get("user") or {}
    return str(user.get("login", "")) == CODEX_LOGIN


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


# Eine Commit-Spalte traegt einen abgekuerzten SHA in Backticks. Kopf- und
# Trennzeile der Tabelle fallen an dieser Pruefung heraus, ohne dass jemand
# sie zaehlen muss — «Commit» und «---» sind keine Hex-Ziffern.
_KURZ_SHA = re.compile(r"^[0-9a-f]{7,40}$")


def _statuszeilen(body: str) -> list[tuple[str, str]]:
    """(Status, Kurz-SHA) je Datenzeile der Codex-Statustabelle."""
    zeilen: list[tuple[str, str]] = []
    for roh in body.splitlines():
        zeile = roh.strip()
        if not zeile.startswith("|"):
            continue
        zellen = [z.strip() for z in zeile.strip("|").split("|")]
        if len(zellen) < 3:
            continue
        commit = zellen[2].strip("`").strip()
        if not _KURZ_SHA.match(commit):
            continue
        zeilen.append((zellen[1], commit))
    return zeilen


def classify(
    reviews: list[dict[str, Any]],
    comments: list[dict[str, Any]],
    head_sha: str,
    since: str | None = None,
) -> tuple[str, str]:
    """(state, reason) aus Reviews und Kommentaren eines PR.

    Zwei verschiedene Abfragen, und beide werden gebraucht: Das Review-Objekt
    kommt aus `pulls/{n}/reviews`, Statustabelle und Meldungstexte aus
    `issues/{n}/comments`. Wer nur eine nimmt, uebersieht den Rest — genau so
    ist die Kontingent-Meldung am 21.8.2026 zuerst durchgerutscht.

    Reihenfolge: Review-Objekt, dann Statustabelle, dann Einzelkommentare.
    Jede Stufe bindet an den Head — das Objekt ueber `commit_id`, die Tabelle
    ueber ihre Commit-Spalte, die Kommentare ueber `since`. Ein Urteil zu
    einem frueheren Commit belegt nichts ueber den, der gemergt wird.
    """
    grenze = _parse_iso(since)
    kurz = head_sha[:7] if head_sha else ""

    for review in reviews:
        if not _codex_authored(review):
            continue
        if head_sha and str(review.get("commit_id", "")) != head_sha:
            continue
        return (
            REVIEWED,
            f"Codex-Review-Objekt zu {kurz}: Es liegen Befunde vor. Beheben "
            "oder beantworten und pushen — das Gate wird erst gruen, wenn ein "
            "Lauf zum dann aktuellen Head nichts mehr findet.",
        )

    laeuft = False
    fertig = False
    fremder_status: str | None = None
    for comment in comments:
        if not _codex_authored(comment) or STATUS_MARKER not in str(comment.get("body", "")):
            continue
        for status, commit in _statuszeilen(str(comment.get("body", ""))):
            if head_sha and not head_sha.startswith(commit):
                continue
            gesenkt = status.lower()
            if "running" in gesenkt or "queued" in gesenkt or "in progress" in gesenkt:
                laeuft = True
            elif "completed" in gesenkt:
                fertig = True
            elif fremder_status is None:
                fremder_status = " ".join(status.split())[:200]

    if fremder_status is not None:
        return (
            UNKNOWN,
            f"Die Codex-Statustabelle fuehrt zu {kurz} einen unbekannten Status. "
            f"Woertlich: «{fremder_status}» — einordnen statt durchwinken.",
        )
    if laeuft:
        return RUNNING, f"Codex-Review zu {kurz} laeuft noch."
    if fertig:
        return (
            CLEAR,
            f"Codex hat den Lauf zu {kurz} abgeschlossen und weder ein "
            "Review-Objekt noch eine Meldung hinterlassen. Das belegt die "
            "Pruefung; dass es keine Befunde gab, ist die naheliegende "
            "Lesart und nicht gegenprobiert.",
        )

    unbekannt: list[str] = []
    for comment in comments:
        if not _codex_authored(comment):
            continue
        body = str(comment.get("body", ""))
        if STATUS_MARKER in body:
            continue  # oben schon gelesen; hier waere sie ein «fremder Text».
        erstellt = _parse_iso(comment.get("created_at"))
        if grenze is not None and erstellt is not None and erstellt < grenze:
            continue
        gesenkt = body.lower()
        if any(m in gesenkt for m in _CLEAR_MARKERS):
            return CLEAR, "Codex meldet keine Befunde zu diesem Commit."
        if any(m in gesenkt for m in _QUOTA_MARKERS):
            return (
                QUOTA,
                "Codex-Kontingent fuer Code-Reviews ist aufgebraucht. Das ist "
                "KEIN Freispruch: Es wurde nichts geprueft. Kontingent haengt "
                "am Konto, nicht am Repo.",
            )
        if any(m in gesenkt for m in _ENVIRONMENT_MARKERS):
            return (
                ENVIRONMENT,
                "Fuer dieses Repo fehlt eine Codex-Environment, und die "
                "Statustabelle nennt keinen Lauf zu diesem Commit. Sie wird je "
                "Repo angelegt (chatgpt.com/codex/cloud/settings/environments); "
                "eine fuers Konto genuegt nicht.",
            )
        unbekannt.append(" ".join(body.split())[:300])

    if unbekannt:
        return (
            UNKNOWN,
            "Codex hat etwas geschrieben, das in keinen der bekannten Faelle "
            f"passt. Woertlich: «{unbekannt[0]}» — einordnen und die Marker in "
            "scripts/classify_codex_review.py ergaenzen, statt es als «kein "
            "Befund» durchzuwinken.",
        )
    return PENDING, f"Noch kein Codex-Urteil zu {kurz or '?'}."


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="classify_codex_review")
    ap.add_argument("--head-sha", default="", help="Head-Commit des PR")
    ap.add_argument("--reviews", type=Path, required=True, help="JSON aus pulls/{n}/reviews")
    ap.add_argument("--comments", type=Path, required=True, help="JSON aus issues/{n}/comments")
    ap.add_argument(
        "--since",
        default=None,
        help="ISO-8601; aeltere Kommentare zaehlen nicht als Urteil zu diesem Head.",
    )
    args = ap.parse_args(argv)

    def load(path: Path) -> list[dict[str, Any]]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        return data if isinstance(data, list) else []

    state, reason = classify(load(args.reviews), load(args.comments), args.head_sha, args.since)
    print(f"state={state}")
    print(f"reason={reason}")
    print(f"proven={'true' if state in PROVEN else 'false'}")

    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        # Zeilenumbruch raus: Die `key=value`-Form endet an der ersten neuen
        # Zeile, und ein zitierter Fremdtext koennte sonst ein eigenes
        # `state=clear` nachschieben und das rote Gate gruen faerben.
        flat = " ".join(reason.split())
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"state={state}\n")
            fh.write(f"reason={flat}\n")
            fh.write(f"proven={'true' if state in PROVEN else 'false'}\n")
    # Immer 0: Ueber rot oder gruen entscheidet der Workflow.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
