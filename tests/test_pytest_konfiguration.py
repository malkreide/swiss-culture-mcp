"""Der Loop-Scope fuer Async-Fixtures steht ausdruecklich in `pyproject.toml`.

Bis zum 3.11.2026 fehlte der Eintrag. pytest-asyncio meldete darauf in jedem
Lauf eine `PytestDeprecationWarning`, auch im woechentlichen Live-Lauf: Ohne
Eintrag folgt der Loop dem Scope der Fixture, kuenftige Versionen geben
`function` vor.

Heute aendert der Eintrag am Verhalten nichts — das Repo hat keine einzige
Async-Fixture. Er legt fest, was fuer die naechste gilt, statt das der gerade
installierten Plugin-Version zu ueberlassen; pytest-asyncio ist nicht gepinnt.
"""

from __future__ import annotations


def test_fixture_loop_scope_ist_function(pytestconfig):
    """Geprueft wird, was pytest eingelesen hat, nicht der Dateitext.

    `getini` liefert `None`, wenn der Schluessel fehlt oder in der falschen
    Tabelle steht — beides Faelle, in denen die Warnung zurueckkaeme.
    """
    assert pytestconfig.getini("asyncio_default_fixture_loop_scope") == "function"
