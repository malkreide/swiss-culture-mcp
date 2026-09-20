"""Dockerfile und `.dockerignore` gegeneinander gehalten (C2).

Keine dieser Zusicherungen baut ein Image — ein Docker-Daemon steht in der CI
nicht zur Verfuegung. Geprueft wird deshalb die Stelle, an der ein Build
scheitern WUERDE, und zwar dort, wo die beiden Dateien sich widersprechen
koennen: Der Dockerfile kopiert vier Dinge, die `.dockerignore` ausschliessen
kann, ohne dass es beim Schreiben auffaellt.

Das ist die schwaechere Form von Beleg, und sie steht hier benannt statt
verschwiegen: Ein gruener Lauf heisst «die beiden Dateien widersprechen sich
nicht», nicht «das Image baut».
"""

from __future__ import annotations

import pathlib
import re

import pytest

WURZEL = pathlib.Path(__file__).resolve().parent.parent
DOCKERFILE = (WURZEL / "Dockerfile").read_text(encoding="utf-8")
DOCKERIGNORE_TEXT = (WURZEL / ".dockerignore").read_text(encoding="utf-8")


def _muster() -> list[str]:
    """Die wirksamen Zeilen der `.dockerignore`, ohne Kommentare und Leerzeilen."""
    return [
        z.strip()
        for z in DOCKERIGNORE_TEXT.splitlines()
        if z.strip() and not z.lstrip().startswith("#")
    ]


def _kopierte_pfade() -> list[str]:
    """Was der Dockerfile aus dem Build-Kontext holt.

    Aus der Datei gelesen und nicht von Hand aufgezaehlt: Eine Liste im Test
    waere eine zweite Quelle, die beim naechsten `COPY` still veraltet — genau
    die Drift, gegen die dieses Modul geschrieben ist.
    """
    pfade: list[str] = []
    for zeile in DOCKERFILE.splitlines():
        treffer = re.match(r"^COPY\s+(?!--from)(.*)$", zeile.strip())
        if treffer:
            # Das letzte Feld ist das Ziel im Image, nicht die Quelle.
            pfade.extend(treffer.group(1).split()[:-1])
    return pfade


# ---------------------------------------------------------------------------
# `.dockerignore`
# ---------------------------------------------------------------------------


def test_die_dockerignore_existiert_und_ist_nicht_leer():
    assert _muster(), ".dockerignore enthaelt keine wirksame Zeile"


def test_der_build_kontext_traegt_die_historie_nicht_mit():
    """`.git` ist der teuerste Posten: Der ganze Kontext geht vor dem ersten
    Befehl an den Daemon, auch was kein `COPY` je anfasst."""
    assert ".git/" in _muster()


@pytest.mark.parametrize("pfad", ["tests/", "audits/", ".venv/", "__pycache__/", "dist/"])
def test_was_nicht_zur_laufzeit_gehoert_bleibt_draussen(pfad: str):
    assert pfad in _muster(), f"{pfad} fehlt in .dockerignore"


def test_der_dockerfile_kopiert_genau_die_erwarteten_vier_dinge():
    """Verankert die Liste unten. Kommt ein `COPY` hinzu, faellt diese Zeile —
    und mit ihr der Anlass, die Ausschluesse noch einmal anzusehen."""
    assert set(_kopierte_pfade()) == {"pyproject.toml", "README.md", "LICENSE", "src/"}


@pytest.mark.parametrize("pfad", ["pyproject.toml", "README.md", "LICENSE", "src/"])
def test_kein_kopierter_pfad_steht_in_der_dockerignore(pfad: str):
    """Der tragende Fall, und er ist im Portfolio schon eingetreten: `*.md`
    schliesst `README.md` mit aus, und der Build bricht im ersten `COPY` ab.
    Die Ausnahme `!README.md` haelt ihn drin.
    """
    muster = _muster()
    assert pfad not in muster, f"{pfad} wird vom Dockerfile kopiert, steht aber in .dockerignore"
    basis = pfad.rstrip("/")
    assert basis not in muster, f"{basis} wird vom Dockerfile kopiert, steht aber in .dockerignore"


def test_die_ausnahme_fuer_die_readme_steht_nach_dem_wildcard():
    """Die Reihenfolge ist tragend, nicht kosmetisch: Docker wertet die Muster
    der Reihe nach aus, und eine Ausnahme VOR dem `*.md`, das sie aufhebt,
    wirkt nicht. Ein Test, der nur das Vorkommen beider Zeilen prueft, bliebe
    bei vertauschter Reihenfolge gruen — und der Build faellt trotzdem.
    """
    muster = _muster()
    assert "*.md" in muster
    assert "!README.md" in muster
    assert muster.index("!README.md") > muster.index("*.md"), (
        "!README.md steht vor *.md und wird dadurch wirkungslos"
    )


# ---------------------------------------------------------------------------
# Dockerfile
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("variable", "wert"),
    [
        ("MCP_TRANSPORT", "streamable_http"),
        ("MCP_HOST", "0.0.0.0"),
        ("MCP_PORT", "8000"),
        ("MCP_ALLOW_PUBLIC_BIND", "true"),
    ],
)
def test_die_erwarteten_env_werte_stehen_im_image(variable: str, wert: str):
    assert f"{variable}={wert}" in DOCKERFILE


def test_der_transportname_im_image_waehlt_wirklich_den_http_transport():
    """Nicht das Literal gegen sich selbst, sondern gegen die Alias-Liste des
    Servers.

    Ein Tippfehler hier faellt sonst durch bis in den Betrieb: Ein Wert
    ausserhalb der Liste laesst `main()` auf stdio zurueckfallen, und das ist
    im Container ein Prozess, der startet, keinen Port oeffnet und erst am
    Healthcheck auffaellt. Eine Fehlkonfiguration soll nicht wie ein
    Deployment aussehen.
    """
    from swiss_culture_mcp.server import _HTTP_TRANSPORT_ALIASES

    treffer = re.search(r"MCP_TRANSPORT=(\S+)", DOCKERFILE)
    assert treffer, "MCP_TRANSPORT steht nicht im Dockerfile"
    assert treffer.group(1) in _HTTP_TRANSPORT_ALIASES


def test_der_container_startet_ueber_das_konsolenskript():
    """`python -m swiss_culture_mcp.server` laedt das Modul zweimal — einmal
    beim Paket-Import, dann als `__main__` — und hinterlaesst zwei
    `MCPServer`-Instanzen im Prozess."""
    assert 'CMD ["swiss-culture-mcp"]' in DOCKERFILE


def test_der_dockerfile_nennt_die_allowlist_variable():
    """C2: Die Variable muss dort dokumentiert sein, wo jemand das Image
    deployt. Sie bekommt bewusst KEINEN Wert — der Hostname haengt am
    Zielsystem, und ein geratener wiese jede echte Anfrage mit 421 ab.
    """
    assert "MCP_ALLOWED_HOSTS" in DOCKERFILE
    assert not re.search(r"^\s*MCP_ALLOWED_HOSTS=", DOCKERFILE, re.MULTILINE), (
        "MCP_ALLOWED_HOSTS ist im Image auf einen Wert gesetzt; der Hostname "
        "ist zur Bauzeit nicht bekannt"
    )


def test_der_container_laeuft_nicht_als_root():
    assert re.search(r"^USER\s+mcp\s*$", DOCKERFILE, re.MULTILINE)


def _healthcheck_befehl() -> str:
    """Die HEALTHCHECK-Anweisung samt ihrer Fortsetzungszeilen.

    Hier stand `DOCKERFILE.split("HEALTHCHECK", 1)[1]`, und die Gegenprobe vom
    20.9.2026 hat gezeigt, dass das nichts misst: Das Wort kommt im Kommentar
    ueber dem `ENV`-Block ebenfalls vor («so the HEALTHCHECK below keeps
    working»), also traf die Teilung dort — und der gemessene Bereich enthielt
    `MCP_PORT=8000` aus dem `ENV`. Die Mutation, die den Port im Healthcheck
    fest verdrahtete, ueberlebte deshalb.

    Der Fehler ist lehrreicher als der Test: Es war der Kommentar aus DIESEM
    Commit, der den Test derselben Aenderung entschaerft hat. Ein Muster, das
    auf ein Wort statt auf eine Anweisung zielt, trifft irgendwann Prosa.
    """
    zeilen = DOCKERFILE.splitlines()
    for i, zeile in enumerate(zeilen):
        if not zeile.startswith("HEALTHCHECK"):
            continue
        befehl = [zeile]
        while befehl[-1].rstrip().endswith("\\") and i + 1 < len(zeilen):
            i += 1
            befehl.append(zeilen[i])
        return "\n".join(befehl)
    raise AssertionError("keine HEALTHCHECK-Anweisung im Dockerfile")


def test_der_healthcheck_nutzt_denselben_port_wie_der_bind():
    """Sonst meldet ein gesunder Container dauerhaft «unhealthy» — und zwar
    nur dort, wo `MCP_PORT` vom Default abweicht, also erst im Betrieb."""
    assert "MCP_PORT" in _healthcheck_befehl()


def test_der_healthcheck_findet_die_anweisung_und_nicht_den_kommentar():
    """Gegenprobe zum Helfer selbst. Ohne sie faellt niemandem auf, wenn er
    wieder Prosa statt der Anweisung greift — der Test darueber bliebe gruen.
    """
    befehl = _healthcheck_befehl()
    assert befehl.startswith("HEALTHCHECK ")
    assert "CMD" in befehl
    assert "ENV" not in befehl, "der Helfer hat den ENV-Block eingefangen"
