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
