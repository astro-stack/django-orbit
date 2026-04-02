# 🛰️ Django Orbit

<div align="center">

**Satellite Observability for Django**

*A debugging and observability dashboard that orbits your app without touching it.*

<img width="1919" height="905" alt="Django Orbit Dashboard" src="https://github.com/user-attachments/assets/2a88b143-3a25-4da4-aa6c-f61226536221" />

[![PyPI version](https://img.shields.io/pypi/v/django-orbit?style=flat-square)](https://pypi.org/project/django-orbit/)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=flat-square&logo=python)](https://python.org)
[![Django](https://img.shields.io/badge/Django-4.0%2B-green?style=flat-square&logo=django)](https://djangoproject.com)
[![License](https://img.shields.io/badge/License-MIT-purple?style=flat-square)](LICENSE)
[![Code Style](https://img.shields.io/badge/Code%20Style-Black-black?style=flat-square)](https://github.com/psf/black)

[📚 Documentation](https://astro-stack.github.io/django-orbit) · [🎮 Try the Demo](#-try-the-demo) · [⭐ Star on GitHub](https://github.com/astro-stack/django-orbit)

</div>

---

## Table of Contents

- [Why Orbit?](#-why-orbit)
- [What Orbit tracks](#-what-orbit-tracks)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Try the Demo](#-try-the-demo)
- [Configuration](#️-configuration)
- [Dashboards](#-dashboards)
- [MCP Server — AI Assistant Integration](#-mcp-server--ai-assistant-integration)
- [Background Job Integrations](#-background-job-integrations)
- [Health & Plug-and-Play](#-health--plug-and-play)
- [Security](#️-security)
- [Roadmap](#️-roadmap)
- [Contributing](#-contributing)

---

## 🎯 Why Orbit?

Unlike Django Debug Toolbar — which injects HTML into your templates — Django Orbit lives at its own isolated URL (`/orbit/`). It observes your application from a distance, like a satellite, without interfering with it.

| | Django Debug Toolbar | Django Orbit |
|---|---|---|
| Template injection | ✅ Yes | ❌ No |
| Works with APIs / SPAs | ❌ No | ✅ Yes |
| SQL + logs + exceptions | Partial | ✅ All in one |
| Background jobs | ❌ | ✅ Celery, RQ, Django-Q |
| AI assistant integration | ❌ | ✅ MCP Server |
| Health / module status | ❌ | ✅ |

Inspired by [Laravel Telescope](https://laravel.com/docs/telescope).

---

## 📡 What Orbit tracks

| Category | Events |
|---|---|
| **HTTP** | Requests, responses, headers, body, status codes |
| **Database** | SQL queries, slow queries, N+1 detection |
| **Logging** | All Python `logging` output, any level |
| **Exceptions** | Full traceback, request context |
| **Cache** | GET hits/misses, SET, DELETE (any backend) |
| **Models** | ORM create, update, delete events |
| **Commands** | `manage.py` executions with exit code |
| **HTTP Client** | Outgoing requests via `requests` / `httpx` |
| **Mail** | Sent emails with headers and body |
| **Signals** | Django signal dispatches |
| **Background Jobs** | Celery, Django-Q, RQ, APScheduler |
| **Redis** | GET, SET, DEL, HGET, LPUSH, and more |
| **Permissions** | Authorization checks, granted/denied |
| **Transactions** | `atomic()` blocks, commits, rollbacks |
| **Storage** | File save/open/delete (local + S3) |

All events are linked by `family_hash`, so you can see every query, log, and exception that occurred within a single request.

---

## 📦 Installation

```bash
pip install django-orbit

# With MCP support (AI assistant integration — Claude, Cursor, Copilot)
pip install django-orbit[mcp]
```

---

## 🚀 Quick Start

**1. Add to `INSTALLED_APPS`:**

```python
INSTALLED_APPS = [
    # ...
    'orbit',
]
```

**2. Add middleware** (early in the list):

```python
MIDDLEWARE = [
    'orbit.middleware.OrbitMiddleware',
    # ...
]
```

**3. Include URLs:**

```python
from django.urls import path, include

urlpatterns = [
    path('orbit/', include('orbit.urls')),
    # ...
]
```

**4. Migrate and run:**

```bash
python manage.py migrate orbit
python manage.py runserver
```

Visit **http://localhost:8000/orbit/** 🚀

---

## 🎮 Try the Demo

```bash
git clone https://github.com/astro-stack/django-orbit.git
cd django-orbit
pip install -e .
python demo.py setup
python manage.py runserver
```

| URL | |
|---|---|
| `http://localhost:8000/` | Demo app |
| `http://localhost:8000/orbit/` | Orbit Dashboard |
| `http://localhost:8000/orbit/stats/` | Stats Dashboard |
| `http://localhost:8000/orbit/health/` | Health Dashboard |

---

## ⚙️ Configuration

All settings go in `ORBIT_CONFIG` (or `ORBIT`) in your `settings.py`. Everything has a sensible default — you only need to set what you want to change.

```python
ORBIT_CONFIG = {
    'ENABLED': True,                      # set to DEBUG to auto-disable in production
    'SLOW_QUERY_THRESHOLD_MS': 500,
    'STORAGE_LIMIT': 1000,                # max entries to keep

    # Watchers — all enabled by default
    'RECORD_REQUESTS': True,
    'RECORD_QUERIES': True,
    'RECORD_LOGS': True,
    'RECORD_EXCEPTIONS': True,
    'RECORD_COMMANDS': True,
    'RECORD_CACHE': True,
    'RECORD_MODELS': True,
    'RECORD_HTTP_CLIENT': True,
    'RECORD_MAIL': True,
    'RECORD_SIGNALS': True,
    'RECORD_JOBS': True,
    'RECORD_REDIS': True,
    'RECORD_GATES': True,
    'RECORD_TRANSACTIONS': True,
    'RECORD_STORAGE': True,

    # Security
    'AUTH_CHECK': lambda request: request.user.is_staff,
    'IGNORE_PATHS': ['/orbit/', '/static/', '/media/'],

    # Resilience
    'WATCHER_FAIL_SILENTLY': True,        # failed watchers log errors but don't crash the app
}
```

---

## 📊 Dashboards

### Main Dashboard — `/orbit/`

HTMX-powered live feed with 3-second polling. Filter by event type, search by keyword, export to JSON, and click any entry to see its full detail in a slide-over panel.

### Stats Dashboard — `/orbit/stats/`

| Metric | |
|---|---|
| **Apdex Score** | User satisfaction index (0–1) |
| **Percentiles** | P50, P75, P95, P99 response times |
| **Error Rate** | Failure percentage with trend |
| **Throughput** | Requests per minute / hour |
| **Slow Queries** | Count and top offenders |
| **Cache Hit Rate** | Sparkline chart |
| **Job Success Rate** | Per-backend breakdown |
| **Top Denied Permissions** | Authorization audit |

Time range filters: 1h · 6h · 24h · 7d

### Health Dashboard — `/orbit/health/`

Shows the status of every Orbit module:

- 🟢 **Healthy** — working normally
- 🔴 **Failed** — initialization error (click for full traceback)
- 🟡 **Disabled** — turned off via config

---

## 🤖 MCP Server — AI Assistant Integration

Django Orbit exposes your telemetry as an [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server. Connect Claude, Cursor, Windsurf, or any MCP-compatible AI assistant and ask questions directly against your app's live data.

**Examples:**
- *"Why is `/api/orders/` slow?"*
- *"What exceptions occurred in the last hour?"*
- *"Find all N+1 patterns in the app"*
- *"Show me everything that happened during this request"*

### Setup

```bash
pip install django-orbit[mcp]
```

```json
// Claude Desktop → claude_desktop_config.json
// Cursor → .cursor/mcp.json
// Windsurf → .windsurfrc
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

The MCP server launches on-demand when your AI assistant needs it. No extra process to manage.

### Available tools

| Tool | What it returns |
|---|---|
| `get_recent_requests` | Last N requests with status, path, duration |
| `get_slow_queries` | SQL queries above threshold, sorted by duration |
| `get_exceptions` | Exceptions in a time window with full traceback |
| `get_n1_patterns` | Requests where N+1 duplicate queries were detected |
| `get_request_detail` | Every event for one request via `family_hash` |
| `search_entries` | Keyword search across all event types |
| `get_stats_summary` | Error rate, avg response time, cache hit rate |

---

## 🔧 Background Job Integrations

| Backend | How |
|---|---|
| **Celery** | Via signals (automatic) |
| **Django-Q** | Via signals (automatic) |
| **RQ** | Worker monkey-patching (automatic) |
| **APScheduler** | `register_apscheduler(scheduler)` |
| **django-celery-beat** | Via model signals (automatic) |

---

## 💚 Health & Plug-and-Play

Each watcher initializes independently. If Celery isn't installed, only the Celery watcher fails — everything else keeps working.

```python
from orbit import get_watcher_status, get_failed_watchers

get_watcher_status()
# {'cache': {'installed': True, 'error': None, 'disabled': False}, ...}

get_failed_watchers()
# {'celery': 'ModuleNotFoundError: No module named celery'}
```

---

## 🛡️ Security

Restrict access using any callable:

```python
ORBIT_CONFIG = {
    # Staff only
    'AUTH_CHECK': lambda request: request.user.is_staff,

    # Disable entirely in production
    'ENABLED': DEBUG,
}
```

Orbit automatically redacts sensitive fields (passwords, tokens, API keys) from request bodies and headers.

---

## 🗺️ Roadmap

### What's next

- **External storage backends** — persist events to PostgreSQL or Redis instead of SQLite
- **AI Insights engine** — automatic pattern detection and plain-English summaries powered by LLMs
- **VS Code / Cursor extension** — surface Orbit data in your editor sidebar while you code
- **Alerting** — Slack, email, and webhook notifications for exceptions and slow requests
- **Orbit Cloud** — shared team dashboards with historical data retention

---

## 🤝 Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

MIT — see [LICENSE](LICENSE).

---

<div align="center">

Inspired by [Laravel Telescope](https://laravel.com/docs/telescope), [Spatie Ray](https://spatie.be/products/ray), and [Django Debug Toolbar](https://django-debug-toolbar.readthedocs.io/).

[⭐ Star on GitHub](https://github.com/astro-stack/django-orbit) · [📚 Documentation](https://astro-stack.github.io/django-orbit) · [🐛 Issues](https://github.com/astro-stack/django-orbit/issues)

</div>
