# 🛰️ Django Orbit

<div align="center">

**Satellite Observability for Django**

*A modern debugging and observability tool that orbits your Django application without touching it.*

<!-- demo file -->
<video src="demo.mp4" controls></video>

https://labs.wearehik.com/django-orbit

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=flat-square&logo=python)](https://python.org)
[![Django](https://img.shields.io/badge/Django-4.0%2B-green?style=flat-square&logo=django)](https://djangoproject.com)
[![License](https://img.shields.io/badge/License-MIT-purple?style=flat-square)](LICENSE)
[![Code Style](https://img.shields.io/badge/Code%20Style-Black-black?style=flat-square)](https://github.com/psf/black)

</div>

---

## ✨ Features

- 🌐 **Request Tracking** - Capture all HTTP requests with headers, body, and response data
- 🗄️ **SQL Recording** - Log every database query with timing, caller info, and duplicate detection
- 📝 **Log Aggregation** - Automatically capture Python logging output
- 🚨 **Exception Tracking** - Full traceback capture for unhandled exceptions
- ⏱️ **Performance Metrics** - Duration tracking for requests and queries
- 🔗 **Event Correlation** - Link related events with `family_hash` grouping
- 🌙 **Beautiful Dark UI** - Space-themed mission control dashboard
- ⚡ **Live Updates** - HTMX-powered real-time feed
- 🔒 **Zero DOM Injection** - Unlike Debug Toolbar, lives at its own URL

## 🎯 Philosophy

> **"Satellite Observability"** - Like a satellite, Orbit observes your application from a distance without interfering with it.

Unlike Django Debug Toolbar which injects HTML into your templates, Django Orbit runs on its own isolated URL (`/orbit/`). This means:

- ✅ No DOM pollution
- ✅ No CSS conflicts
- ✅ Works with any frontend (React, Vue, HTMX, etc.)
- ✅ API-friendly debugging
- ✅ Clean separation of concerns

## 📦 Installation

### From PyPI

```bash
pip install django-orbit
```

### From Source

```bash
git clone https://github.com/astro-stack/django-orbit.git
cd django-orbit
pip install -e .
```


## 🎮 Try the Demo

The fastest way to see Django Orbit in action:

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

### Demo Script Commands

| Command | Description |
|---------|-------------|
| `python demo.py setup` | Creates sample data: books, reviews + 40+ Orbit entries (all 9 types) |
| `python demo.py fill` | Tests live watchers by making HTTP requests (requires server) |
| `python demo.py simulate` | Simulates continuous traffic for load testing |
| `python demo.py status` | Shows current entry counts |
| `python demo.py clear` | Clears all Orbit entries |

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
    'orbit.middleware.OrbitMiddleware',  # Add early in the list
    # ...
]
```

### 3. Include URLs

```python
# urls.py

from django.urls import path, include

urlpatterns = [
    # ...
    path('orbit/', include('orbit.urls')),
]
```

### 4. Run Migrations

```bash
python manage.py migrate orbit
```

### 5. Visit the Dashboard

Navigate to `http://localhost:8000/orbit/` to see your mission control!

## ⚙️ Configuration

Django Orbit is configurable via Django settings:

```python
# settings.py

ORBIT_CONFIG = {
    # Enable/disable Orbit (default: True)
    'ENABLED': True,
    
    # Slow query threshold in milliseconds (default: 500)
    'SLOW_QUERY_THRESHOLD_MS': 500,
    
    # Paths to ignore (default list shown)
    'IGNORE_PATHS': [
        '/orbit/',
        '/static/',
        '/admin/jsi18n/',
        '/favicon.ico',
    ],
    
    # Headers to hide from capture (default list shown)
    'HIDE_REQUEST_HEADERS': [
        'Authorization',
        'Cookie',
        'X-CSRFToken',
    ],
    
    # Body keys to hide (default list shown)
    'HIDE_REQUEST_BODY_KEYS': [
        'password',
        'token',
        'secret',
        'api_key',
    ],
    
    # Maximum request body size to capture (default: 64KB)
    'MAX_BODY_SIZE': 65536,
    
    # Maximum entries to keep (default: 1000)
    'STORAGE_LIMIT': 1000,
    
    # What to record (all default: True)
    'RECORD_REQUESTS': True,
    'RECORD_QUERIES': True,
    'RECORD_LOGS': True,
    'RECORD_EXCEPTIONS': True,
}
```

## 🎨 Dashboard Features

### Main Feed

The main feed shows a real-time stream of events:

- **Requests** - HTTP requests with status codes
- **Queries** - SQL queries with timing
- **Logs** - Python log messages
- **Exceptions** - Errors with tracebacks
- **Jobs** - Background task tracking (coming soon)

### Detail Panel

Click any entry to open the slide-over detail panel featuring:

- Full JSON payload with syntax highlighting
- Request/Response headers
- SQL query with caller location
- Exception traceback
- Related events (same request family)

### Sidebar Navigation

Filter events by type with live count badges:

- 🌐 Requests
- 🗄️ Queries
- 📝 Logs
- 🚨 Exceptions
- ⏰ Jobs

## 📊 Entry Types

### Request Entry

Captures HTTP request/response cycle:

```json
{
  "method": "POST",
  "path": "/api/users/",
  "status_code": 201,
  "duration_ms": 45.2,
  "client_ip": "127.0.0.1",
  "headers": {"Content-Type": "application/json"},
  "body": {"username": "john", "password": "***HIDDEN***"},
  "query_count": 5
}
```

### Query Entry

Captures SQL queries:

```json
{
  "sql": "SELECT * FROM users WHERE id = %s",
  "params": [1],
  "duration_ms": 2.3,
  "is_slow": false,
  "is_duplicate": false,
  "caller": {
    "filename": "/app/views.py",
    "lineno": 42,
    "function": "get_user"
  }
}
```

### Log Entry

Captures Python logging:

```json
{
  "level": "WARNING",
  "message": "Rate limit exceeded for user 123",
  "logger": "myapp.views",
  "module": "views",
  "filename": "views.py",
  "lineno": 78
}
```

### Exception Entry

Captures unhandled exceptions:

```json
{
  "exception_type": "ValueError",
  "message": "Invalid input data",
  "traceback": [
    {"filename": "/app/views.py", "lineno": 42, "name": "process", "line": "raise ValueError(...)"}
  ],
  "request_method": "POST",
  "request_path": "/api/process/"
}
```

## 🔧 Advanced Usage

### Manual Entry Creation

You can create entries programmatically:

```python
from orbit.models import OrbitEntry

# Log a custom event
OrbitEntry.objects.create(
    type=OrbitEntry.TYPE_LOG,
    payload={
        'level': 'INFO',
        'message': 'Custom event',
        'custom_data': {'key': 'value'}
    }
)
```

### Family Hash Grouping

Events are automatically grouped by request using `family_hash`. You can query related events:

```python
# Get all events for a specific request
request_entry = OrbitEntry.objects.requests().first()
related = OrbitEntry.objects.for_family(request_entry.family_hash)
```

### Custom Log Handler

The `OrbitLogHandler` integrates with Python logging:

```python
import logging

logger = logging.getLogger('myapp')
logger.info('This will be captured by Orbit!')
```

## 🛡️ Security Considerations

### Production Usage

Django Orbit is designed for **development and staging environments**. For production:

1. **Disable in production** or protect the URL:

```python
# settings.py
ORBIT_CONFIG = {
    'ENABLED': DEBUG,  # Only enable in debug mode
}
```

2. **Use authentication**:

```python
# settings.py
ORBIT_CONFIG = {
    # Callable that takes 'request' and returns True/False
    'AUTH_CHECK': lambda request: request.user.is_staff,
}
```

### Sensitive Data

Orbit automatically hides:

- Authorization headers
- Cookies
- Password fields
- Tokens and API keys

Configure additional fields to hide via `HIDE_REQUEST_HEADERS` and `HIDE_REQUEST_BODY_KEYS`.

## 🗺️ Roadmap

### Already Implemented ✅
- [x] Request tracking
- [x] SQL query recording with slow/duplicate detection
- [x] Log aggregation
- [x] Exception capture with tracebacks
- [x] Event correlation (family_hash grouping)
- [x] **Management Commands** - Track `python manage.py` commands
- [x] **Cache Operations** - Hit/miss/set/delete tracking
- [x] **Model Events** - ORM create/update/delete auditing
- [x] **HTTP Client** - Outgoing API request monitoring
- [x] **Debug Dumps** - `orbit_dump()` for variable inspection
- [x] **Data Security** - Dashboard authentication (AUTH_CHECK)
- [x] **Data Cleanup** - Pruning management command
- [x] **Search & Filter** - Search by UUID or content
- [x] **Export** - Download entries as JSON (Single & Bulk)

### Coming Soon 🚧
- [ ] **Email Capture** - Track sent emails
- [ ] **Django Signals** - Event dispatch monitoring

### Future Plans 🔮
- [ ] Redis/external storage backend
- [ ] Background job tracking (Celery, RQ, etc.)
- [ ] Scheduled tasks monitoring
- [ ] Export/import functionality
- [ ] Advanced filtering and search
- [ ] Performance insights and recommendations

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

Django Orbit is open source under the [MIT License](LICENSE).

## 💖 Acknowledgments

Inspired by:

- [Laravel Telescope](https://laravel.com/docs/telescope) - The original inspiration
- [Spatie Ray](https://spatie.be/products/ray) - Beautiful debugging experience
- [Django Debug Toolbar](https://django-debug-toolbar.readthedocs.io/) - The Django classic

---

<div align="center">

**Built with ❤️ for the Django community**

[⭐ Star us on GitHub](https://github.com/astro-stack/django-orbit)

</div>
