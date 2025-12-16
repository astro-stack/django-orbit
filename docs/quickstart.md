# Quick Start

!!! info "Coming Soon"
    This page is under construction. We're working hard to bring you comprehensive documentation!

In the meantime, check out the [Installation Guide](installation.md) to get started.

## Basic Usage

```python
# settings.py
INSTALLED_APPS = [
    'orbit',
    ...
]

MIDDLEWARE = [
    'orbit.middleware.OrbitMiddleware',
    ...
]
```

```python
# urls.py
from django.urls import path, include

urlpatterns = [
    path('orbit/', include('orbit.urls')),
    ...
]
```

Then visit `/orbit/` in your browser! 🚀
