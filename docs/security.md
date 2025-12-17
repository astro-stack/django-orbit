# Security

!!! warning "Development Only"
    Django Orbit is designed for **development and debugging purposes**. Do not use it in production without proper security measures.

## Best Practices

### 1. Disable in Production

```python
# settings.py
ORBIT = {
    'ENABLED': DEBUG,  # Only enable when DEBUG=True
}
```

### 2. Restrict Access

Orbit v0.3.0+ includes built-in support for access control via configuration.

```python
# settings.py
ORBIT_CONFIG = {
    'ENABLED': True,
    # Callable that takes 'request' and returns True/False
    'AUTH_CHECK': lambda request: request.user.is_staff,
    # Or for simple uses:
    # 'AUTH_CHECK': 'orbit.utils.is_superuser', 
}
```

This is safer and easier than wrapping URLs manually.

### 3. Sensitive Data

Be careful with sensitive data in:
- Request headers (authentication tokens)
- Request bodies (passwords, PII)
- SQL queries (personal data)

## Reporting Security Issues

If you discover a security vulnerability, please email us directly instead of opening a public issue.

---

*Stay secure! 🔒*
