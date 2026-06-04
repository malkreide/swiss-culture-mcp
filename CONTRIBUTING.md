# Contributing to swiss-culture-mcp

🌐 **English** | **[Deutsch](CONTRIBUTING.de.md)**

Thank you for your interest in this project! Contributions are welcome.

## How can I contribute?

**Report bugs:** Create an [Issue](../../issues) with a clear description, reproduction steps, and expected vs. actual output.

**Suggest features:** Describe the use case, ideally with a reference to Swiss cultural context (school projects, spatial planning, cultural tourism, AI demos, etc.).

**Contribute code:**

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Install dev dependencies: `pip install -e ".[dev]"`
4. Write tests for your changes
5. Run linter: `ruff check src/ tests/`
6. Commit with clear message: `git commit -m "feat: add tradition search by canton"`
7. Create a Pull Request

## Code Standards

- Python 3.11+, Ruff for linting
- Docstrings in English (for international compatibility)
- Comments and error messages may be in German or English
- All MCP tools must set `readOnlyHint: True` (read-only access)
- Pydantic models for all tool inputs

## Data Source Policy

This server uses exclusively **official Open Government Data (OGD)** sources from the Swiss federal government and cantons. New data sources must:

- Be publicly accessible (no login, no mandatory API key)
- Originate from official Swiss government bodies or public institutions
- Comply with OGD terms of use (e.g. Open Data Licence, CC BY)

## Tests

The test suite distinguishes between unit tests (mocked, no network) and live tests (real API calls):

```bash
# Unit tests (always runnable, no internet required)
PYTHONPATH=src pytest tests/ -m "not live"

# Live tests (internet and reachable APIs required)
PYTHONPATH=src pytest tests/ -m "live"
```

Live tests are marked with `@pytest.mark.live` and excluded from the CI pipeline.

## Security

If you discover a security vulnerability, please follow the responsible-disclosure process in [SECURITY.md](SECURITY.md) rather than opening a public issue.

## License

By contributing, you agree that your contributions are licensed under the MIT License — see [LICENSE](LICENSE).
