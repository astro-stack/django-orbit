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

### Evidence API Safety

`orbit.evidence.v1` is metadata-first and omits raw payloads, summaries, tags,
SQL, parameters, request headers and bodies, exception messages, tracebacks,
and logs.

The remaining metadata can still reveal endpoint paths, exception class names,
database aliases, timestamps, IDs, and fingerprints. Treat the output as
sensitive debugging data and restrict access accordingly.

A top-level status other than `ok`, `evidence_quality.status` other than
`complete`, `truncated: true`, `null` measurements, or nonempty
`truncated_fields` indicate incomplete evidence. Automated tools and coding
agents must follow `evidence_quality.next_actions` and must not interpret
missing evidence as a successful check.

See [Evidence API](evidence-api.md) for the complete contract.

## Reporting Security Issues

If you discover a security vulnerability, please email us directly instead of opening a public issue.

---

*Stay secure! 🔒*
