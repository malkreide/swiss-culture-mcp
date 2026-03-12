"""pytest conftest.py — registriert benutzerdefinierte CLI-Optionen."""


def pytest_addoption(parser):
    parser.addoption(
        "--run-live",
        action="store_true",
        default=False,
        help="Live-Integrationstests ausführen (erfordert Netzwerkzugang)",
    )
