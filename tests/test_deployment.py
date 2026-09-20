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


# ---------------------------------------------------------------------------
# Beide READMEs gegen den Quelltext
# ---------------------------------------------------------------------------

PAKET = WURZEL / "src" / "swiss_culture_mcp"
READMES = ("README.md", "README.de.md")


def _module() -> list[pathlib.Path]:
    """Alle Python-Module des Pakets.

    Hier stand eine feste Liste aus zwei Dateien — und das war genau der
    Fehler, gegen den dieses Modul geschrieben ist: eine zweite Wahrheitsquelle,
    die still veraltet. Ein `os.getenv` in `constants.py` oder in einem neuen
    Modul waere nicht gefunden worden, die Verankerung unten waere von den
    uebrigen Treffern gruen geblieben, und keine der beiden READMEs haette die
    neue Einstellung nennen muessen.

    Gefunden hat das ein Codex-Review am 20.9.2026 (PR #73, P2). Der Test war
    als Drift-Wache gedacht und trug die Drift in sich selbst.
    """
    return sorted(PAKET.rglob("*.py"))


def _gelesene_env_vars() -> set[str]:
    """Jede Umgebungsvariable, die der Server tatsaechlich liest.

    Aus dem Quelltext erhoben, nicht aufgezaehlt: Eine Aufzaehlung im Test
    waere eine zweite Quelle, die beim naechsten `os.getenv` still veraltet —
    und dann prueft dieses Modul die Vollstaendigkeit der Doku mit einer
    unvollstaendigen Liste.
    """
    namen: set[str] = set()
    for pfad in _module():
        namen |= set(re.findall(r'os\.getenv\(\s*"([A-Z_]+)"', pfad.read_text(encoding="utf-8")))
    return namen


def test_der_quelltext_liest_ueberhaupt_env_vars():
    """Verankert die Erhebung. Greift der Ausdruck oben eines Tages ins Leere,
    waeren alle Zusicherungen darunter leer und trotzdem gruen — die
    gefaehrlichste Form von bestanden."""
    assert len(_gelesene_env_vars()) >= 5


def test_die_erhebung_deckt_das_ganze_paket_ab():
    """Die Zusicherung, die den P2-Befund festhaelt.

    Ohne sie faellt ein `os.getenv` in einem bisher nicht erfassten Modul
    niemandem auf: Die Verankerung oben bliebe von den uebrigen Treffern gruen.
    Geprueft wird deshalb die MENGE der durchsuchten Dateien gegen alle Module
    des Pakets, nicht ihre Anzahl.
    """
    gefunden = {p.name for p in _module()}
    alle = {p.name for p in PAKET.rglob("*.py")}
    assert gefunden == alle, f"nicht durchsucht: {sorted(alle - gefunden)}"
    assert "constants.py" in gefunden, (
        "das Paket hat seine Module umbenannt — die Erhebung ist nachzupruefen"
    )


@pytest.mark.parametrize("readme", READMES)
def test_beide_readmes_dokumentieren_jede_gelesene_env_var(readme: str):
    """Im Portfolio sind EN und DE desselben Repos schon dreimal
    auseinandergelaufen, weil nur eine Fassung nachgezogen wurde. Geprueft wird
    jede Sprache einzeln, damit die Meldung sagt, WELCHE Fassung fehlt.

    Die Richtung ist Absicht: Eine Variable, die der Server liest und die
    Dokumentation verschweigt, ist eine Einstellung, von der der Betreiber
    nichts weiss — bei `MCP_ALLOWED_HOSTS` ist das der Unterschied zwischen
    geprueftem und ungeprueftem `Host`-Header.
    """
    text = (WURZEL / readme).read_text(encoding="utf-8")
    fehlend = sorted(name for name in _gelesene_env_vars() if name not in text)
    assert not fehlend, f"{readme} dokumentiert nicht: {', '.join(fehlend)}"


@pytest.mark.parametrize("readme", READMES)
def test_beide_readmes_nennen_den_connector_pfad(readme: str):
    """Die Connector-URL ist Host plus Transportpfad. Der Pfad `/mcp` ist der
    Default des SDK (`streamable_http_path`) und steht nirgends sonst im
    Projekt — wer ihn raet, traegt eine URL ein, die 404 liefert."""
    text = (WURZEL / readme).read_text(encoding="utf-8")
    assert "<host>/mcp" in text, f"{readme} nennt das Muster der Connector-URL nicht"


def _abschnitt(text: str, von: str, bis: str) -> str:
    """Der Textbereich zwischen zwei Markern, beide in EN und DE identisch."""
    beginn = text.index(von)
    return text[beginn : text.index(bis, beginn)]


@pytest.mark.parametrize("readme", READMES)
def test_die_render_anleitung_setzt_beide_variablen(readme: str):
    """Die Zusicherung zum P1-Befund aus dem Codex-Review (PR #73, 20.9.2026).

    Die READMEs bewerben ausdruecklich den Weg ueber claude.ai im Browser. Wer
    der Anleitung folgte, setzte `MCP_ALLOWED_HOSTS` und nichts weiter — und
    genau dann kommt ein Browser-Client nicht durch. Gemessen an diesem Server
    mit `MCP_ALLOWED_HOSTS=mcp.example.ch` und ungesetztem `ALLOWED_ORIGINS`:

        Origin: https://claude.ai   ->  403        (abgelehnter Origin)
        CORS-Preflight              ->  kein Access-Control-Allow-Origin

    Die `403` ist der Ort, an dem der Befund praeziser wurde als seine erste
    Fassung: Er nannte `421`, das ist der Code fuer einen abgelehnten `Host`.
    Ein abgelehnter `Origin` gibt `403`.

    **Diese Zeile umfasste zuerst Render-Liste UND Docker-Aufruf in einem
    Bereich.** Die Gegenprobe hat sie widerlegt: Faellt die Variable nur aus der
    Render-Liste, hielt der Docker-Aufruf im selben Bereich den Test gruen.
    Zwei Anleitungen brauchen zwei Zusicherungen — der Nachbartest unten sagt
    dasselbe ueber die andere Richtung, und beide zusammen sind erst der Beleg.
    """
    abschnitt = _abschnitt(
        (WURZEL / readme).read_text(encoding="utf-8"), "**Render.com", "**Docker.**"
    )
    for variable in ("MCP_ALLOWED_HOSTS", "ALLOWED_ORIGINS"):
        assert variable in abschnitt, f"{readme}: die Render-Anleitung setzt {variable} nicht"


@pytest.mark.parametrize("readme", READMES)
def test_der_docker_aufruf_setzt_beide_variablen(readme: str):
    """Die andere Haelfte. Render-Liste und `docker run` sind zwei getrennte
    Anleitungen; wer nur eine prueft, misst die andere nicht. Beide Zeilen
    zusammen fangen jede der zwei Richtungen einzeln — das war in der ersten
    Fassung nicht so, siehe den Docstring darueber.
    """
    aufruf = _abschnitt((WURZEL / readme).read_text(encoding="utf-8"), "docker run", "```")
    for variable in ("MCP_ALLOWED_HOSTS", "ALLOWED_ORIGINS"):
        assert variable in aufruf, f"{readme}: der docker-run-Aufruf setzt {variable} nicht"
