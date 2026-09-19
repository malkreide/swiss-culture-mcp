# CLAUDE.md

## Vor der Arbeit

Klon-Aktualität prüfen — Standard-Branch ermitteln, nicht `main` annehmen:

```bash
B=$(git ls-remote --symref origin HEAD | sed -n 's|^ref: refs/heads/\([^[:space:]]*\).*|\1|p')
git fetch origin "${B:?Standard-Branch nicht ermittelbar}" &&
  git rev-list --count HEAD..FETCH_HEAD
```

Drei Server im Portfolio heissen ihren Standard-Branch `master`
(`openlex-mcp`, `swiss-courts-mcp`, `swisstopo-mcp`); dort scheitert ein fest
verdrahtetes `origin/main` mit «couldn't find remote ref main». Wer das für ein
Netzproblem hält, arbeitet weiter auf genau dem veralteten Klon, vor dem dieser
Absatz warnt. Den `:?`-Schutz nicht weglassen: Bei leerem `B` fetcht git still
den Remote-HEAD und endet mit 0.

Ein veralteter Klon erzeugt eine rote CI, deren Ursache nicht im Diff steht.
Am 3.8.2026 zweimal passiert — beide Male fehlten genau die Commits, die
das Gate einführten, an dem der Branch scheiterte.

Seit `.claude/settings.json` läuft diese Prüfung als SessionStart-Hook
(`.claude/hooks/session-start.sh`) und meldet den Rückstand von selbst. Sie
blockiert nie und schweigt bei 0 — bleibt oben also von Hand zu fahren, wenn
der Hook nicht greift (fremder Klon, kein Netz beim Start). Begründung und
Zusicherungen: `.claude/hooks/README.md`.

Gates lokal fahren, mit der GEPINNTEN ruff-Version aus der CI. Eine andere
Version meldet Abweichungen, die niemand verursacht hat.

## Tests

Gegenprobe ist Pflicht. Ein Test, der grün bleibt, wenn man die
Implementierung entfernt, prüft nichts. Jede neue Zusicherung einzeln
neutralisieren und zeigen, dass genau die zugehörigen Tests fallen.
Zwei Fallen, die beide grün blieben:
- Eine Fake-Uhr, die nur beim Schlafen vorrückt, kann eine Zusicherung über
echte Zeit nicht widerlegen.
- monkeypatch.setattr(modul.asyncio, "sleep", ...) greift ins Modul
asyncio selbst und entschärft die Mechanik im ganzen Prozess. Patche
einen Modul-Alias (_sleep = asyncio.sleep), nicht das fremde Modul.
Handgeschriebene Fixtures kodieren die Annahme des Autors und können sie
nicht widerlegen. Mindestens eine aufgezeichnete Antwort pro externem
Endpunkt, mit Aufnahmedatum.

## Wenn etwas rot ist

Roter Live-Test: erst die Quelle abfragen, dann einordnen. Nicht aus der
Fehlermeldung schliessen. Am 3.8.2026 hiess "nicht gefunden" nicht, dass der
Datensatz weg war, sondern dass die Quelle die Schreibweise ihrer Kopfzeile
gewechselt hatte — vier von sechs Datensätzen produktiv kaputt, alle
Unit-Tests grün.
PR ohne jeden Check ist selten ein Repo ohne CI, meistens ein
Merge-Konflikt: GitHub berechnet dafür keinen Merge-Commit und startet nichts.
Ein Codex-Review auf einem PR wird beantwortet oder behoben, nie ignoriert.

**Ein 4xx ist kein Nein.** Am 29.8.2026 antwortete `past-publications` in
`swiss-procurement-mcp` auf jede Publikation mit Losen mit HTTP 400. Daraus war
geschlossen worden, die Quelle verweigere diese Auskunft; der Befund stand
datiert im Fixture-Nachweis, ein Test bestätigte ihn, alles blieb grün. Die
Spec desselben Endpunkts führt einen als *optional* deklarierten Parameter
`lotId` — für Publikationen mit Losen ist er Pflicht. Mit ihm antwortet
dieselbe Publikation mit 200. Ein Projekt trug sieben Vorgängerpublikationen,
die der Server als «Quelle nicht erreichbar» wegwarf.

Drei Handgriffe daraus:

- **Die Parameterliste der Spec durchgehen, bevor ein Statuscode eingeordnet
  wird.** «Optional» heisst dort oft «optional für die Mehrheit».
- **Einer deterministischen Absage keinen Wiederholungsrat geben.** «Nicht
  erreichbar, bitte später erneut» ist bei einem 400 falsch und liest sich für
  das Modell wie eine Störung. Den Status mitführen und den fehlenden
  Parameter benennen — den Status, nicht den Antwortkörper.
- **Beide Antworten aufzeichnen, mit und ohne den Parameter.** Eine
  Aufzeichnung nur des Fehlschlags kann nicht zeigen, dass er vermeidbar war;
  dass nur der 400er aufgezeichnet war, ist der Grund, warum der falsche
  Befund nicht auffiel.

**Und ein 403 ist gar keine Auskunft.** Am 29.8.2026 sollten für 42 Repos die
Dependabot-Labels nachgemessen werden. Alle 13 Abfragen des ersten Stapels
kamen zurück als:

```
Failed to find label: API rate limit already exceeded for user ID 8864492.
```

Der gefährliche Teil steht vorn: Das Werkzeug verpackt eine Sperre als
Fund-Fehlschlag. Wer die Zeile überfliegt oder nur auf ein leeres Ergebnis
prüft, zählt 39 Repos als «Label fehlt» und hat seine eigene Erschöpfung
gemessen. Das Limit hängt am Konto, nicht am Repo — derselbe Vormittag hatte
es mit 42 eröffneten und 42 gemergten PRs verbraucht.

Das ist der Absatz darüber, andersherum gelesen: dort war ein 400 eine echte,
wiederholbare Antwort und galt als Störung; hier ist eine Störung als Antwort
verpackt. Entscheidend ist nie der Statuscode, sondern ob die Quelle überhaupt
geantwortet hat.

- **Positivkontrolle im selben Repo.** Ein «nicht gefunden» wird erst dadurch
  zur Messung, dass eine gleichzeitige Abfrage etwas findet.
- **Die Messung entlang der Sperre teilen.** `raw.githubusercontent.com` ist
  ein CDN und nicht die REST-API. Um 11:19:27 UTC lieferte es für
  `register-mcp` HTTP 200, während die Label-Abfrage desselben Repos in
  derselben Minute die Sperre meldete. Alle 42 `dependabot.yml` kamen so
  durch, während die Label-Hälfte stand.
- **Am Token vorbei geht es nicht.** Beide Umwege enden am Agent-Proxy, und
  jeder mit einer eigenen irreführenden Begründung. `api.github.com` ohne
  Zugangsdaten:

  ```
  GitHub access is not enabled for this session. An org admin must connect
  the Claude GitHub App for this organization.
  ```

  Das ist keine Aussage über die Organisation, sondern das, was ohne Token
  kommt. Wer ihr folgt, sucht einen Admin für ein Problem, das keiner hat.
  Die HTML-Seite `github.com/<owner>/<repo>/labels` fällt ebenfalls, aber
  anders:

  ```
  This GitHub API path is not available: sessions are bound to their
  configured repositories. Use repository-scoped endpoints
  (repos/{owner}/{repo}/...).
  ```

  Der Proxy behandelt also auch `github.com` als API-Pfad; die zweite Meldung
  klingt nach einem Scope-Problem und ist doch nur dieselbe Sackgasse. Den
  Token aus der Umgebung in einen curl-Header zu setzen, blockiert der
  Klassifikator. Ob es überhaupt hülfe, ist offen: die Sperre nennt ein
  Nutzerkonto, und ob der Token zu diesem gehört, wurde nie geprüft.
- **Die Sperre gilt nicht dem Dienst, sondern dem Zugangspfad.** Unmittelbar
  nachdem eine Abfrage der Checks eines PR sauber durchlief, meldete die
  Label-Abfrage weiter die Sperre. Von einem blockierten Werkzeug also nicht
  auf «GitHub ist zu» schliessen — und umgekehrt eine gelungene Abfrage nicht
  als Entwarnung für die gesperrte nehmen. Das ist dieselbe Asymmetrie wie
  bei der verschwundenen Codex-Meldung weiter unten.

Wann die Sperre fällt, geben diese Beobachtungen nicht her. Die Meldung nennt
keinen Zeitpunkt, und die `X-RateLimit`-Kopfzeilen sind hinter dem Proxy nicht
zu sehen. Belegt sind drei gesperrte Zeitpunkte — 11:14, 11:16 und 11:19 UTC.
Wer daraus eine Dauer macht, hat sie erfunden.

**Dieselbe Falle bei einer Konfigurationsoption: die Vorgabe lesen, bevor man
einen Schlüssel für wirkungslos hält.** Am 29.8.2026 fielen die
`labels:`-Zeilen aus den `dependabot.yml` des Portfolios, begründet mit
«Dependabot legt Labels nicht an». Eine Messung danach zeigte, dass
`dependencies` in 36 von 42 Repos sehr wohl existiert, 35 davon mit GitHubs
Standardbeschreibung. Das las sich zuerst wie ein Beleg, dass die Aktion
falsch war.

Die Optionsreferenz kehrt es um:

```
Dependabot creates these default labels automatically, as necessary in
your repository.

If you define more than one package manager, an additional label for the
ecosystem or language is added to each pull request.

The labels specified are used instead of the default labels.
```

Ohne `labels:` vergibt Dependabot also `dependencies` — und, sobald mehr als
ein Paketmanager deklariert ist, zusätzlich ein Ökosystem-Label — und legt sie
selbst an; eine eigene Liste **ersetzt** diesen Satz, und «if any of these
labels is not defined in the repository, it is ignored». Die Zeile war nicht
wirkungslos — sie tauschte einen sich selbst pflegenden Vorgabesatz gegen eine
starre Liste.

**Die Bedingung nicht weglassen.** Bei nur einem Paketmanager steht das
Ökosystem-Label gar nicht zu; wer es dort trotzdem erwartet, schreibt genau
den Fehlbefund auf, gegen den dieser Abschnitt geschrieben ist — der Abschnitt
liefe an sich selbst vorbei. Im Portfolio deklariert jede `dependabot.yml`
zwei (`pip` und `github-actions`), die Bedingung ist hier also überall
erfüllt; anderswo nicht unbedingt. Aufgefallen ist die fehlende Bedingung
nicht beim Schreiben, sondern durch einen Codex-Review auf
`swiss-environment-mcp` PR #113 — vierzehn Sekunden vor dem Merge desselben
PR.

Was das kostet, ist an `openlex-mcp` gemessen: zwei Ökosysteme deklariert,
also stünden `dependencies` **und** ein Ökosystem-Label zu; vorhanden ist nur
das erste, `github-actions` und `github_actions` fehlen beide (Kontrolle `bug`
vorhanden). `register-mcp` ist die Gegenprobe: dort existieren alle vier
deklarierten Namen mit handgeschriebener Beschreibung, die Liste ist gewollt
und vollständig.

**Dreimal falsch eingeordnet, in drei Richtungen.** Erst die Zeile für bloss
wirkungslos gehalten. Dann die gefundenen Labels für einen Widerspruch. Dann,
auf denselben Fund gestützt, einen richtigen PR geschlossen mit dem Argument,
das Label existiere ja — obwohl es existiert, *weil* die Vorgabe es anlegt.
Der dritte Fehler ist der teuerste, weil er wie eine Messung aussah.

Was die Messung **nicht** hergibt: wer die 36 Labels angelegt hat. Die
Referenz sagt, Dependabot tue es; die Objekt-IDs liegen aber so dicht
beieinander, dass sie eher aus einem Stapellauf stammen. Beides passt zum
Befund, keines ist belegt — die Herkunft blieb ungemessen.

Beim Aufräumen gilt deshalb dieselbe Frage wie bei `lotId`: Was ist die
*Vorgabe*, wenn man das Ding weglässt — nicht bloss, ob der aktuelle Wert
etwas bewirkt.

**`results[0]` ist nur so verlässlich wie die Zusicherung danach.** Pinnt die
Abfrage einen bekannten Datensatz, ist der erste Treffer eine Drift-Wache und
in Ordnung. Hängt die Zusicherung dagegen davon ab, *welche* Variante die
Quelle heute zuoberst hat, prüft der Test den Tag: am 25.8.2026 rot, weil die
neueste Zürcher Publikation zufällig Lose hatte, am 26.8. grün, ohne dass sich
etwas geändert hätte. Den Fall gezielt wählen und beide Zweige fahren.

## Wenn Codex gar nicht erst hinsieht

Die Zeile oben unterstellt, dass es einen Befund geben *kann*. Das ist nicht
immer so, und man sieht es dem PR nicht an.

Am 21.8.2026 war das Code-Review-Kontingent zwischen 08:41 und 09:48
aufgebraucht — davor echte Reviews, danach in 30 Repos nur noch:

```
You have reached your Codex usage limits for code reviews.
```

Wie lange die Sperre dauerte, geben die Beobachtungen nur als Spanne her. Vier
Zeitpunkte sind belegt: letzter gelungener Review am 21.8. um 08:41, erste
Limit-Meldung um 09:48, letzte beobachtete Limit-Meldung am 22.8. um 11:03,
erste *andere* Meldung am 23.8. um 08:22.

Zwischen erster und letzter Limit-Meldung liegen **25 h 15 min**. Das ist der
Abstand zweier Fehlschläge, nicht die Dauer einer Sperre. Wer ihn Untergrenze
nennt, hat die durchgehende Erschöpfung schon vorausgesetzt, die er belegen
soll: Öffnete sich das Fenster zwischendurch und schloss es sich durch neue
Auslöser wieder, waren es zwei kurze Sperren und nie eine von 25 Stunden.
Untergrenze einer *einzelnen* Sperre sind die 25 h 15 min nur unter genau dieser
Annahme — und die ist unbelegt.

Nach oben trägt die Rechnung dagegen. Die längste mit den Beobachtungen
verträgliche Sperre reicht vom letzten Erfolg um 08:41 bis zur abweichenden
Meldung um 08:22, also **47 h 41 min**; länger kann keine einzelne gewesen sein.
Wer stattdessen ab der ersten Limit-Meldung rechnet, unterschlägt die 67
Minuten, in denen das Kontingent schon weg gewesen sein kann, und nennt die
Spanne zwischen zwei Beobachtungen eine Obergrenze.

Beobachtungspunkte sind keine Messreihe — die 21 Stunden vor der abweichenden
Meldung liefen ganz ohne Codex-Auslöser, dort hat niemand gemessen.

In der Zwischenzeit sind 32 PRs mit formal erfülltem Häkchen gemergt worden,
ohne dass jemand hineingesehen hat, und am 22.8. noch einmal 43.

**Vier** Gründe, warum Codex schweigt, und nur einer davon ist harmlos:

- **Kein Befund** — dann schreibt er einen gewöhnlichen Issue-Kommentar:

  ```
  Codex Review: Didn't find any major issues. Swish!
  ```

  Der Schlusssatz wechselt bei jedem Lauf («Delightful!», «Keep it up!»,
  «More of your lovely PRs please.»); stabil ist nur der Satz davor. Der
  Infokasten, den Codex unter jeden Review setzt, behauptet weiterhin eine
  Reaktion («otherwise it will react with 👍») — am 23.8. kam in sechs Repos
  die Meldung und in keinem die Reaktion. Der Kasten ist keine Quelle.
- **Der PR ist ein Draft** — dann kommt manchmal nichts und manchmal die
  Environment-Meldung. Beides am 19.9.2026 in diesem Repo beobachtet, siehe
  unten.
- **Das Kontingent ist weg** — dann schreibt er die Meldung oben.
- **Für das Repo fehlt eine Environment** — dann schreibt er:

  ```
  To use Codex here, create an environment for this repo.
  ```

Der vierte kam erst zum Vorschein, als der dritte wegfiel, und das ist kein
Zufall: Die Prüfungen liegen hintereinander. Dass es diese Reihenfolge ist und
nicht die umgekehrte, lässt sich an einem einzigen Repo ablesen — in
`swiss-public-data-mcp` bekam PR #54 am 22.8. um 10:56:55 die Kontingent-Meldung
und PR #56 am 23.8. um 08:22:20 die Environment-Meldung. Läge die
Environment-Prüfung vorn, hätte #54 sie schon am Vortag gesehen; die Environment
fehlte ja bereits. Zwei Meldungen aus demselben Repo schlagen hier jede
Vermutung über die Reihenfolge.

Praktisch heisst das: **Eine verschwundene Limit-Meldung ist keine Entwarnung.**
Sie kann bedeuten, dass das Kontingent wieder da ist — und dass jetzt etwas
anderes den Review verhindert. Belegt ist eine Prüfung erst durch ein
Review-Objekt **oder** eine Befundlos-Meldung. Wer nur das Objekt gelten lässt,
zählt jeden befundlosen Review als ungeprüft — und baut sich denselben Fehlalarm
ein, den dieser Abschnitt verhindern soll, nur in die andere Richtung.

«Kein Kommentar» heisst also nicht «geprüft und sauber». Unterscheiden lässt es
sich an der Form: Ein Review **mit** Befund ist ein Review-Objekt
(«💡 Codex Review», mit Commit-Angabe); ein Review **ohne** Befund, die beiden
Ausfallmeldungen — Kontingent wie Environment — und die Laufstatus-Tabelle
weiter unten sind gewöhnliche Issue-Kommentare und trennen sich nur im Text.
Ein kommentarloser Draft ist kein Beleg, sondern ein nicht durchgeführter
Test. Am 19.9.2026 so beobachtet: PR #56 trug als Draft über Stunden null
Kommentare, und der erste erschien auf die Sekunde mit dem Umschalten auf
ready.

**Hier stand «Beim Draft gibt es überhaupt nichts, weil Codex nicht anläuft».
Das ist widerlegt, gemessen in diesem Repo am selben Tag.** PR #62 wurde um
09:05:5x als Draft angelegt; um **09:06:06**, also rund dreissig Sekunden
später, stand die Environment-Meldung darunter. Codex läuft also auf einem
Draft sehr wohl an — jedenfalls weit genug, um zu antworten.

Und die Antwort ist die zweite Widerlegung: **Die Environment-Meldung belegt
nicht, dass eine Environment fehlt.** 85 Minuten vorher, um 07:41, war auf
PR #61 desselben Repos ein regulärer Review durchgelaufen, Statustabelle samt
Infokasten «Your team has set up Codex to review pull requests in this repo».

Zwei Erklärungen passten auf beide Beobachtungen. **Die Messung hat neun
Minuten später entschieden:** Um 09:15:06 wurde derselbe PR #62 auf ready
geschaltet, um 09:15:12 setzte Codex eine reguläre Statustabelle auf
`f09a9e0` — samt Infokasten «Your team has set up Codex to review pull
requests in this repo», und um 09:16:08 stand sie auf `✅ Completed`.

**Die Environment ist da. Die Meldung auf dem Draft war Draft-Verhalten.**
Derselbe PR, dieselbe Minute des Tages, zwei gegensätzliche Auskünfte —
getrennt nur durch das Umschalten von Draft auf ready.

Daraus die Regel: **Auf einem Draft ist die Environment-Meldung keine
Auskunft über das Repo.** Wer sie dort liest und eine Environment anlegt,
behebt ein Problem, das keines ist — dieselbe Klasse wie der Admin, den
niemand braucht, im Abschnitt «Ein 403 ist gar keine Auskunft». Auf einem
ready-PR gilt sie weiterhin.

Fürs Gate ist der Fall damit doppelt entschärft: Der Job läuft auf Drafts gar
nicht (`if: draft == false`), und der `since`-Filter hätte den Kommentar von
09:06 ohnehin verworfen — er liegt vor dem Committer-Datum des Head-Commits.

Fürs Gate ist der Fall schon entschieden, und zwar richtig herum: Der
Klassifizierer liest die Statustabelle **vor** den Meldungstexten. Eine
`Completed`-Zeile zum Head schlägt eine Environment-Meldung; fehlt sie, gilt
die Meldung und der Job wird rot. `test_eine_fertige_tabelle_schlaegt_eine_environment_meldung`
hält beide Richtungen fest, seit dem 19.9.2026 mit dem hier aufgezeichneten
Wortlaut aus PR #62.

Das sind verschiedene Abfragen — `get_reviews` fürs Objekt, `get_comments` für
alles andere; wer nur eine nimmt, übersieht den Rest. Genau so ist die
Limit-Meldung zuerst durchgerutscht.

Der Kommentarzähler allein reicht ohnehin nicht: `comments: 1` kann die
Befundlos-, die Kontingent-, die Environment- **oder** die Laufstatus-Meldung
sein — vier gegensätzliche Bedeutungen unter derselben Zahl. Den Text lesen,
nicht die Zahl. Und einen unbekannten fünften Text wörtlich zitieren, statt ihn
in eine der bekannten Schubladen zu zwingen: Dieser Abschnitt musste schon
zweimal wachsen — von drei auf vier Gründe, dann um die Form unten — und die
👍-Reaktion stand hier zwei Fassungen lang als Tatsache.

**Die vierte Bedeutung: «läuft noch».** Am 19.9.2026 in diesem Repo beobachtet.
Codex setzt beim Auslösen einen Issue-Kommentar mit dem HTML-Marker
`<!-- codex-pull-request-review-summary -->`, der eine Tabelle trägt:

```
## Codex Review Summary
| Review | Status | Commit | Review trigger |
| 📝 Code Review | 🔄 Running since 2026-09-19T06:35:59Z | b503b48 | Draft marked ready |
```

Das ist keine der drei Meldungen oben. Es ist eine Aussage über den Lauf, nicht
über den Befund, und es kommt **vor** dem Ergebnis. Ein `comments: 1` kann also
heissen, dass gerade noch geprüft wird — wer die Zahl als Beleg nimmt, zählt
einen laufenden Review als abgeschlossenen. In derselben Antwort stand
`reactions.total_count: 0`, während der Infokasten eine 👀-Reaktion während des
Laufs behauptet. Der Kasten bleibt keine Quelle.

Der Marker ist der verlässliche Teil, nicht die Überschrift: Er steht im
Rohtext des Kommentarkörpers und trennt diese Form von jedem anderen Text,
ohne dass man auf Emoji oder Wortlaut angewiesen wäre.

**Der Endzustand steht in DEMSELBEN Kommentar — er wird bearbeitet, nicht
ergänzt.** Um 06:38:03 las dieselbe Tabelle:

```
| 📝 Code Review | ✅ Completed 2026-09-19T06:38:03Z | b503b48 | Draft marked ready |
```

Gleiche Kommentar-ID, `created_at` unverändert 06:36:00, `updated_at` auf
06:38:04 gewandert. Daraus zwei Handgriffe:

- **Den Kommentarkörper neu holen, nicht erinnern.** Wer ihn einmal gelesen und
  behalten hat, hält einen fertigen Lauf für einen laufenden — der Text unter
  derselben ID ist inzwischen ein anderer.
- **Der Zähler bewegt sich über den ganzen Lebenszyklus nicht.** `comments: 1`
  beim Start, `comments: 1` am Ende. Was oben über die Zahl steht, gilt hier
  also nicht bloss abgeschwächt, sondern ganz: Sie kann den Unterschied
  zwischen «läuft» und «fertig» gar nicht anzeigen.

**`✅ Completed` heisst «Lauf zu Ende», nicht «nichts gefunden».** Die
Unterscheidung ist nicht zu ersparen. In beiden Beobachtungen — PR #56 und
PR #57 desselben Tages — kamen kein Review-Objekt (`get_reviews` → `[]`),
keine Review-Threads (`get_review_comments` → `totalCount: 0`), keine
Befundlos-Meldung und keine Reaktion (`reactions.total_count: 0`); der Status
in der Tabelle war jedes Mal das einzige Artefakt. Das sieht nach «sauber» aus
und belegt es nicht: **Beide PRs waren zum Zeitpunkt des Laufs schon gemergt**,
und ob ein Befund auf einem gemergten PR überhaupt noch irgendwohin
geschrieben wird, ist damit weiterhin nicht geprüft. Die oben dokumentierte
«Swish!»-Meldung blieb beide Male aus — ob Codex das Format gewechselt hat oder
der Merge den Weg abschnitt, entscheiden zwei gleichartige Beobachtungen so
wenig wie eine.

Dass es inzwischen **sieben** sind — #56 bis #62 —, macht die Sache nicht
sicherer, sondern nur die Lücke sichtbarer: Siebenmal dasselbe unter denselben
Bedingungen zu sehen ist keine Gegenprobe, sondern dieselbe Messung siebenmal.
**Die fehlende Kontrolle ist ein `Completed` auf einem PR, der beim Lauf noch
OFFEN war** — die gibt es bis heute nicht. Solange sie fehlt, gilt unverändert,
was oben steht: Belegt ist eine Prüfung durch ein Review-Objekt oder eine
Befundlos-Meldung, nicht durch den Status in der Tabelle.

Warum sie fehlt und wohl vorerst fehlen wird, steht weiter unten unter «Der
Review wird nicht abgewartet». Zwei Versuche, sie über einen Ablauf zu
beschaffen, sind gescheitert, und der dritte — ein Check-Run, der neben dem
Merge herläuft — hat sie am 19.9.2026 auf #62 ebenfalls nicht geliefert. Sie
käme erst mit einer Sperre, die das Mergen bis zum Urteil verhindert.

Eine parallele Session an `lindas-mcp` meldet, die Tabelle sei bei Befund und
ohne Befund **zeichengleich** und beweise nur, DASS geprüft wurde. Das deckt
sich mit dem, was hier steht, ist aber **fremde Angabe aus einem anderen Repo
und hier nicht nachgemessen** — als Beleg taugt es nicht, als Hinweis, wo zu
suchen wäre, schon.

Und ein befundloser Lauf ist kein Freispruch. Am 23.8. lief derselbe Text durch
42 Reviews: 36 meldeten denselben P2-Befund, 6 die Befundlos-Meldung — gleiche
Eingabe, gegenteiliges Urteil, alles in denselben neun Minuten. Ein sauberer
Lauf sagt damit etwas über den Lauf, nicht über den Text. Wer sein Häkchen
daran hängt, hängt es an einen Münzwurf.

Portfolio-weit nachsehen:

```
search_pull_requests: user:malkreide commenter:chatgpt-codex-connector[bot] updated:>=<Datum>
```

Findet nur, wo er *kommentiert* hat. Repos ohne PR-Aktivität tauchen nicht auf
— das ist kein Beleg, dass dort geprüft wurde.

Zweiter Weg, den Prüfer zu verlieren, ganz ohne Kontingentproblem: zu schnell
mergen. Am 21./22.8. lagen zwischen «ready for review» und Merge mehrfach drei
bis fünf Sekunden. Codex wird beim Umschalten von Draft auf ready ausgelöst und
braucht danach Zeit; wer sofort mergt, hat das Häkchen gesetzt und den Review
nicht abgewartet.

**Seit der Laufstatus-Tabelle ist das vorher zu sehen und nicht erst hinterher.**
Das ist der praktische Wert der Form oben: Sie nennt Status UND Commit, ist vor
dem Merge abrufbar, und `Running` auf dem Head-Commit heisst, dass das Häkchen
noch nicht zu setzen ist. Bis dahin liess sich der zu frühe Merge nur
rekonstruieren, wenn er schon passiert war.

Am 19.9.2026 ist er trotzdem passiert, in diesem Repo, an PR #56:

| Zeit (UTC) | |
|---|---|
| 06:35:53 | Draft → ready for review |
| 06:35:59 | Codex-Review startet auf `b503b48` |
| 06:36:50 | **PR gemergt** |

**51 Sekunden** nach dem Start des Reviews. Die Tabelle stand in diesem Moment
auf `Running` und war abrufbar — der Beleg, dass noch niemand hingesehen hatte,
lag also vor und wurde nicht gelesen.

**Der Merge bricht den Lauf nicht ab.** Um 06:38:03, also **73 Sekunden nach
dem Merge**, stand die Tabelle auf `✅ Completed`. Diese Zeile stand hier eine
Fassung lang als offene Frage, weil zwischen Merge und erstem Nachsehen nur
gut eine Minute lag; der nächste Blick hatte die Antwort. Der Reflex, eine
Beobachtungslücke nicht zur Aussage zu machen, war richtig — die Lücke war
bloss kleiner als gedacht.

**Er startet sogar noch nach dem Merge.** Zwanzig Minuten später, an PR #57
desselben Repos, lagen zwischen «ready» (06:56:01) und Merge (06:56:05) **vier
Sekunden** — und der Lauf begann um 06:56:06, also eine Sekunde NACH dem
Merge. Codex hängt damit am `ready`-Ereignis und nicht am Zustand des PR; dass
er beim Anlaufen ins Leere greift, hält ihn nicht auf. Wer hofft, ein schneller
Merge spare wenigstens das Kontingent, irrt also auch darin.

Was der zu frühe Merge also kostet, ist nicht der Lauf, sondern das
**Zeitfenster zum Reagieren**: Wer 51 Sekunden nach dem Start mergt, hat die
Entscheidung getroffen, bevor das Ergebnis existierte. Kommt ein Befund, kommt
er auf einen PR, der nicht mehr zu ändern ist — er wäre in einem eigenen PR zu
beheben, was hier niemand tun kann, der den Befund nicht sucht.

**Was weiterhin NICHT belegt ist:** ob ein Befund auf einem bereits gemergten
PR überhaupt noch geschrieben wird. Hier kam keiner, und das ist zweideutig —
siehe den Absatz zu `✅ Completed` weiter oben. Ein sauber aussehender
Endzustand auf einem gemergten PR ist deshalb kein Freispruch, sondern eine
nicht durchgeführte Messung.

Die Grössenordnung fürs Warten, aus zwei Messungen desselben Tages:

| PR | Start | Ende | Dauer |
|---|---|---|---|
| #56 | 06:35:59 | 06:38:03 | **124 s** |
| #57 | 06:56:06 | 06:56:42 | **36 s** |
| #58 | 07:02:29 | 07:03:49 | **80 s** |
| #59 | 07:07:11 | 07:08:08 | **57 s** |
| #62 | 09:15:12 | 09:16:08 | **56 s** |

Hier stand eine Fassung lang «rund zwei Minuten; die nächste kann länger
brauchen». Die Vorsicht war richtig, die Richtung geraten: Die nächste brauchte
ein Drittel. Aus einer einzigen Messung eine Zahl zu machen und ihr einen
einseitigen Aufschlag mitzugeben, ist derselbe Fehler wie die erfundene
Sperrdauer weiter oben — nur kleiner und darum leichter zu übersehen.

Bekannt ist eine Spanne von **36 bis 124 Sekunden**, aus fünf Läufen. Der
fünfte (#62, 56 s) hat die Spanne nicht verschoben — das macht sie nicht zur
Regel, nur zu einer Spanne, die einmal gehalten hat. Was
daraus fürs Warten folgt, ist nicht eine Wartezeit, sondern eine Bedingung:
**Den Status lesen, nicht die Uhr.** Ein Timer, der auf die längste bekannte
Dauer gestellt ist, geht beim ersten längeren Lauf falsch; die Tabelle nicht.

### Der Review wird nicht abgewartet — was das Häkchen wert ist

Hier stand ein Verfahren. Es ist entfernt, weil es fünfmal nicht stattgefunden
hat. Was bleibt, ist die Tatsache und ihre Folge fürs Lesen.

**Gemessen am 19.9.2026, fünf PRs dieses Repos**, Zeit zwischen «ready for
review» und Merge:

| PR | ready → Merge | Stand des Laufs beim Merge |
|---|---|---|
| #56 | 57 s | lief (`Running`) |
| #57 | 4 s | startete erst 1 s danach |
| #58 | 20 s | lief (`Running`) |
| #59 | **2 s** | startete erst 8 s danach |
| #60 | 63 s | lief (`Running`) |
| #62 | **2 s** | startete erst 4 s danach |

Ein Codex-Lauf braucht 36 bis 124 Sekunden. In keinem der sechs Fälle lag beim
Merge ein Ergebnis vor.

Es lag nicht an fehlendem Wissen: #58 trug die Wartebedingung in der eigenen
Checkliste, #59 war der PR, der das Verfahren einführte, und bei #60 hatte ein
Agent den PR selbst auf ready geschaltet, um das Zeitfenster zu erzeugen — es
wurde 63 Sekunden gross und reichte trotzdem nicht. Zwei Anläufe, die Sache
über einen Ablauf zu regeln, sind damit gescheitert. Ein dritter Ablauf wäre
dieselbe Schraube ein drittes Mal.

**#62 ist der Beleg dafür, dass auch das Gate allein nicht reicht.** Es war
der PR, der das Gate einführte; sein Text nannte die Einschränkung in einem
eigenen Abschnitt. Der Job startete um 09:15:08 und wurde um 09:16:14 grün —
**66 Sekunden nach dem Merge**, der um 09:15:08 stattfand. Ein Check, der
nicht *required* ist, hält nichts auf. Das war vorher ein Argument und ist
jetzt eine Messung.

**Die Folge, und nur darum geht es hier: Ein gemergter PR in diesem Repo ist
kein Beleg, dass Codex hineingesehen hat.** Das Häkchen «Codex-Review
beantwortet oder behoben — kein offener Befund beim Merge» in der
PR-Vorlage wird gesetzt, bevor es zutrifft. Wer später wissen will, ob eine
Änderung geprüft wurde, muss es nachträglich am PR nachsehen:

- `get_comments`, den Kommentar mit `<!-- codex-pull-request-review-summary -->`
  heraussuchen und darin ZWEI Spalten lesen: **Status** und **Commit**. Der
  Commit muss der Head sein — eine Tabelle zu einem älteren Stand sagt nichts
  über den jetzigen.
- `✅ Completed` heisst «Lauf zu Ende», nicht «nichts gefunden». Die Befunde
  stehen woanders: `get_reviews` und `get_review_comments`, beide.
- Der Lauf überlebt den Merge und startet sogar noch danach — die Ergebnisse
  sind also auch auf einem längst gemergten PR da und nachlesbar. Nur eben
  erst, nachdem entschieden wurde.

**Was das Problem wirklich lösen würde**, ist keine Vereinbarung, sondern eine
Sperre: ein Check-Run, der als *required check* eingetragen ist und rot bleibt,
bis Codex geurteilt hat.

Seit dem 19.9.2026 liegt so einer hier: `.github/workflows/codex-gate.yml` mit
`scripts/classify_codex_review.py`, portiert aus `swiss-cultural-heritage-mcp`
und auf die hier gemessenen Fälle umgeschrieben. Der Job wartet nach jedem
`opened`, `ready_for_review`, `reopened` und `synchronize` bis zu 20 Minuten
auf ein Urteil und wird rot, wenn keines kommt. `synchronize` stösst vorher
selbst `@codex review` an — ein Push ist keiner der drei Auslöser, die Codex
in seinem Infokasten nennt.

**Der erste Live-Lauf liegt vor, auf PR #62 am 19.9.2026.** Der Job startete
um 09:15:08 (zwei Sekunden nach «ready»), pollte, sah um 09:16:08 die Tabelle
auf `✅ Completed` springen, ordnete sie als `clear` ein und endete um
09:16:14 mit `conclusion: success`. Die Mechanik trägt also — für den Weg
über `ready_for_review`.

**Drei Dinge fehlen ihm, und alle drei gehören benannt:**

- **Er ist kein required check.** Das einzutragen ist eine Repo-Einstellung,
  die der Agent-Proxy mit HTTP 403 sperrt — das kann nur ein Mensch, unter
  Settings → Branches (oder als Ruleset), Name: `codex-gate`. Wie teuer das
  ist, hat derselbe Lauf gemessen: #62 war um 09:15:08 gemergt, das Gate wurde
  um 09:16:14 grün. Es hat 66 Sekunden zu spät recht gehabt.
- **Der Weg über `synchronize` ist ungeprüft.** Nach einem Push kommentiert
  der Job selbst `@codex review`. Ob Codex auf einen Kommentar des
  `GITHUB_TOKEN`-Bots reagiert, ist nicht gemessen — #62 wurde nie
  nachgepusht, solange er offen war. Tut Codex es nicht, läuft das Gate nach
  jedem Push in den Timeout und sagt dort, dass ein Mensch `@codex review`
  schreiben muss.
- **Auf einem Draft läuft er nicht** (`if: draft == false`) und ist dort als
  `skipped` verzeichnet. Ob GitHub ein übersprungenes Ergebnis als erfüllten
  required check zählt, ist **ungemessen**; wer die Einstellung vornimmt,
  sollte es prüfen. Drafts sind zwar ohnehin nicht mergbar — aber eine
  Annahme, die nie geprüft wurde, gehört nicht in die Begründung einer
  Schranke.

**Was er NICHT geliefert hat, obwohl es erhofft war.** Oben steht, die
fehlende Kontrolle sei ein `Completed` auf einem PR, der beim Lauf noch OFFEN
war, und der Gate-Job liefere sie nebenbei. Er hat sie nicht geliefert: Auf
#62 lag der Merge um 09:15:08, der Codex-Lauf begann um 09:15:12 — **vier
Sekunden danach**, wie schon bei #57 und #59. Es ist jetzt die siebte
Beobachtung unter denselben Bedingungen und immer noch keine Gegenprobe.

Der Denkfehler steckte in der Erwartung: Nicht der Gate-Job entscheidet, wann
Codex läuft, sondern das `ready`-Ereignis — und wie schnell danach gemergt
wird, entscheidet ein Mensch. Ein Job, der neben dem Merge herläuft, kann ihn
nicht aufhalten. **Die Kontrolle käme erst mit dem required check**, und damit
ist sie derselbe eine Handgriff wie alles andere hier.

Bis dahin behauptet der Zustand `clear` im Klassifizierer ausdrücklich nur das
Gemessene («angesehen»), nicht «keine Befunde» —
`tests/test_classify_codex_review.py` hält den Wortlaut fest.

Wer stattdessen ein Skript oder eine Routine bauen will, stösst auf eine Wand,
die in dieser Datei schon zweimal beschrieben ist: Die GitHub-Werkzeuge hängen
an der Session, nicht am Konto. Ein Shell-Skript hat keinen Zugang (`curl` auf
`api.github.com` endet bei «GitHub access is not enabled for this session»),
und eine gefeuerte Routine erbt **keine** MCP-Werkzeuge. Wer eine Routine dafür
baut, baut etwas, das nichts prüfen kann und «geprüft» meldet.

Das Kontingent hängt am Konto, nicht am Repo, und Code-Reviews haben einen
eigenen Topf — nur GitHub-getriggerte Reviews zählen hinein. ChatGPT-Pläne
fahren ein rollendes Fünf-Stunden-Fenster plus Wochenlimits; welches greift,
steht im Codex-Dashboard. Welches hier griff, ist **offen**. Die Lücke oben
schliesst das Fünf-Stunden-Fenster nicht aus: Es kann sich zwischendurch
geöffnet und durch neue Auslöser wieder erschöpft haben. Das auszuschliessen
bräuchte den Nachweis, dass in der ganzen Spanne kein einziger Review durchlief
— den gibt es nicht, weil nur Fehlschläge beobachtet wurden. Eine lange Reihe
von Fehlschlägen belegt eine lange Reihe von Fehlschlägen, nicht ihre Ursache.

Zeigt das Dashboard freies Kontingent, während Reviews weiter scheitern, ist
das ein bekannter Fehler bei mehreren verbundenen Konten — dann den
GitHub-Connector in den Codex-Einstellungen trennen und neu verbinden.

Die Environment legt man unter `chatgpt.com/codex/cloud/settings/environments`
an, und zwar **je Repo**. Die Meldung sagt es selbst («for this repo»), und am
23.8. war es genau so: In `swiss-public-data-mcp` fehlte sie, dort kam kein
Review; in den übrigen Repos lief Codex am selben Morgen durch. Eine
Environment fürs Konto genügt also nicht — wer eine anlegt und den Rest für
erledigt hält, mergt weiter Ungeprüftes.

---

## Wenn zwei Agenten dasselbe tun

Vor dem Anlegen eines Branches mit vorgegebenem Namen prüfen, ob es ihn schon
gibt:

```bash
git ls-remote --heads origin claude/<name> | wc -l
```

Steht dort `1`, arbeitet jemand anderes daran — mit Schreibrecht auf denselben
Ref.

Ein PR mit leerem Diff wird geschlossen, nicht gemergt. Der Test ist
`get_files` auf dem PR: kommt `[]` zurück, ändert er nichts. Ein grüner Check
sagt dazu nichts — die CI prüft den Head, nicht die Differenz zur Basis.

Am 21.8.2026 liefen zwei Sessions dieselbe Aufgabe über 45 Repos, auf den
Branches `claude/codex-review-audit-templates-9sn6mx` und
`claude/codex-review-audit-7ioh56`. Wo die eine zuerst nach `main` kam, wurde
`main` in den Branch der anderen gemergt und der add/add-Konflikt zugunsten
von `main` aufgelöst. Übrig blieben 14 PRs, die durch sämtliche Gates grün
liefen und nichts enthielten; sie wurden gemergt und hinterliessen leere
Merge-Commits. Mit den zwei Folge-PRs, die aus demselben Grund gegenstandslos
waren, waren 16 der 59 PRs jenes Tages reine Reibung.

Dieselbe Klasse wie der handgeschriebene Stub, der denselben Feldnamen annahm
wie der Code: Nichts ist rot, weil nichts geprüft wird, worauf es ankommt.

## Dieses Repo

**ruff: genau eine Quelle** — `ruff==0.16.3` im dev-Extra von
`pyproject.toml`. Der dev-Install liefert damit die CI-Version, lokal wie
dort. Keine zweite Version in die Workflows schreiben: ein solcher Schritt
läuft nach dem Install und überstimmt den Pin still. `ci.yml` hatte zwei
solche Schritte (Jobs `test` und `lint`); `test_werkzeug_versionen.py` hält
beides fest. Eine `.pre-commit-config.yaml` gibt es nicht.

**Der `lint`-Job muss das Projekt installieren.** Er hatte als einzige
ruff-Quelle den eigenen Pin-Schritt — den ersatzlos zu streichen nahm ihm
das Werkzeug (`ruff: command not found`). Er trägt deshalb ein
`pip install -e ".[dev]"`, anders als der `test`-Job, der ohnehin installiert.

Vor dem Lauf `ruff --version` prüfen: ein älteres ruff früher im `PATH`
schlägt den Pin, ohne dass der Install etwas meldet.

**Gates, wörtlich aus `ci.yml`** (Matrix: Python 3.11 / 3.12 / 3.13):

```bash
python scripts/check_ruff_pin.py
ruff check src/ tests/ scripts/
ruff format --check src/ tests/ scripts/
python -m py_compile src/swiss_culture_mcp/server.py
python -c "from swiss_culture_mcp.server import mcp; print('Import OK')"
PYTHONPATH=src pytest tests/ -m "not live"   # nur Python 3.11
python scripts/check_version_sync.py
```

**Live-Tests.** `.github/workflows/live-tests.yml` läuft geplant
(`cron: "53 4 * * 1"`, wöchentlich Mo) plus `workflow_dispatch`, gegen
`api3.geo.admin.ch`, `opendata.swiss` und den BAK-News-Feed; die
Einordnung macht `scripts/classify_live_run.py`
(`clear` / `finding` / `unknown`), ein Fund öffnet bzw. schliesst ein
`upstream`-Issue. `schedule` greift nur auf dem Default-Branch: Änderungen
an der Datei wirken erst nach dem Merge, vorher von Hand auslösen.
Der pytest-Aufruf braucht **`--run-live`**; ohne die Option überspringt
sich jeder Live-Test selbst und der Lauf endet mit 4 übersprungen /
Exit 0. Der Flag fehlte, `test_live_workflow.py` hält ihn jetzt fest.
Die Sollwerte der ISOS-Zahlen stehen nicht in der API, sondern im Anhang 1
der VISOS (SR 451.12, Fassung 1.6.2026): 1253 Ortsbilder, ZH 73, GR 105,
alle 26 Kantone deckungsgleich mit `api3.geo.admin.ch`. Fällt der Test, erst
die Verordnung nachzählen. Gezählt wird nach ISOS-`nummer`, nie nach
Feature-`id`: Die Quelle liefert je Objekt mehrere Features, in GR bis zu 51.
Ein Live-Test läuft nie allein: Der modulweite HTTP-Client überlebt sonst
den Event-Loop des vorherigen Tests (`RuntimeError: Event loop is closed`,
sichtbar als `JSONDecodeError`). Die autouse-Fixture in `conftest.py` setzt
ihn je Live-Test zurück — ohne sie meldet der Job einen gebrochenen Vertrag,
wo nur zwei Tests hintereinander liefen.

**Wer den Cron überwacht, braucht selbst Werkzeug.** Am 17.8.2026 feuerte
`schedule` zum ersten fälligen Termin nicht; beide bisherigen Live-Läufe
liefen von Hand. Ein Check-in dafür als Routine (`create_trigger`) hilft nur
mit Vorsicht: Die gefeuerte Session erbt **keine** MCP-Tools — die Warnung
steht im Rückgabewert des Aufrufs. GitHub ist hier kein claude.ai-Connector
(`ListConnectors` liefert leer), sondern hängt an der Session und dem Repo,
das ihr angehängt ist; `curl` und `WebFetch` auf `api.github.com` enden bei
«GitHub access is not enabled for this session» bzw. 403. Eine solche
Routine muss den Fall «keine Tools» darum ausdrücklich behandeln und dem
Menschen die URL nennen, statt etwas zu melden, das sie nicht geprüft hat.

**Die Allowlist prüft das Ziel, die Fixture muss es aufschreiben.**
`_assert_host_allowed()` prüft den Host NACH der Umleitung. `opendata.swiss`
beantwortet die CKAN-Aufrufe mit 302 auf `ckan.opendata.swiss` — der Host
fehlte in `ALLOWED_HOSTS`, also scheiterte jeder `bak_get_opendata`-Aufruf
produktiv, während alle Unit-Tests grün blieben. `adressen.json` notierte
brav 200: Der Recorder folgte der Umleitung und schrieb den Ausgangs-Host
auf. Er schreibt jetzt `final_host` mit, `test_umleitungsziele.py` prüft für
jede abgerufene Adresse Start- und Zielhost gegen die Allowlist. Nur die
abgerufenen — `gisos` und `bak_wurzel` gibt der Server als Link aus, ohne sie
zu holen; deren Ziel `www.bak.admin.ch` gehört nicht in die Liste.

Fixtures liegen unter `tests/fixtures/`, erzeugt von
`scripts/record_fixtures.py`, Aufnahmedatum in `PROVENANCE.md` — nicht von
Hand pflegen. Der Recorder bricht bei einem vorübergehenden 502 der Quelle
ab; die Ausgabe endet dann an einer Stelle, die wegen der Pipe-Pufferung
nicht die fehlerhafte Sonde ist. Einfach nochmal laufen lassen.
Alles Weitere: `README.md`, `CONTRIBUTING.md`.
