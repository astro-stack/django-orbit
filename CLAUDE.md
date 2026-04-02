# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

**Django Orbit** is a reusable Django app (published to PyPI as `django-orbit`) that provides "satellite observability" — a debugging/monitoring dashboard at `/orbit/` that records requests, SQL queries, logs, exceptions, cache operations, model events, background jobs, and more. It is inspired by Laravel Telescope.

The key design constraint: **Orbit must never interfere with the host app**. Every watcher must fail gracefully (`WATCHER_FAIL_SILENTLY`), and all writes to `OrbitEntry` must be guarded by `_table_exists()` to prevent poisoning migrations on a fresh database.

## Commands

```bash
# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run a single test file
pytest tests/test_core.py

# Run a single test by name
pytest tests/test_core.py::test_middleware_captures_request

# Run with coverage
pytest --cov=orbit --cov-report=html

# Format and lint
black orbit tests
isort orbit tests
flake8 orbit tests
mypy orbit

# Run the demo server
python demo.py setup    # Populate sample data
python manage.py runserver
```

## Architecture

### Central model: `OrbitEntry` (`orbit/models.py`)

A single polymorphic model storing all telemetry. All event types share one table with a `type` discriminator and a `JSONField` payload. Entries are grouped across a request lifecycle via `family_hash`.

### Data flow

```
HTTP Request
    → OrbitMiddleware (orbit/middleware.py)
        → installs OrbitQueryWrapper on connection (orbit/recorders.py)
        → sets family_hash context for log handler (orbit/handlers.py)
        → calls get_response()
    → Response captured → OrbitEntry(type='request') saved
    → All SQL queries → OrbitEntry(type='query') saved
    → All log calls → OrbitEntry(type='log') via OrbitLogHandler
```

### Watcher system (`orbit/watchers.py`)

`install_all_watchers()` is called from `OrbitConfig.ready()`. Each watcher monkey-patches a Django/Python subsystem:
- **Command watcher**: patches `BaseCommand.execute`
- **Cache watcher**: patches `cache.get/set/delete`
- **Model watcher**: connects to `post_save`/`post_delete` signals
- **HTTP client watcher**: patches `urllib3` / `requests`
- **Mail watcher**: patches `EmailMessage.send`
- **Signal watcher**: patches `Signal.send`
- **Redis watcher**: patches `redis.StrictRedis`
- **Job watcher**: hooks into Celery/Django-Q/RQ signals

### Health / plug-and-play system (`orbit/health.py`)

Each watcher is registered via `@module_registry.register(name)`. If initialization raises, the module is marked `FAILED` and others continue. Status is visible at `/orbit/health/`.

### Key guard: `_table_exists()`

Every watcher's write path calls `_table_exists()` before touching the DB. The result is cached permanently once `True`. This prevents `InternalError` during `migrate` on a fresh DB (issue #15/#16) and avoids excessive DB connections.

### MCP Server (`orbit/mcp_server.py`, `orbit/management/commands/orbit_mcp.py`)

`create_mcp_server()` builds a `FastMCP` instance (from the optional `mcp>=1.0` package) that exposes 7 tools for AI assistants: `get_recent_requests`, `get_slow_queries`, `get_exceptions`, `get_n1_patterns`, `get_request_detail`, `search_entries`, `get_stats_summary`. Launched via `python manage.py orbit_mcp` using stdio transport. Install with `pip install django-orbit[mcp]`.

### Configuration (`orbit/conf.py`)

All behavior is controlled via `ORBIT_CONFIG` in Django settings. `get_config()` merges user config with defaults. Important keys: `ENABLED`, `RECORD_*` flags, `AUTH_CHECK` (callable), `SLOW_QUERY_THRESHOLD_MS`, `STORAGE_LIMIT`, `WATCHER_FAIL_SILENTLY`.

### Dashboard (`orbit/views.py`, `orbit/urls.py`)

HTMX-powered dark UI at `/orbit/`. Main views: entry list, entry detail, stats (`/orbit/stats/`), health (`/orbit/health/`). Auth gate applied via `AUTH_CHECK` config.

## Testing conventions

- Tests use in-memory SQLite (see `tests/settings.py`)
- `tests/settings.py` inherits from `example_project/settings.py`
- `pytest.ini_options` sets `DJANGO_SETTINGS_MODULE = "tests.settings"`
- Mark DB tests with `@pytest.mark.django_db`
- Signals watcher is disabled in tests (`RECORD_SIGNALS: False`) to avoid noise
- `conftest.py` lives in `tests/`

## Commit style

Follow Conventional Commits: `feat:`, `fix:`, `test:`, `chore:`, `docs:`, `refactor:`. Reference GitHub issues with `(#N)` in the commit body or title.
