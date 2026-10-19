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

## Content Security Policy

The dashboard is compatible with a strict Content Security Policy. All of its
assets are same-origin (served from Orbit's package static files, see
[Installation](installation.md)), the templates contain no executable inline
scripts, inline event handlers, inline `<style>` blocks or `style` attributes,
and server data reaches JavaScript only through `json_script` blocks (data, not
code) and `data-*` attributes.

Orbit renders `nonce="..."` on its own `<script>` and `<link rel="stylesheet">`
tags when the request has a CSP nonce, from either:

- Django 6.0+ built-in CSP (`django.middleware.csp.ContentSecurityPolicyMiddleware`
  with `CSP.NONCE` in `SECURE_CSP`), or
- [django-csp](https://django-csp.readthedocs.io/) (`request.csp_nonce`).

Without CSP, or on Django 5.2 (which has no built-in CSP), no attribute is
rendered. The template tags `{% orbit_nonce %}` and `{% orbit_nonce_attr %}`
(`{% load orbit_tags %}`) are available if you extend Orbit's templates.

### Directives the dashboard needs

Verified in Chromium with Django 6.1's middleware (no violations reported on the
dashboard, detail panel, mail preview, stats and health pages):

```python
# settings.py (Django 6.0+)
from django.utils.csp import CSP

SECURE_CSP = {
    "default-src": [CSP.NONE],
    "script-src": [CSP.SELF, CSP.NONCE, CSP.UNSAFE_EVAL],
    "style-src": [CSP.SELF, CSP.NONCE],
    "font-src": [CSP.SELF],
    "connect-src": [CSP.SELF],
    "img-src": [CSP.SELF],
    "base-uri": [CSP.NONE],
    "form-action": [CSP.SELF],
}
```

| Directive | Why |
| --- | --- |
| `script-src 'self'` | htmx, Alpine.js, Lucide, ApexCharts and Orbit's scripts are static files. `'nonce-...'` is only needed instead of `'self'` for nonce-only policies. |
| `script-src 'unsafe-eval'` | See the limitation below. |
| `style-src 'self'` | Compiled `orbit.css`; Orbit sets no inline styles. Alpine and Orbit change styles through the DOM API, which CSP allows. |
| `font-src 'self'` | Self-hosted Inter and JetBrains Mono. |
| `connect-src 'self'` | The feed, detail panel and handoff requests use `fetch`/htmx against Orbit's own URLs. |
| `img-src 'self'` | Icons are inline SVG. The mail HTML preview is a sandboxed `srcdoc` iframe that inherits this policy, so remote images in previewed emails are blocked. |

!!! warning "Alpine.js requires `'unsafe-eval'`"
    Orbit uses the standard Alpine.js build, which evaluates `x-data`, `@click`
    and similar expressions with the `Function` constructor. Under a policy
    without `'unsafe-eval'` the dashboard's interactive parts (feed, filters,
    detail panel) do not initialise. htmx is configured with `allowEval: false`
    and does not need it.

    Moving to the [Alpine CSP build](https://alpinejs.dev/advanced/csp) would
    remove this requirement but means rewriting the inline expressions as
    registered components. That is a possible future step and is not done yet.
    Because the policy applies host-wide, consider granting `'unsafe-eval'` only
    to Orbit's URLs (for example with Django's `csp_override` decorator on the
    included views or a small middleware) rather than to your whole site. Orbit is
    a development tool, so this is the recommended place to relax it.

## Reporting Security Issues

If you discover a security vulnerability, please email us directly instead of opening a public issue.

---

*Stay secure! 🔒*
