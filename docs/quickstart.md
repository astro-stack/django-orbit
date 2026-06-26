# Quick Start

This guide gets Django Orbit running with the smallest possible setup.

## Fast Path

After installing `django-orbit`, use the packaged helper to wire an existing Django project:

```bash
# Print the default install plan
django-orbit-quickstart

# Preview file changes without writing
django-orbit-quickstart --settings myproject/settings.py --urls myproject/urls.py

# Apply settings.py and urls.py changes
django-orbit-quickstart --settings myproject/settings.py --urls myproject/urls.py --write

# Use a custom dashboard path and MCP install guidance
django-orbit-quickstart --settings myproject/settings.py --urls myproject/urls.py --url-prefix _debug/orbit/ --with-mcp --write
```

The helper is intentionally conservative: it only adds `orbit`, `OrbitMiddleware`, the `include` import and the Orbit URL pattern when they are missing. Without `--write`, it runs as a dry-run.

Finish setup:

```bash
python manage.py migrate orbit
python manage.py runserver
```

## Manual Usage

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
}
```

## What To Check First

- Main dashboard: `/orbit/`
- Stats dashboard: `/orbit/stats/`
- Health dashboard: `/orbit/health/`

## Next Steps

- [Configuration Reference](configuration.md)
- [Dashboard Guide](dashboard.md)
- [Running the Demo](running-demo.md)
