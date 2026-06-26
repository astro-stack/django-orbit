# Django Orbit

**AI agent-native observability and debugging for Django.**

Django Orbit is a reusable Django app that records what your application is doing and exposes it through a dashboard and MCP tools. It captures requests, SQL queries, logs, exceptions, cache operations, jobs, storage, mail, permissions and more, then links related events by `family_hash` so humans and AI agents can debug from one coherent timeline.

Unlike Django Debug Toolbar, Orbit does not inject HTML into your app. It lives at its own isolated `/orbit/` URL and is designed to observe from a distance without interfering with the host project.

<img width="1312" height="612" alt="Django Orbit Dashboard" src="https://github.com/user-attachments/assets/87528512-b458-4217-8dde-699a23c507ce" />

[![PyPI version](https://img.shields.io/pypi/v/django-orbit?style=flat-square)](https://pypi.org/project/django-orbit/)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=flat-square&logo=python)](https://python.org)
[![Django](https://img.shields.io/badge/Django-4.0%2B-green?style=flat-square&logo=django)](https://djangoproject.com)
[![License](https://img.shields.io/badge/License-MIT-purple?style=flat-square)](LICENSE)
[![Code Style](https://img.shields.io/badge/Code%20Style-Black-black?style=flat-square)](https://github.com/psf/black)

- [Documentation](https://astro-stack.github.io/django-orbit)
- [Try the demo](#try-the-demo)
- [MCP / AI assistant setup](#mcp-ai-assistant-setup)

## Why Orbit

Django teams increasingly debug with AI coding agents, but most local observability tools are built only for humans. Orbit is built for both:

- humans get a focused dashboard for inspecting runtime behavior;
- agents get structured MCP tools for investigation and handoff;
- captured events are grouped by request family, so evidence stays connected;
- agent output is masked, bounded and read-only by default.

| Capability | Django Debug Toolbar | Django Orbit |
|---|---:|---:|
| Runs outside your app UI | No | Yes |
| Works with APIs and SPAs | Limited | Yes |
| Persistent request history | No | Yes |
| SQL, logs and exceptions together | Partial | Yes |
| Background jobs and infrastructure events | No | Yes |
| Agent-native MCP debugging tools | No | Yes |
| Request-to-fix handoff bundles | No | Yes |
| Plug-and-play watcher health | No | Yes |

Inspired by Laravel Telescope, Spatie Ray and Django Debug Toolbar.

## What Orbit Tracks

| Category | Events |
|---|---|
| HTTP | Requests, responses, headers, body, status codes |
| Database | SQL queries, slow queries, duplicate query / N+1 signals |
| Logging | Python `logging` output, any level |
| Exceptions | Exception type, message, traceback and request context |
| Cache | GET hits/misses, SET, DELETE |
| Models | ORM create, update and delete events |
| Commands | `manage.py` executions with exit code |
| HTTP Client | Outgoing requests via supported clients |
| Mail | Sent email metadata and body previews |
| Signals | Django signal dispatches |
| Jobs | Celery, Django-Q, RQ and APScheduler signals/hooks |
| Redis | GET, SET, DEL, HGET, LPUSH and more |
| Permissions | Authorization checks, granted/denied |
| Transactions | `atomic()` commits and rollbacks |
| Storage | File save/open/delete operations |

All events can be linked by `family_hash`, which lets you inspect every query, log and exception associated with one request or operation.

## What's New in v0.11.0

Orbit v0.11.0 expands the agent-native debugging workflow from single requests into daily and release-oriented triage:

- `investigate_endpoint` summarizes endpoint health across recent traffic;
- `daily_health_brief` produces local morning triage for exceptions, failed jobs, slow queries, N+1 candidates and warning logs;
- `generate_release_risk_brief` flags blocker and caution signals before deploys;
- all new workflow tools are exposed through MCP and honor `MCP_ENABLED: False`.

The 0.11 line keeps these capabilities local/open-source. Cloud monetization should focus on persistence, collaboration, alerts, shared bundles, team policies and scheduled workflows.
## Installation

```bash
pip install django-orbit
```

For AI assistant integration, install the MCP extra:

```bash
pip install django-orbit[mcp]
```

## Quick Start

Add Orbit to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ...
    "orbit",
]
```

Add the middleware early in the stack:

```python
MIDDLEWARE = [
    "orbit.middleware.OrbitMiddleware",
    # ...
]
```

Mount the dashboard URLs:

```python
from django.urls import include, path

urlpatterns = [
    path("orbit/", include("orbit.urls")),
    # ...
]
```

Run migrations and start Django:

```bash
python manage.py migrate orbit
python manage.py runserver
```

Visit `http://localhost:8000/orbit/`.

## Try the Demo

```bash
git clone https://github.com/astro-stack/django-orbit.git
cd django-orbit
pip install -e .
python demo.py setup
python manage.py runserver
```

| URL | Purpose |
|---|---|
| `http://localhost:8000/` | Demo app |
| `http://localhost:8000/orbit/` | Orbit dashboard |
| `http://localhost:8000/orbit/stats/` | Stats dashboard |
| `http://localhost:8000/orbit/health/` | Watcher health dashboard |

## MCP AI Assistant Setup

Orbit exposes a local MCP server so AI assistants can query live Django runtime evidence.

```bash
pip install django-orbit[mcp]
```

Add this server to Claude Desktop, Cursor, Windsurf or any MCP-compatible client:

```json
{
  "mcpServers": {
    "django-orbit": {
      "command": "python",
      "args": ["manage.py", "orbit_mcp"],
      "cwd": "/path/to/your/django/project"
    }
  }
}
```

The server launches on demand over stdio. It is read-only: it queries `OrbitEntry` data and never mutates the host app.

### Raw Telemetry Tools

| Tool | Purpose |
|---|---|
| `get_recent_requests` | Last N requests with status, path and duration |
| `get_slow_queries` | SQL queries above the configured threshold |
| `get_exceptions` | Exceptions within a time window |
| `get_n1_patterns` | Requests with duplicate-query evidence |
| `get_request_detail` | All events for one `family_hash` |
| `search_entries` | Keyword search across entries |
| `get_stats_summary` | Error rate, average response time and cache stats |

### Agent-Native Tools

| Tool | Purpose |
|---|---|
| `audit_mcp_exposure` | Show the effective MCP safety policy |
| `preview_masked_entry` | Preview one entry exactly as an agent sees it, with masked payload and risk paths |
| `find_sensitive_payload_risks` | Find recent entries whose payload keys look like secrets, tokens or credentials |
| `list_agent_safe_fields` | Document the allowlisted fields and payload policy per entry type |
| `investigate_request` | Diagnose one request family: timeline, signals, queries, hypotheses and next actions |
| `investigate_exception_group` | Summarize an exception fingerprint and affected paths |
| `create_incident_bundle` | Create JSON, Markdown or prompt handoff from request, fingerprint or ticket text |
| `build_debug_brief` | Match natural-language ticket text to recent evidence |
| `investigate_endpoint` | Summarize endpoint health, errors, slow requests and related exceptions |
| `compare_endpoint_windows` | Compare recent endpoint behavior against a baseline window to spot regressions |
| `find_n_plus_one_candidates` | Rank recent duplicate-query/N+1 candidates with suggested next tools |
| `summarize_exception_groups` | Group recent exceptions by fingerprint with affected paths and representatives |
| `daily_health_brief` | Produce local daily triage from recent runtime signals |
| `generate_release_risk_brief` | Flag blocker/caution signals before a release |
| `generate_pr_context` | Produce PR-ready evidence, test plan and release-risk context from Orbit data |
| `propose_fix_hypotheses` | Rank likely fix directions from captured evidence |
| `propose_test_plan` | Suggest regression/performance tests for the observed issue |

### Agent Workflow

A typical ticket-to-fix handoff looks like this:

```text
audit_mcp_exposure()
find_sensitive_payload_risks(limit=20)
build_debug_brief("checkout returns 500 payment token rejected")
create_incident_bundle("fingerprint", "<fingerprint>", format="markdown")
create_incident_bundle("fingerprint", "<fingerprint>", format="prompt")
propose_fix_hypotheses("fingerprint", "<fingerprint>")
propose_test_plan("family_hash", "<family_hash>")
generate_pr_context("fingerprint", "<fingerprint>")
compare_endpoint_windows("/checkout/", method="POST")
find_n_plus_one_candidates(hours=24)
summarize_exception_groups(hours=24)
```

The goal is not for Orbit to edit code. The goal is to give a human or coding agent enough structured, safe evidence to reproduce, test and fix the issue.

The same flow works in Codex, Claude Desktop/Claude Code, Cursor and other MCP-compatible assistants; see the docs demo for the Claude-specific config path.

## Agent Safety

Agent-facing output goes through Orbit's safe serializer:

- sensitive keys are masked using `MASK_KEYS`;
- payloads can be disabled with `MCP_INCLUDE_PAYLOADS: False`;
- result sizes are bounded by `MCP_MAX_LIMIT`;
- oversized payloads are replaced with truncation metadata;
- `MCP_ENABLED: False` blocks all MCP tools with a stable disabled response;
- `preview_masked_entry`, `find_sensitive_payload_risks` and `list_agent_safe_fields` let teams verify exactly what coding agents can see before sharing context.

Example:

```python
ORBIT_CONFIG = {
    "MCP_ENABLED": True,
    "MCP_INCLUDE_PAYLOADS": True,
    "MCP_MAX_LIMIT": 100,
    "MCP_MAX_PAYLOAD_CHARS": 12000,
}
```

## Configuration

All settings go in `ORBIT_CONFIG` or `ORBIT` in `settings.py`. Most projects can start with defaults.

```python
ORBIT_CONFIG = {
    "ENABLED": True,
    "SLOW_QUERY_THRESHOLD_MS": 500,
    "STORAGE_LIMIT": 1000,

    # Access control. Set this for shared/staging environments.
    "AUTH_CHECK": lambda request: request.user.is_staff,

    # Keep Orbit from breaking the host app if a watcher fails.
    "WATCHER_FAIL_SILENTLY": True,

    # MCP / agent exposure controls.
    "MCP_ENABLED": True,
    "MCP_INCLUDE_PAYLOADS": True,
    "MCP_MAX_LIMIT": 100,
    "MCP_MAX_PAYLOAD_CHARS": 12000,
}
```

All watchers can be controlled individually with `RECORD_*` flags such as `RECORD_REQUESTS`, `RECORD_QUERIES`, `RECORD_EXCEPTIONS`, `RECORD_JOBS`, `RECORD_REDIS`, `RECORD_TRANSACTIONS` and `RECORD_STORAGE`.

See the [configuration docs](https://astro-stack.github.io/django-orbit/configuration/) for the full list.

## Dashboard

### Main Dashboard: `/orbit/`

The main dashboard shows a live feed of captured entries. You can filter by type, search, inspect details, export JSON and navigate related entries.

### Stats Dashboard: `/orbit/stats/`

The stats dashboard summarizes request throughput, Apdex, percentiles, error rate, slow queries, cache hit rate, job health and security/permission signals.

### Health Dashboard: `/orbit/health/`

Each watcher registers with Orbit's health system. Failed or missing integrations are shown without taking down the rest of Orbit.

## Storage Backends

By default, Orbit stores entries in the project's default database. For production or heavier usage, route Orbit writes to a dedicated database alias:

```python
DATABASES = {
    "default": {...},
    "orbit": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "orbit.sqlite3",
    },
}

ORBIT_CONFIG = {
    "STORAGE_BACKEND": "orbit.backends.django_db.DjangoDBBackend",
    "STORAGE_DB_ALIAS": "orbit",
}
```

```bash
python manage.py migrate orbit --database=orbit
```

## Security Model

Orbit is powerful because it records application behavior. Treat access to `/orbit/` and MCP as developer/operator access.

Recommended defaults for shared environments:

```python
ORBIT_CONFIG = {
    "AUTH_CHECK": lambda request: request.user.is_staff,
    "MCP_ENABLED": False,  # enable only where local agent access is intended
    "WATCHER_FAIL_SILENTLY": True,
}
```

Orbit masks common sensitive keys in request data and agent-facing output, but you should still avoid exposing Orbit dashboards or MCP servers to untrusted users.

## Roadmap

The v0.10.0 base makes Orbit agent-native. Next tracks:

- OpenTelemetry bridge for interoperability with wider observability tooling;
- AI/LLM watcher for provider/model/token/tool-call metadata;
- dashboard affordances for copying incident bundles;
- GitHub/Jira ticket handoff flows;
- deeper query and regression analysis.

See [Agent-Native Roadmap](https://astro-stack.github.io/django-orbit/roadmap/).

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT. See [LICENSE](LICENSE).
