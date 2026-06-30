# Quick Start

This guide gets Django Orbit running with the smallest possible setup.

## Basic Usage

```python
# settings.py
INSTALLED_APPS = [
    # ...
    "orbit",
]

MIDDLEWARE = [
    "orbit.middleware.OrbitMiddleware",
    # ...
]
```

```python
# urls.py
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

Then make a few requests to your app and open `/orbit/`.

## Recommended First Config

```python
ORBIT_CONFIG = {
    "ENABLED": True,
    "SLOW_QUERY_THRESHOLD_MS": 300,
    "AUTH_CHECK": lambda request: request.user.is_staff,
    "IGNORE_PATHS": ["/orbit/", "/static/", "/media/"],
    "WATCHER_FAIL_SILENTLY": True,
}
```

For shared or staging environments, start more conservatively:

```python
ORBIT_CONFIG = {
    "ENABLED": True,
    "AUTH_CHECK": lambda request: request.user.is_staff,
    "MCP_ENABLED": False,
    "MCP_INCLUDE_PAYLOADS": False,
    "LLM_CAPTURE_CONTENT": False,
    "LLM_CAPTURE_TOOL_CALL_ARGUMENTS": False,
    "WATCHER_FAIL_SILENTLY": True,
}
```

## What To Check First

- Main dashboard: `/orbit/`
- Stats dashboard: `/orbit/stats/`
- Health dashboard: `/orbit/health/`
- If using MCP: run `python manage.py orbit_mcp` from your Django project root and connect it from Claude, Codex, Cursor or another MCP-compatible assistant.
- If using AI providers: make one local OpenAI or Anthropic call and check the `AI/LLM` event filter. By default Orbit should show metadata, tokens and latency, not prompts or completions.

## Next Steps

- [Configuration Reference](configuration.md)
- [Dashboard Guide](dashboard.md)
- [Running the Demo](running-demo.md)
