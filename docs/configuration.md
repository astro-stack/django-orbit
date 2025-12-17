# Configuration Reference

Django Orbit is configured through the `ORBIT_CONFIG` dictionary in your Django settings.

## Full Configuration

```python
# settings.py

ORBIT_CONFIG = {
    # Core Settings
    'ENABLED': True,
    # Authentication check (callable or path to function)
    'AUTH_CHECK': None,
    'STORAGE_LIMIT': 1000,
    
    
    # Recording Settings
    'RECORD_REQUESTS': True,
    'RECORD_QUERIES': True,
    'RECORD_LOGS': True,
    'RECORD_EXCEPTIONS': True,
    'RECORD_DUMPS': True,
    
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

### Recording Settings

#### `RECORD_REQUESTS`
- **Type**: `bool`
- **Default**: `True`
- **Description**: Record HTTP request/response cycles

#### `RECORD_QUERIES`
- **Type**: `bool`
- **Default**: `True`
- **Description**: Record SQL queries

#### `RECORD_LOGS`
- **Type**: `bool`
- **Default**: `True`
- **Description**: Capture Python logging output

    
#### `RECORD_EXCEPTIONS`
- **Type**: `bool`
- **Default**: `True`
- **Description**: Capture unhandled exceptions

#### `RECORD_DUMPS`
- **Type**: `bool`
- **Default**: `True`
- **Description**: Capture debug dumps from `orbit.dump()`

### Performance Settings

#### `SLOW_QUERY_THRESHOLD_MS`
- **Type**: `int`
- **Default**: `500`
- **Description**: Threshold in milliseconds for marking a query as "slow"

Queries exceeding this threshold are highlighted in the dashboard.

### Path Filtering

#### `IGNORE_PATHS`
- **Type**: `list[str]`
- **Default**: `['/orbit/', '/static/', '/admin/jsi18n/', '/favicon.ico']`
- **Description**: URL path prefixes to ignore

Requests to these paths are not recorded. Always include `/orbit/` to avoid infinite loops.

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

Larger bodies are replaced with a placeholder message.

## Environment-Based Configuration

You can configure Orbit differently per environment:

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

## Programmatic Configuration

You can also modify configuration at runtime:

```python
from orbit.conf import get_config

# Read current config
config = get_config()
print(config['SLOW_QUERY_THRESHOLD_MS'])

# Note: Runtime changes should modify Django settings directly
from django.conf import settings
settings.ORBIT_CONFIG['ENABLED'] = False
```

## Next Steps

- [Dashboard Guide](dashboard.md)
- [Security Best Practices](security.md)
