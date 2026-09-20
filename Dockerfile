# syntax=docker/dockerfile:1.7
# Multi-stage build: install deps with pip into a venv, then ship a slim runtime.
# Same layout as the other servers of the Swiss Public Data MCP portfolio.
FROM python:3.13-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/

RUN python -m venv /app/.venv \
    && /app/.venv/bin/pip install --no-cache-dir .

# ---------------------------------------------------------------------------

FROM python:3.13-slim AS runtime

# The server reads MCP_TRANSPORT / MCP_HOST / MCP_PORT (see server.py:main).
# MCP_ALLOW_PUBLIC_BIND=true is required for a 0.0.0.0 bind: the container is
# the sandbox, and the platform's edge proxy is the only way in.
#
# SET MCP_ALLOWED_HOSTS AT DEPLOY TIME. It is the comma-separated list of
# hostnames this server answers to, without a scheme — e.g.
# `MCP_ALLOWED_HOSTS=mcp.example.ch`. It is deliberately NOT given a value
# here: the name depends on where the image is deployed, and a guess would
# reject every real request with HTTP 421.
#
# Left unset with MCP_HOST=0.0.0.0, the Host and Origin headers are not checked
# at all — measured, not inferred: `streamable_http_app()` derives its own
# allow-list from the bind host, and for 0.0.0.0 it derives none. The server
# logs `dns_rebinding_protection_off` on every such start. Loopback stays
# allowed either way, so the HEALTHCHECK below keeps working.
#
# ALLOWED_ORIGINS (also unset) is the CORS origin list for browser clients;
# empty means no browser origin is permitted. stdio and non-browser clients are
# unaffected by it.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    MCP_TRANSPORT=streamable_http \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8000 \
    MCP_ALLOW_PUBLIC_BIND=true

RUN groupadd --system mcp \
    && useradd --system --gid mcp --home-dir /app --shell /usr/sbin/nologin mcp

WORKDIR /app
COPY --from=builder --chown=mcp:mcp /app/.venv /app/.venv

USER mcp
EXPOSE 8000

# SCALE-004: let orchestrators/load balancers detect an unhealthy container.
# The HTTP transport opens MCP_PORT; a successful TCP connect means the server
# is up. Uses stdlib only (no curl in the slim image).
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os,socket; socket.create_connection(('127.0.0.1', int(os.getenv('MCP_PORT','8000'))), 3).close()" || exit 1

# Read-only, no-auth public-data server — no secrets required at runtime.
# Console entry point (not `python -m`), so the server module is imported once.
CMD ["swiss-culture-mcp"]
