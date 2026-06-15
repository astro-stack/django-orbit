# Customization

Use customization to tune what Orbit records and how visible it is in your environment.

## Common Patterns

### Reduce noise

```python
# settings.py
ORBIT_CONFIG = {
    "ENABLED": True,
    "RECORD_QUERIES": True,
    "RECORD_LOGS": True,
    "IGNORE_PATHS": [
        "/orbit/",
        "/health/",
        "/metrics/",
        "/static/",
    ],
    "SLOW_QUERY_THRESHOLD_MS": 100,
}
```

### Restrict dashboard access

```python
ORBIT_CONFIG = {
    "AUTH_CHECK": lambda request: request.user.is_staff,
}
```

### Disable expensive watchers

```python
ORBIT_CONFIG = {
    "RECORD_HTTP_CLIENT": False,
    "RECORD_STORAGE": False,
    "RECORD_JOBS": False,
}
```

### Route telemetry to a separate database

```python
ORBIT_CONFIG = {
    "STORAGE_BACKEND": "orbit.backends.django_db.DjangoDBBackend",
    "STORAGE_DB_ALIAS": "orbit",
}
```

### Keep Orbit disabled outside development

```python
ORBIT_CONFIG = {
    "ENABLED": DEBUG,
}
```

## When To Customize

- Tighten `AUTH_CHECK` before sharing a staging environment.
- Lower `SLOW_QUERY_THRESHOLD_MS` when profiling local performance issues.
- Expand `IGNORE_PATHS` for health checks, metrics, and internal endpoints.
- Disable watchers selectively if you are debugging overhead or isolating an issue.

## Next Steps

- [Configuration Reference](configuration.md)
- [Security](security.md)
- [Storage Backends](storage-backends.md)
