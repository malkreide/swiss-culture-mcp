# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Security

- **Host- und Origin-Pruefung fuer den HTTP-Transport** (SEC-005). `main()`
  startete den Streamable-HTTP-Transport ueber `mcp.run()`. Dieser Weg nimmt
  `transport_security` gar nicht entgegen, und ohne diesen Parameter leitet das
  SDK seine Allowlist allein aus dem Bind-Host ab. Am Draht gemessen,
  `transport_security=None`:

  ```
  host=127.0.0.1   fremder Host -> 421   127.0.0.1:9999 -> 200
  host=0.0.0.0     fremder Host -> 200   127.0.0.1:9999 -> 200
  ```

  Mit `MCP_HOST=0.0.0.0` — was das Container-Image setzt — wurde also weder
  `Host` noch `Origin` geprueft. Der Server stand damit offen fuer
  DNS-Rebinding: Ein Angreifer laesst den Browser des Opfers auf ihn zeigen und
  spricht ihn unter fremdem `Host` an.

  Der Befund lautete zuerst pauschal «ohne `transport_security` prueft das SDK
  nichts», gestuetzt auf den Kommentar im SDK-Quelltext. Die Gegenprobe hat das
  widerlegt, bevor die falsche Begruendung im Code stehenbleiben konnte: Bei
  einem Loopback-Bind installiert `streamable_http_app()` selbst
  `127.0.0.1:*` — mit **Port-Wildcard**. Der Befund traegt genau fuer
  `0.0.0.0`; die neue Liste ist portgenau und damit enger als die bisherige
  SDK-Vorgabe.

  Neu speist `MCP_ALLOWED_HOSTS` (kommagetrennt, ohne Schema) die Allowlist.
  Loopback bleibt immer erlaubt, sonst meldet der Healthcheck des Containers
  einen gesunden Server als krank. Bei einem Nicht-Loopback-Bind ohne Allowlist
  bleibt der Schutz aus und der Server protokolliert
  `dns_rebinding_protection_off` — eine geratene Liste wuerde jede echte
  Anfrage mit 421 abweisen, und diese Luecke ist als eigene Zusicherung
  festgehalten statt stillschweigend geschlossen.

  Die Sperre `MCP_ALLOW_PUBLIC_BIND` bleibt unveraendert.

### Hinzugefuegt

- **CORS mit ausdruecklicher Header-Allowlist** (SDK-004). `mcp.run()` serviert
  die ASGI-App ohne CORS; ein Browser-Client kann den Antwort-Header
  `Mcp-Session-Id` dann nicht lesen und verliert seine Sitzung — der Server
  antwortet korrekt, und der Client kommt trotzdem nicht weiter. Die App wird
  jetzt selbst gebaut (`build_http_app`, eigene `uvicorn.run`-Schleife in
  `_run_http`) und gibt den Header ueber `expose_headers` frei.

  Die Header-Liste ist ausdruecklich und kein `"*"`: Bei einem Wildcard
  schaltet Starlette auf `allow_all_headers` und spiegelt zurueck, was der
  Browser ankuendigt. Das ist nicht eine Allowlist, sondern ihr Fehlen — und es
  verdeckt jede Drift, weil ein Wildcard nicht falsch werden kann.
  `ALLOWED_ORIGINS` ist fail-closed: Ohne Angabe ist kein Browser-Origin
  zugelassen; stdio und Nicht-Browser-Clients sind nicht betroffen.

- **`.dockerignore`** (C2). Ein Dockerfile lag bereits vor, eine
  `.dockerignore` nicht. Ohne sie geht der gesamte Build-Kontext an den
  Daemon — `.git` samt Historie, `tests/`, `audits/`, `.venv/` mit
  Binaerdateien der Bauhost-Architektur — bei jedem Build, auch wenn kein
  `COPY` sie je anfasst.

  Zwei Zeilen darin sind tragend und einzeln zugesichert: die Ausnahme
  `!README.md` unter dem `*.md` (der Dockerfile kopiert `README.md`, ohne die
  Ausnahme bricht der Build im ersten `COPY`) und ihre **Reihenfolge** —
  Docker wertet die Muster der Reihe nach aus, eine Ausnahme vor dem Muster,
  das sie aufhebt, wirkt nicht.

- **Tests fuer das Deployment und die Server-Identitaet**:
  `tests/test_transport_security.py`, `tests/test_cors.py`,
  `tests/test_deployment.py`, `tests/test_servername.py`. Der Dockerfile hatte
  bisher keinen einzigen Test. Die Grenze von `test_deployment.py` steht im
  Modul-Docstring statt verschwiegen: Es baut kein Image (kein Docker-Daemon in
  der CI), es haelt nur Dockerfile und `.dockerignore` gegeneinander.

- **Drift-Wache fuer beide READMEs.** Jede Umgebungsvariable, die der Server
  tatsaechlich liest, muss in EN **und** DE dokumentiert sein; die Liste wird
  aus dem Quelltext erhoben statt im Test aufgezaehlt. Im Portfolio sind die
  beiden Sprachfassungen desselben Repos schon dreimal auseinandergelaufen,
  weil nur eine nachgezogen wurde. Geprueft wird jede Sprache einzeln, damit
  die Meldung sagt, welche Fassung fehlt.

  Die erste Fassung durchsuchte zwei fest benannte Dateien — also genau die
  zweite Wahrheitsquelle, gegen die diese Wache geschrieben ist. Ein
  `os.getenv` in `constants.py` waere nie gefunden worden, und die Verankerung
  waere von den uebrigen Treffern gruen geblieben. Gefunden hat das ein
  Codex-Review (P2); durchsucht wird jetzt das ganze Paket, und eine eigene
  Zusicherung haelt die Abdeckung fest.

- **`ALLOWED_ORIGINS` in den Deployment-Beispielen beider READMEs**, und je
  eine Zusicherung fuer die Render-Anleitung und den `docker run`-Aufruf. Die
  READMEs bewerben den Weg ueber claude.ai im Browser; wer der Anleitung
  folgte, setzte nur `MCP_ALLOWED_HOSTS` — und genau dann kommt ein
  Browser-Client nicht durch. Gemessen mit
  `MCP_ALLOWED_HOSTS=mcp.example.ch` und ungesetztem `ALLOWED_ORIGINS`:

  ```
  Origin: https://claude.ai   ->  403        (abgelehnter Origin)
  CORS-Preflight              ->  kein Access-Control-Allow-Origin
  ```

  Auch dieser Befund kam aus einem Codex-Review (P1). Die Messung hat ihn
  dabei praezisiert: Er nannte `421`, das ist der Code fuer einen abgelehnten
  `Host`; ein abgelehnter `Origin` gibt `403`.

### Geaendert

- **`serverInfo.name` heisst `swiss-culture-mcp`** (C3), mit Bindestrich wie
  Distribution, Konsolenskript, `server.json` und ausgehender `User-Agent`.
  Bisher stand dort `swiss_culture_mcp`; in der Aera `2026-07-28` steht dieser
  Name in **jeder** Antwort, nicht nur im Handshake. Wer den Server anhand
  seines `serverInfo.name` wiederzufinden versucht, suchte damit unter einem
  Namen, unter dem er nirgends sonst gefuehrt wird.

  Der Python-Logger behaelt den Unterstrich, und das steht als eigene Zeile da:
  Ein Logger-Name ist keine Server-Identitaet, ihn mitzuziehen braeche jede
  Logkonfiguration beim Betreiber. Eine Ausnahme, die man nicht aufschreibt,
  wird beim naechsten Aufraeumen zum Fehler.

- **`MCP_ALLOWED_HOSTS` im Dockerfile dokumentiert**, aber ausdruecklich ohne
  Wert: Der Hostname haengt am Zielsystem, ein geratener wiese jede echte
  Anfrage mit 421 ab. Beide READMEs fuehren die Variable, die Connector-URL
  `https://<host>/mcp` und den Docker-Aufruf.

### Anmerkung zur Gegenprobe

41 Mutationen einzeln gefahren, Bytecode-Cache je Lauf geleert, die Ankunft
jeder Mutation belegt. Vier davon haben Fehler in den **Tests** gezeigt, nicht
im Code — sie sind in den betroffenen Docstrings mit Datum festgehalten:

- «main() geht wieder ueber `mcp.run()`» lief in den Timeout, statt rot zu
  werden: `mcp.run` startete einen echten Server. Ein Lauf, der nicht endet,
  ist keine Messung.
- «Sperre gegen public bind entfaellt» liess
  `test_main_refuses_public_bind_without_override` **gruen**: Der echte
  `_run_http` lief, uvicorn scheiterte am belegten Port 8000 und beendete sich
  mit `sys.exit(1)`. Das erwartete `SystemExit` kam aus der Bindung statt aus
  der Sperre.
- «Healthcheck nimmt einen festen Port» ueberlebte, weil der Test den
  Dockerfile am ersten Vorkommen des Wortes `HEALTHCHECK` teilte — das seit
  derselben Aenderung im Kommentar ueber dem `ENV`-Block steht. Der Kommentar
  dieses Eintrags hat den Test desselben Eintrags entschaerft.
- «`ALLOWED_ORIGINS` fehlt nur in der Render-Liste» ueberlebte, weil die
  Zusicherung Render-Anleitung UND Docker-Aufruf in einem Bereich umfasste:
  Die Variable stand noch im Docker-Aufruf und hielt den Test gruen. Zwei
  Anleitungen brauchen zwei Zusicherungen. Bemerkenswert daran ist, dass der
  Docstring der Nachbarzeile vor genau diesem Fehler warnte — die Warnung war
  aufgeschrieben und trotzdem nicht befolgt.

## [1.2.0] - 2026-09-19

### Hinzugefuegt

- **Frischehinweise auf den auflistenden Methoden** (SEP-2549, Spec
  `2026-07-28`): `ttlMs` 300000, `cacheScope` `public`. Das SDK setzt beides von
  sich aus auf «sofort veraltet, nie geteilt» — wer nichts übergibt, lässt jeden
  Client bei jeder Verbindung neu auflisten, für Verzeichnisse, die per
  Dekorator beim Import feststehen und nicht vom Aufrufer abhängen.

  `resources/read` und `prompts/get` bleiben ohne Hinweis: das wäre eine
  Zusicherung über den Inhalt statt über das Verzeichnis. Ein Test hält das an
  der Antwort fest, ein zweiter an der Konfiguration.

- **Protokoll-Gate: beide Spec-Aeren gepinnt und geprueft**
  (`tests/test_protocol_version.py`). `mcp` 2.x bedient zwei Aeren ueber
  denselben Server — den `initialize`-Handshake, der bei `2025-11-25`
  deckelt, und den Pro-Request-Envelope, der `2026-07-28` erreicht.
  `LATEST_PROTOCOL_VERSION` ist ein Alias auf die **moderne** Aera; wer nur
  dagegen pinnt, laesst genau die Aera frei wandern, die heutige Clients
  aushandeln. Beide sind jetzt einzeln gepinnt, ein Dependabot-Bump von
  `mcp` kann keine davon still verschieben.

  Dieses Gate haengt an den SDK-Konstanten — die schwaechere Form, im Docstring
  benannt statt verschwiegen. Den gemessenen Teil liefert inzwischen
  `tests/test_modern_era.py` (siehe unten); die beiden Konstanten stehen weiter
  nur einmal da und werden von dort importiert.

  Beide READMEs beschreiben die Aeren; ein Test haelt jede Sprache einzeln
  dagegen — im Portfolio sind EN und DE desselben Repos schon dreimal
  auseinandergelaufen, weil nur eine Fassung nachgezogen wurde.

- **Spec `2026-07-28` am Draht gemessen** (`tests/test_modern_era.py`, 25
  Zusicherungen). Der Test baut die echte ASGI-App des Servers
  (`streamable_http_app()`), fährt ihren Lifespan und schickt Anfragen durch
  sie hindurch — den Pro-Request-Envelope der modernen Ära ebenso wie den
  `initialize`-Handshake.

  Warum nicht über einen In-Process-Client: Die moderne Ära existiert **nur**
  auf dem Streamable-HTTP-Einstieg. `StreamableHTTPSessionManager` routet einen
  Request, dessen `mcp-protocol-version`-Header keine Handshake-Revision nennt,
  auf den Pro-Request-Pfad; stdio und `Client(mcp)` kennen ausschliesslich den
  Handshake. Wer die Spec durch einen In-Process-Client prüft, prüft die
  Handler und nicht die Ära — und übersieht genau den Fehler unter «Behoben».

  Gemessen und nicht angenommen wurde auch, was eine moderne Anfrage
  mitbringen muss. `mcp-name` spiegelt je Methode ein anderes Feld (`name` bei
  `tools/call`, `uri` bei `resources/read`); die Zuordnung kommt aus
  `NAME_BEARING_METHODS` des SDK statt aus einer zweiten Tabelle. Ein
  unbekanntes Werkzeug antwortet `200` mit `isError: true` und nicht 4xx — ein
  fehlgeschlagener Werkzeugaufruf ist nach Spec ein Resultat, damit das Modell
  die Meldung sieht. Beide Erwartungen standen zuerst falsch im Test.

  Der Frischehinweis-Test parametrisiert über `CACHEABLE_METHODS` des SDK und
  NICHT über `CACHE_HINTS`. Die erste Fassung tat Letzteres, und die
  Gegenprobe zeigte, warum das zu wenig ist: einen Eintrag aus `CACHE_HINTS`
  zu löschen liess die Suite grün, weil mit dem Eintrag auch der Testfall
  verschwand. Ein Test, der über sein Prüfobjekt parametrisiert, kann dessen
  Entfernung nicht bemerken.

- **`serverInfo` trägt jetzt eine Identität.** Spec `2026-07-28` führt
  `serverInfo` im `_meta` **jeder** Antwort mit, nicht einmal pro Sitzung wie
  die Handshake-Ära. Am Draht gemessen stand dort — in `tools/list`,
  `resources/list`, `server/discover` und `tools/call` gleichermassen —
  `{"name": "swiss_culture_mcp", "version": ""}`. Was fehlte, fehlte also bei
  jedem Aufruf.

  Der leere String war kein unvermeidlicher SDK-Default: `MCPServer` nimmt
  `version=""` nur an, weil niemand etwas übergab. Der `User-Agent` gegenüber
  den Upstreams trug die Nummer die ganze Zeit korrekt, aus derselben
  `__version__` der Paket-Metadaten. Nur die MCP-Seite blieb blank. Ergänzt
  sind `version` (aus `importlib.metadata`, kein Literal —
  `scripts/check_version_sync.py` weist eines zurück), `title`, `description`
  und `website_url`. Beide Ären geben es jetzt aus.

  Die Projektadresse steht dafür als `PROJECT_URL` in `constants.py`, statt
  als Literal ein zweites Mal neben dem `User-Agent`.

- **Frischehinweis auch auf `prompts/list`** (SEP-2549). Die Liste ist hier
  permanent leer — dieser Server registriert keinen Prompt — und antwortete am
  Draht dennoch `ttlMs=0`, `cacheScope=private`: jeder Client fragt bei jeder
  Verbindung eine Liste neu ab, die garantiert leer zurückkommt. Dieselbe
  Verschwendung, gegen die der Eintrag oben argumentiert, unter derselben Regel
  («die auflistenden Methoden»).

- **`scripts/record_fixtures.py`, `tests/fixtures/` und `PROVENANCE.md`.**
  Dieser Server braucht keine Zugangsdaten — seine gesamte Adressliste ist
  pruefbar, und war es nie. Aufgezeichnet ist jetzt, ob jede Adresse, die er
  baut oder als Quelle ausgibt, etwas liefert.

  **Vier Kontrollen**: ein erfundener geo.admin.ch-Dienst (404), ein
  erfundener BAK-Pfad (404), eine erfundene News-Organisationsnummer (200,
  aber 367 B statt 344 962 B — die Nummer filtert also wirklich) und ein
  erfundener Tradition-Slug (404).

- **Ein Beinahe-Fehlbefund, mit aufgezeichnet.** `TRADITIONS_BASE` allein
  antwortet mit 404; dem Stamm fehlt ein `.html`. Daraus folgt **nichts**:
  Der Server ruft den Stamm nie allein auf, sondern nur
  `{TRADITIONS_BASE}/liste/liste.html` und
  `{TRADITIONS_BASE}/traditionen/<slug>.html` — beide antworten mit 200.

  Mein erster Abruf schlug fehl, weil ich einen Slug geraten hatte. Der
  Recorder zieht sie deshalb aus der Listenseite, statt sie sich auszudenken,
  und `tests/test_adressen.py` haelt den Fall fest.

- **`tests/test_adressen.py`** — 9 Tests, die **in** der CI laufen.
  Gegengeprueft mit einer Rueckmutation (toter Link zurueck in die Ausgabe):
  Die Suite wird rot.

- **Zwei Gates mehr in der CI.** `live-tests.yml` faehrt die Live-Suite
  woechentlich gegen die echten Quellen — `--run-live` ist dabei Pflicht, ohne
  die Option ueberspringt sich jeder Live-Test selbst und der Lauf endet gruen,
  ohne etwas abgefragt zu haben. `scripts/classify_live_run.py` ordnet das
  Ergebnis ein und oeffnet bzw. schliesst dazu ein `upstream`-Issue.
  `codex-gate.yml` macht das Codex-Urteil zu einem Check-Run; freigegeben wird
  nur ein Lauf, der **nichts** findet.

  Am Server aendert das nichts. Es steht hier, weil es aendert, was ein gruener
  Lauf behauptet: vorher «die Mocks stimmen».

### Geaendert

- **Lieferkette und Werkzeugversionen festgenagelt.** Alle GitHub Actions
  haengen an einem Commit-SHA statt an einem beweglichen Tag. `ruff==0.16.3`
  steht nur noch an einer Stelle, im dev-Extra von `pyproject.toml`;
  `scripts/check_ruff_pin.py` weist eine zweite Version in den Workflows
  zurueck, weil ein solcher Schritt nach dem Install laeuft und den Pin still
  ueberstimmt.

### Behoben

- **Der HTTP-Transport startete nie — und mit ihm nichts von Spec
  `2026-07-28`.** `main()` rief `mcp.run(transport="streamable_http")`, mit
  Unterstrich. `MCPServer.run()` prüft den Namen gegen ein `Literal` und nimmt
  nur `streamable-http` an; gemessen:

  ```
  ValueError: Unknown transport: streamable_http
  ```

  Die Folge reicht weiter als ein Transport: Die moderne Ära wird
  ausschliesslich über den Streamable-HTTP-Einstieg bedient, stdio kennt nur
  den `initialize`-Handshake. Ein Server, dessen HTTP-Transport beim Start
  abbricht, spricht die Spec also gar nicht — so vollständig die Handler und so
  korrekt die gepinnten Revisionen auch sein mögen.

  Warum es niemandem auffiel: `tests/test_server.py` patchte `mcp.run` und
  hielt den übergebenen String gegen eine handgeschriebene Erwartung —
  denselben Tippfehler. Ein Mock nimmt jeden Namen an. Dieselbe Klasse wie der
  handgeschriebene Stub, der denselben Feldnamen annahm wie der Code: Nichts
  ist rot, weil nichts geprüft wird, worauf es ankommt. Die Prüfung hängt jetzt
  am `Literal` des SDK, und `tests/test_modern_era.py` führt den Namen
  zusätzlich wirklich durch `mcp.run()`.

  `MCP_TRANSPORT=streamable_http` bleibt gültig: Beide READMEs dokumentieren
  die Schreibweise mit Unterstrich, und so steht sie in bestehenden
  Deployments. Angenommen werden beide, umbenannt wird nichts.

- **`bak_get_opendata` scheiterte produktiv an der eigenen Allowlist.**
  `opendata.swiss` beantwortet die CKAN-Aufrufe mit `302` auf
  `ckan.opendata.swiss`. `_assert_host_allowed()` prueft den Host **nach** der
  Umleitung, und das Ziel stand nicht in `ALLOWED_HOSTS` — jeder Aufruf endete
  in «Host nicht erlaubt», waehrend saemtliche Unit-Tests gruen blieben.

  Warum es monatelang unsichtbar war: Die aufgezeichnete Antwort hielt fuer
  diese Adresse `200` fest. Der Recorder folgte der Umleitung und schrieb den
  **Ausgangs**-Host auf — eine Aufzeichnung, die den Bruch, den sie sehen soll,
  gar nicht sehen kann. Sie fuehrt jetzt `final_host` mit, und
  `tests/test_umleitungsziele.py` prueft fuer jede abgerufene Adresse Start-
  und Zielhost gegen die Allowlist. Gefunden hat den Fehler der erste
  Live-Lauf, den es je gab.

- **Die ISOS-Zahlen zaehlten Features statt Ortsbilder.** `bak_isos_by_kanton`
  meldete fuer GR `total_in_kanton: 507`; Anhang 1 der VISOS (SR 451.12,
  Fassung vom 1.6.2026) setzt 105 fest. Der `find`-Endpunkt liefert je
  Ortsbild mehrere Features, und die Deduplizierung lief ueber die
  Feature-`id` — sie zaehlte Features und nannte sie Objekte.

  Fuer ZH kam dieselbe Zahl heraus wie richtig gerechnet (73), weil dort jedes
  Objekt genau eine Feature-ID traegt. Genau deshalb blieb es unentdeckt: Der
  Fall, an dem man es sieht, ist GR mit bis zu 51 IDs je Objekt. Betroffen
  waren vier Werkzeuge mit derselben kopierten Schleife (`bak_search_isos`,
  `bak_isos_by_kanton`, `bak_isos_by_kategorie`, `bak_isos_statistics`); alle
  vier laufen jetzt ueber `_dedup_objekte()`. Gegengeprueft gegen die
  Verordnung statt gegen die API: 1253 Ortsbilder, alle 26 Kantone nach der
  Korrektur deckungsgleich.

- **Eine ausgegebene Quelle war tot.** `bak_isos_overview` gab
  `https://www.bak.admin.ch/bak/de/home/kulturerbe/baukultur.html` als
  BAK-Website aus. Am 2026-08-08 gemessen: HTTP 404, Titel «404 - Seite nicht
  gefunden» — und nicht nur diese Seite, der ganze Zweig
  `.../home/kulturerbe.html` antwortet ebenfalls mit 404.

  Belegt mit einer Kontrolle: Ein frei erfundener Pfad unter demselben
  Praefix liefert denselben 404 mit demselben Titel und praktisch derselben
  Groesse (490 266 B gegen 490 250 B). Ohne sie hiesse der Befund nur «ich
  habe eine 404 bekommen».

  **Eine Ersatzadresse ist bewusst nicht geraten.** Die BAK-Navigation liegt
  hinter JavaScript, und die Wurzel verlinkt im Rohtext keine
  Baukultur-Seite. Ausgegeben wird jetzt die BAK-Wurzel, die nachweislich mit
  200 antwortet.


## [1.1.4] - 2026-07-30

> **Nachtrag vom 2026-09-19.** Dieser Abschnitt ist unvollstaendig und in einem
> Punkt irrefuehrend. `v1.1.4` enthaelt bereits die Migration auf die 2.x-API —
> `mcp.server.fastmcp` → `mcp.server.mcpserver`, `FastMCP` → `MCPServer`,
> Abhaengigkeit `mcp[cli]>=2.0.0,<3`. Der Satz unten, sie bleibe «eine eigene,
> bewusste Aufgabe», beschreibt einen Zwischenstand, der nie veroeffentlicht
> wurde: Auf PyPI traegt `1.1.4` `mcp[cli]<3,>=2.0.0`. Am Drahtformat aendert
> die Migration nichts, die Umbenennungen in `mcp_types` 2.x sind
> Pydantic-Aliasse.

### Behoben

- **User-Agent meldet wieder die tatsaechliche Paketversion.** Das auf PyPI
  veroeffentlichte `1.1.3` sendete gegenueber jedem Upstream
  `swiss-culture-mcp/1.0` — der Versionsstring war im Code hartkodiert und beim
  Bumpen liegengeblieben. Die Version kommt jetzt aus den Paket-Metadaten,
  kann also nicht mehr getrennt vom Paket driften.

- **`mcp` auf `<2` begrenzt.** `mcp` 2.0.0, veröffentlicht am 28.07.2026, hat
  `mcp.server.fastmcp` entfernt — genau das Modul, das dieser Server importiert.
  Mit dem bisherigen offenen `>=1.28.1` wählte jede frische Auflösung 2.0.0 und
  scheiterte beim Import mit `ModuleNotFoundError`, in der CI ebenso wie bei
  jedem `pip install`. In beide Richtungen verifiziert: 2.0.0 scheitert, `<2`
  löst auf 1.29.0 auf und importiert sauber. Die Migration auf die 2.x-API
  (`mcp.server.mcpserver`) bleibt eine eigene, bewusste Aufgabe.

## [1.1.0] - 2026-05-27

Security- und Observability-Hardening-Release nach dem Durchlauf des
[`mcp-audit-skill`](https://github.com/malkreide/mcp-audit-skill)-Katalogs
(68 Checks). Alle 8 in Run-1 gefundenen Befunde behoben (2 HIGH, 5 MEDIUM,
1 LOW) und durch 18 Regression-Tests abgesichert; Run-2 zeigt 0 offene
Findings. HTTP-Deployment-Pfad ist nicht mehr Production-blockiert.

### Security
- **SEC-003**: Streamable-HTTP-Transport bindet nun standardmässig auf `127.0.0.1`. Öffentliches Binding nur mit explizitem `MCP_HOST=0.0.0.0` + `MCP_ALLOW_PUBLIC_BIND=true` und dem dokumentierten Hinweis auf vorgelagerten Auth-Proxy.
- **SEC-004**: RSS-Parsing nutzt `defusedxml.ElementTree` statt `xml.etree.ElementTree` — schützt vor XXE und Billion-Laughs.
- **SEC-005**: `TraditionDetailInput.slug` validiert Pydantic-Regex `^[a-z0-9][a-z0-9\-]+$` (verhindert Pfad-Traversal). Zusätzlich Host-Allowlist (`_assert_host_allowed`) auf alle HTTP-Antworten — Open-Redirects auf nicht-erlaubte Hosts werden abgelehnt.
- **SEC-006**: `_handle_error` propagiert keinen Upstream-Response-Body mehr an den LLM. Volle Diagnose nur noch im Log.

### Performance
- **SCALE-001**: Modulweiter `httpx.AsyncClient` mit Connection-Pooling statt Client-Erstellung pro Request.
- **SCALE-002**: `bak_isos_statistics` führt die 7 Kanton-Abfragen jetzt parallel via `asyncio.gather` aus (~7× Speed-up).

### Added
- **OBS-001**: Strukturierte JSON-Logs auf stderr via `logging`-Stdlib. Log-Level via `LOG_LEVEL`-Env (Default `INFO`). Server-Start, Upstream-HTTP-Fehler, Timeouts, Connect-Errors und blockierte Hosts werden geloggt.
- **SEC-019**: HTML-Snapshots als versionierte Fixtures unter `tests/fixtures/` (`tradition_alphorn.html`, `tradition_list.html`) plus `TestHtmlFixtures`-Regression-Klasse — Frühwarnsystem für strukturelle Änderungen auf lebendige-traditionen.ch.
- Neue Env-Vars: `MCP_HOST`, `MCP_ALLOW_PUBLIC_BIND`, `LOG_LEVEL`.
- Neue Dependency: `defusedxml>=0.7.1`.
- 18 zusätzliche Tests (54 statt 36): Main-Hardening (4), Anti-Leak (1), Slug-Regex (4), Host-Allowlist (2), Defused-XML (1), Connection-Pool-Singleton (2), HTML-Fixture-Regressionen (4).

### Changed
- **ARCH-005**: `server.py` modularisiert (1337 → 1074 Zeilen, −20 %). Neue Module: `constants.py` (Konstanten und Referenzdaten), `http_client.py` (HTTP-Client, Logging, Host-Allowlist, Error-Handler), `models.py` (alle Pydantic-Input-Modelle). Öffentliche API über `server.py`-Re-Exports unverändert.
- **ARCH-008**: Lazy `import re` aus Tool-Funktionen entfernt; jetzt am Modulkopf.

### Migration

| Szenario | Aktion nötig |
|---|---|
| Claude Desktop / stdio | Keine — Default-Verhalten unverändert |
| HTTP-Deployment auf Render.com / Docker | Env-Vars setzen: `MCP_HOST=0.0.0.0` + `MCP_ALLOW_PUBLIC_BIND=true` (nur hinter Auth-Reverse-Proxy!) |
| pip/uvx | `uvx swiss-culture-mcp@1.1.0` oder `pip install -U swiss-culture-mcp` |

Vollständige Audit-Berichte unter `audits/2026-05-27-swiss-culture-mcp-rerun-2/audit-report.md` (Run-2).

## [1.0.0] - 2026-03-11

### Added
- 10 Tools für BAK-Kulturdaten (ISOS, Kulturpreise, Lebendige Traditionen, News, Open Data)
- 3 Resources: `bak://isos/kantone`, `bak://isos/kategorien`, `bak://kulturpreise/uebersicht`
- ISOS-Suche: `bak_search_isos`, `bak_isos_by_kanton`, `bak_get_isos_detail`, `bak_isos_by_kategorie`, `bak_isos_statistics`
- BAK-News und Preise: `bak_get_news`, `bak_get_kulturpreise`
- Open Data: `bak_get_opendata` (CKAN/opendata.swiss)
- Lebendige Traditionen: `bak_list_traditions`, `bak_get_tradition_detail`
- 36 Tests (Unit-Tests mit Mocks + 4 Live-Integrationstests)
- Dualer Transport: stdio (lokal) + Streamable HTTP (Cloud/Render.com)
- Bilinguales README (Deutsch primär, Englisch sekundär)
- Pydantic v2 Input-Validierung für alle Tools
- Einheitliche, handlungsorientierte Fehlermeldungen auf Deutsch
- Kantons-Validierung mit vollständiger Schweizer Kantonsliste (26 Kantone)
