# Sicherheitsrichtlinie & -posture

🌐 **[English](SECURITY.md)** | **Deutsch**

`swiss-culture-mcp` wurde gegen den internen MCP-Best-Practice-Audit-Katalog
([`mcp-audit-skill`](https://github.com/malkreide/mcp-audit-skill), ~68 Checks,
Spec 2025-06-18) gehärtet. Dieses Dokument fasst die Sicherheits-Posture
zusammen und hält die **akzeptierten Risiken** für Kontrollen fest, die
bewusst auf der Portfolio-/Gateway-Ebene und nicht in diesem einzelnen Server
behandelt werden.

## Eine Schwachstelle melden

Bitte eröffnen Sie ein privates Security Advisory im GitHub-Repository oder
kontaktieren Sie den in `README.md` genannten Maintainer. Erstellen Sie für
ausnutzbare Schwachstellen keine öffentlichen Issues.

## Posture-Zusammenfassung

Dies ist ein **nur lesender**, **PII-freier** MCP-Server auf **öffentlichen
Open-Data**-Quellen. Alle 10 Tools setzen ausschliesslich HTTP-GET-Anfragen an
eine feste Menge eidgenössischer Open-Data-Endpunkte ab (geo.admin.ch REST,
news.admin.ch RSS, opendata.swiss CKAN, lebendige-traditionen.ch — siehe
`README.de.md`). Bereits umgesetztes Hardening:

| Bereich | Kontrolle |
|---|---|
| Egress | HTTPS gegen eine feste Allow-List eidgenössischer / partnerschaftlicher Hosts; keine nutzergesteuerten URLs werden konstruiert (SEC-005) |
| TLS | Zertifikatsprüfung standardmässig aktiv (httpx-Default); nie deaktiviert |
| Binding | stdio-Transport als Default; der optionale `streamable_http`-Transport bindet auf `127.0.0.1` und verweigert das Binden auf `0.0.0.0`, sofern nicht `MCP_ALLOW_PUBLIC_BIND=true` explizit gesetzt ist (SEC-003) |
| Input | Pydantic-v2-Validierung auf jedem Tool-Input-Modell; ISOS-Detail-Slugs werden vor der Nutzung per Regex validiert (SEC-005) |
| XML | RSS-Parsing nutzt `defusedxml.ElementTree` — schützt vor XXE und Billion-Laughs (SEC-004) |
| HTML | Nicht vertrauenswürdiges HTML von lebendige-traditionen.ch wird defensiv geparst; Regressions-Fixtures sichern den Scraper ab (SEC-019) |
| Tools | Jedes Tool setzt `readOnlyHint: True`; es existieren keine Schreib-, Mutations- oder Löschpfade |
| Secrets | Keine erforderlich — der Server nutzt keinen API-Key und keine Credentials; nichts Geheimes wird gespeichert oder geloggt |
| Fehler | Upstream-Fehlerbodies werden nur auf stderr geloggt; das Modell erhält eine generische, nicht leckende Meldung (SEC-006) |
| Logging | Strukturierte JSON-Logs fest auf stderr; stdout ist dem JSON-RPC-Stream vorbehalten (OBS-001) |
| Resilienz | Ein 20s-Timeout pro Anfrage begrenzt jeden Upstream-Aufruf; Obergrenzen pro Abfrage limitieren die Antwortgrösse (SCALE-001/002) |

Der Audit (`audit/audit-report.md`) und sein Re-Run — 2 High, 5 Medium und 1 Low —
sind per `v1.1.0` **vollständig geschlossen**, jeweils durch einen
Regression-Test abgesichert (54 Tests, CI-Matrix 3.11/3.12/3.13). Die
Hardening-Historie steht in `CHANGELOG.md`.

> ⚠️ Der Server selbst hat **keine Authentifizierung**. Ein Binding auf eine
> öffentliche Schnittstelle ohne vorgelagerten Auth-Layer macht ihn zum offenen
> Proxy für die Bundesdaten-Quellen. Vor jedem `0.0.0.0`-Deployment immer einen
> authentifizierenden Reverse-Proxy (Cloudflare Access, oauth2-proxy,
> nginx + auth_request) vorschalten.

## Akzeptierte Risiken (Kontrollen auf Portfolio-Ebene)

Die folgenden Audit-Checks sind in diesem Server **bewusst nicht** implementiert.
Sie sind portfolioweite Belange, die am besten auf einer MCP-Gateway-/Host-Ebene
durchgesetzt werden; das Restrisiko ist hier gering, da der Server nur lesend
ist und nur eine kleine Menge vertrauenswürdiger Open-Data-Anbieter erreicht.

- **Tool-Allow-Listing über ein MCP-Gateway** — eine Tool-spezifische Allow-List
  gehört zum MCP-Host/-Gateway, der mehrere Server aggregiert, nicht zu einem
  einzelnen Server mit fixem, nur lesendem Tool-Set.
- **Pre-Flight-Tool-Poisoning-Erkennung** — die Tool-Definitionen dieses Servers
  sind versionskontrolliert, im Repo verfasst und per PR reviewt; es gibt keine
  dynamische oder entfernte Tool-Registrierung. Server-übergreifende
  Poisoning-Erkennung bleibt eine Gateway-/Host-Verantwortung auf
  Portfolio-Ebene.
- **Multi-Tenant-Observability (Request-/Correlation-IDs)** — nur relevant, falls
  der Server jemals im Multi-Tenant-HTTP-Modus betrieben wird; für das aktuelle
  Single-Tenant-stdio-/Single-User-HTTP-Profil nicht zutreffend.

## Auslöser für eine Neubewertung

Diese Akzeptanzen sollten überprüft werden, sobald der Server jemals:

- **Schreib**-Fähigkeit erhält oder **PII** verarbeitet, oder
- ein **Authentifizierungs**-Modell hinzufügt (dann gebundene, TTL-behaftete,
  serverseitig invalidierbare Session-IDs implementieren und vor dem Merge
  erneut auditieren), oder
- Tools **dynamisch** / aus entfernten Quellen registriert, oder
- hinter einem geteilten MCP-Gateway aggregiert wird (dann das Tool-Allow-Listing
  und die Tool-Poisoning-Erkennung des Gateways aktivieren).
