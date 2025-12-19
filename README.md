# 🛰️ Django Orbit

<div align="center">

**Satellite Observability for Django**

*A modern debugging and observability tool that orbits your Django application without touching it.*

![Demo](demo.gif)

[![Star on GitHub](https://img.shields.io/github/stars/astro-stack/django-orbit?style=social)](https://github.com/astro-stack/django-orbit)

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=flat-square&logo=python)](https://python.org)
[![Django](https://img.shields.io/badge/Django-4.0%2B-green?style=flat-square&logo=django)](https://djangoproject.com)
[![License](https://img.shields.io/badge/License-MIT-purple?style=flat-square)](LICENSE)
[![Code Style](https://img.shields.io/badge/Code%20Style-Black-black?style=flat-square)](https://github.com/psf/black)

[📚 Documentation](https://astro-stack.github.io/django-orbit) · [🎮 Live Demo](#-try-the-demo) · [⭐ Star on GitHub](https://github.com/astro-stack/django-orbit)

</div>

---

## ✨ Features

### Core Observability
- 🌐 **Request Tracking** - Capture HTTP requests with headers, body, and response
- 🗄️ **SQL Recording** - Log queries with N+1 detection and slow query alerts
- 📝 **Log Aggregation** - Automatically capture Python logging output
- 🚨 **Exception Tracking** - Full traceback capture for errors
- ⏱️ **Performance Metrics** - Duration tracking for requests and queries

### Extended Monitoring (v0.2.0+)
- 🟣 **Management Commands** - Track `python manage.py` executions
- 🟠 **Cache Operations** - Monitor hits, misses, sets, deletes
- 🔵 **Model Events** - ORM create/update/delete auditing
- 🩷 **HTTP Client** - Outgoing API request monitoring
- 📧 **Mail Capture** - Track sent emails
- ⚡ **Django Signals** - Event dispatch monitoring

### Advanced Features (v0.5.0+)
- ⏰ **Background Jobs** - Celery, Django-Q, RQ, APScheduler monitoring
- 🔴 **Redis Operations** - Track GET, SET, DEL, and more
- 🛡️ **Gates/Permissions** - Authorization check auditing
- 📊 **Stats Dashboard** - Apdex score, percentiles, interactive charts

### Dashboard Features
- 🌙 **Beautiful Dark UI** - Space-themed mission control
- ⚡ **Live Updates** - HTMX-powered real-time feed
- 🔗 **Event Correlation** - Link related events with family grouping
- 🔒 **Zero DOM Injection** - Lives at its own URL, no template pollution

## 🎯 Philosophy

> **"Satellite Observability"** - Like a satellite, Orbit observes your application from a distance without interfering with it.

Unlike Django Debug Toolbar which injects HTML into your templates, Django Orbit runs on its own isolated URL (`/orbit/`). This means:

- ✅ No DOM pollution
- ✅ No CSS conflicts
- ✅ Works with any frontend (React, Vue, HTMX, etc.)
- ✅ API-friendly debugging
- ✅ Clean separation of concerns

## 📦 Installation

```bash
pip install django-orbit
```

## 🎮 Try the Demo

```bash
git clone https://github.com/astro-stack/django-orbit.git
cd django-orbit
pip install -e .
python demo.py setup    # Creates sample data with ALL entry types
python manage.py runserver
```

Then visit:
- **Demo app**: http://localhost:8000/
- **Orbit Dashboard**: http://localhost:8000/orbit/
- **Stats Dashboard**: http://localhost:8000/orbit/stats/

## 🚀 Quick Start

### 1. Add to Installed Apps

```python
# settings.py
INSTALLED_APPS = [
    # ...
    'orbit',
]
```

### 2. Add Middleware

```python
# settings.py
MIDDLEWARE = [
    'orbit.middleware.OrbitMiddleware',  # Add early
    # ...
]
```

### 3. Include URLs

```python
# urls.py
from django.urls import path, include

urlpatterns = [
    path('orbit/', include('orbit.urls')),
    # ...
]
```

### 4. Run Migrations

```bash
python manage.py migrate orbit
```

### 5. Visit the Dashboard

Navigate to `http://localhost:8000/orbit/` 🚀

## ⚙️ Configuration

```python
# settings.py
ORBIT_CONFIG = {
    'ENABLED': True,
    'SLOW_QUERY_THRESHOLD_MS': 500,
    'STORAGE_LIMIT': 1000,
    
    # Core watchers
    'RECORD_REQUESTS': True,
    'RECORD_QUERIES': True,
    'RECORD_LOGS': True,
    'RECORD_EXCEPTIONS': True,
    
    # Extended watchers
    'RECORD_COMMANDS': True,
    'RECORD_CACHE': True,
    'RECORD_MODELS': True,
    'RECORD_HTTP_CLIENT': True,
    'RECORD_MAIL': True,
    'RECORD_SIGNALS': True,
    
    # Advanced watchers (v0.5.0+)
    'RECORD_JOBS': True,
    'RECORD_REDIS': True,
    'RECORD_GATES': True,
    
    # Security
    'AUTH_CHECK': lambda request: request.user.is_staff,
    'IGNORE_PATHS': ['/orbit/', '/static/', '/media/'],
}
```

## 📊 Stats Dashboard

The new Stats Dashboard (`/orbit/stats/`) provides advanced analytics:

| Metric | Description |
|--------|-------------|
| **Apdex Score** | User satisfaction index (0-1) |
| **Percentiles** | P50, P75, P95, P99 response times |
| **Error Rate** | Failure percentage with trend |
| **Throughput** | Requests per minute/hour |
| **Database** | Slow queries, N+1 detection |
| **Cache** | Hit rate with sparkline chart |
| **Jobs** | Success rate, failure tracking |
| **Permissions** | Top denied permissions |

## 🔧 Background Job Integrations

Orbit automatically detects and monitors:

| Backend | Integration |
|---------|-------------|
| **Celery** | Via signals (automatic) |
| **Django-Q** | Via signals (automatic) |
| **RQ** | Worker patching (automatic) |
| **APScheduler** | `register_apscheduler(scheduler)` |
| **django-celery-beat** | Via model signals (automatic) |

## 🛡️ Security

```python
# Restrict access to staff users
ORBIT_CONFIG = {
    'AUTH_CHECK': lambda request: request.user.is_staff,
}

# Or disable in production
ORBIT_CONFIG = {
    'ENABLED': DEBUG,
}
```

Orbit automatically hides sensitive data (passwords, tokens, API keys).

## 🗺️ Roadmap

### Implemented ✅
- Request/Query/Log/Exception tracking
- N+1 detection with duplicate navigation
- Management Commands, Cache, Models, HTTP Client
- Mail, Signals watchers
- Jobs (Celery, Django-Q, RQ, APScheduler)
- Redis operations
- Gates/Permissions
- Stats Dashboard with Apdex, charts
- Dashboard authentication
- Search, Export, Pagination

### Future 🔮
- External storage backends (Redis, PostgreSQL)
- Performance recommendations
- Custom dashboards
- Webhook integrations

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md).

## 📄 License

MIT License - see [LICENSE](LICENSE).

## 💖 Acknowledgments

Inspired by [Laravel Telescope](https://laravel.com/docs/telescope), [Spatie Ray](https://spatie.be/products/ray), and [Django Debug Toolbar](https://django-debug-toolbar.readthedocs.io/).

---

<div align="center">

**Built with ❤️ for the Django community**

[⭐ Star us on GitHub](https://github.com/astro-stack/django-orbit) · [📚 Read the Docs](https://astro-stack.github.io/django-orbit)

</div>
