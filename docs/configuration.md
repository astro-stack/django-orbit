# Configuration Reference

Django Orbit is configured through the `ORBIT_CONFIG` dictionary in your Django settings.

## Full Configuration

```python
# settings.py

ORBIT_CONFIG = {
    # Core Settings
    'ENABLED': True,
    'AUTH_CHECK': None,  # Callable or path to function
    'STORAGE_LIMIT': 1000,
    
    # Recording Settings - Phase 1 (Core)
    'RECORD_REQUESTS': True,
    'RECORD_QUERIES': True,
    'RECORD_LOGS': True,
    'RECORD_EXCEPTIONS': True,
    'RECORD_DUMPS': True,
    
    # Recording Settings - Phase 2 (Extended)
    'RECORD_COMMANDS': True,
    'RECORD_CACHE': True,
    'RECORD_MODELS': True,
    'RECORD_HTTP_CLIENT': True,
    'RECORD_MAIL': True,
    'RECORD_SIGNALS': True,
    
    # Recording Settings - Phase 3 (v0.5.0)
    'RECORD_JOBS': True,      # Background jobs (Celery, Django-Q, RQ, APScheduler)
    'RECORD_REDIS': True,     # Redis operations
    'RECORD_GATES': True,     # Permission/Gate checks
    
    # Recording Settings - Phase 4 (v0.6.0)
    'RECORD_TRANSACTIONS': True,  # Database transaction blocks
    'RECORD_STORAGE': True,       # File storage operations
    
    # Performance Settings
    'SLOW_QUERY_THRESHOLD_MS': 500,
    
    # Path Filtering
    'IGNORE_PATHS': [
        '/orbit/',
        '/static/',
        '/media/',
        '/admin/jsi18n/',
        '/favicon.ico',
    ],
    
    # Security Settings
    'HIDE_REQUEST_HEADERS': [
        'Authorization',
        'Cookie',
        'X-CSRFToken',
    ],
    'HIDE_REQUEST_BODY_KEYS': [
        'password',
        'token',
        'secret',
        'api_key',
        'apikey',
        'access_token',
        'refresh_token',
    ],
    'MAX_BODY_SIZE': 65536,
}
```

## Configuration Options

### Core Settings

#### `ENABLED`
- **Type**: `bool`
- **Default**: `True`
- **Description**: Enable or disable Orbit entirely

```python
# Disable in production
ORBIT_CONFIG = {
    'ENABLED': DEBUG,
}
```

#### `STORAGE_LIMIT`
- **Type**: `int`
- **Default**: `1000`
- **Description**: Maximum number of entries to keep in the database

Orbit automatically cleans up old entries when this limit is exceeded.

#### `AUTH_CHECK`
- **Type**: `callable` or `str` (dotted path to callable)
- **Default**: `None`
- **Description**: Function that controls dashboard access. Receives the `request` object and must return `True` (allow) or `False` (deny).

```python
# Using a lambda (recommended for simple checks)
ORBIT_CONFIG = {
    'AUTH_CHECK': lambda request: request.user.is_staff,
}

# Using a dotted path to a custom function
ORBIT_CONFIG = {
    'AUTH_CHECK': 'myapp.auth.can_access_orbit',
}
```

### Recording Settings

#### Core Watchers

| Option | Default | Description |
|--------|---------|-------------|
| `RECORD_REQUESTS` | `True` | HTTP request/response cycles |
| `RECORD_QUERIES` | `True` | SQL queries with N+1 detection |
| `RECORD_LOGS` | `True` | Python logging output |
| `RECORD_EXCEPTIONS` | `True` | Unhandled exceptions |
| `RECORD_DUMPS` | `True` | Debug dumps via `orbit.dump()` |

#### Extended Watchers

| Option | Default | Description |
|--------|---------|-------------|
| `RECORD_COMMANDS` | `True` | Django management commands |
| `RECORD_CACHE` | `True` | Cache operations (hits/misses) |
| `RECORD_MODELS` | `True` | ORM signals (post_save, post_delete) |
| `RECORD_HTTP_CLIENT` | `True` | Outgoing HTTP requests (httpx, requests) |
| `RECORD_MAIL` | `True` | Email sending via Django mail |
| `RECORD_SIGNALS` | `True` | Django signals |

#### Phase 3 Watchers (v0.5.0+)

| Option | Default | Description |
|--------|---------|-------------|
| `RECORD_JOBS` | `True` | Background jobs (Celery, Django-Q, RQ, APScheduler, django-celery-beat) |
| `RECORD_REDIS` | `True` | Redis operations (GET, SET, DEL, etc.) |
| `RECORD_GATES` | `True` | Permission/authorization checks |

#### Phase 4 Watchers (v0.6.0+)

| Option | Default | Description |
|--------|---------|-------------|
| `RECORD_TRANSACTIONS` | `True` | Database transaction blocks (`atomic()`) |
| `RECORD_STORAGE` | `True` | File storage operations (save, open, delete, exists) |

### Performance Settings

#### `SLOW_QUERY_THRESHOLD_MS`
- **Type**: `int`
- **Default**: `500`
- **Description**: Threshold in milliseconds for marking a query as "slow"

Queries exceeding this threshold are highlighted in the dashboard and stats.

### Path Filtering

#### `IGNORE_PATHS`
- **Type**: `list[str]`
- **Default**: `['/orbit/', '/static/', '/admin/jsi18n/', '/favicon.ico']`
- **Description**: URL path prefixes to ignore

Always include `/orbit/` to avoid infinite loops.

```python
ORBIT_CONFIG = {
    'IGNORE_PATHS': [
        '/orbit/',
        '/static/',
        '/media/',
        '/health/',
        '/metrics/',
        '/_internal/',
    ],
}
```

### Security Settings

#### `HIDE_REQUEST_HEADERS`
- **Type**: `list[str]`
- **Default**: `['Authorization', 'Cookie', 'X-CSRFToken']`
- **Description**: Request headers to mask in logs

Values are replaced with `***HIDDEN***`.

#### `HIDE_REQUEST_BODY_KEYS`
- **Type**: `list[str]`
- **Default**: `['password', 'token', 'secret', 'api_key']`
- **Description**: Request body keys to mask (case-insensitive)

Works recursively on nested objects.

#### `MAX_BODY_SIZE`
- **Type**: `int`
- **Default**: `65536` (64KB)
- **Description**: Maximum request body size to capture

## Environment-Based Configuration

```python
# settings/base.py
ORBIT_CONFIG = {
    'ENABLED': True,
    'STORAGE_LIMIT': 1000,
}

# settings/development.py
ORBIT_CONFIG = {
    **ORBIT_CONFIG,
    'SLOW_QUERY_THRESHOLD_MS': 100,  # Stricter in dev
}

# settings/production.py
ORBIT_CONFIG = {
    **ORBIT_CONFIG,
    'ENABLED': False,  # Disabled in production
}
```

## Next Steps

- [Dashboard Guide](dashboard.md)
- [Stats Dashboard](stats.md)
- [Security Best Practices](security.md)
