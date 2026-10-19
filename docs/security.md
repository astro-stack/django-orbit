# Security

## Agent Export Boundaries

`MCP_INCLUDE_PAYLOADS=False` omits payloads and derived free-text summaries,
tags and query-analysis SQL previews from agent serializers and incident bundles.
It does not anonymize identifiers, endpoint paths or other operational context.
Explicit per-call payload inclusion cannot override a disabled configuration.

Payload-enabled exports mask configured sensitive keys, not arbitrary secrets
inside messages or SQL literals. Bundle reports expose policy coverage and an
unknown residual risk; they do not certify universal redaction. Review the
exact handoff before sharing it with a coding agent.

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
    'AUTH_CHECK': lambda request: request.user.is_staff,
    # Or strict superuser check:
    # 'AUTH_CHECK': lambda request: request.user.is_superuser, 
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
