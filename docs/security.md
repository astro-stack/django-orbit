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

Use Django's authentication to protect the dashboard:

```python
# urls.py
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import path, include

urlpatterns = [
    path('orbit/', staff_member_required(include('orbit.urls'))),
]
```

### 3. Sensitive Data

Be careful with sensitive data in:
- Request headers (authentication tokens)
- Request bodies (passwords, PII)
- SQL queries (personal data)

## Reporting Security Issues

If you discover a security vulnerability, please email us directly instead of opening a public issue.

---

*Stay secure! 🔒*
