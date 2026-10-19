"""
Django Orbit Template Tags
"""

from django import template
from django.utils.html import format_html

register = template.Library()


def _resolve_csp_nonce(context):
    """
    Return the current request's Content Security Policy nonce, or "".

    Supported sources, in order:

    1. Django 6.0+ built-in CSP
       (``django.middleware.csp.ContentSecurityPolicyMiddleware``), read through
       ``django.middleware.csp.get_nonce``.
    2. django-csp, which exposes ``request.csp_nonce``.
    3. A ``csp_nonce`` template variable (Django's or django-csp's context
       processor), for hosts that render Orbit with those processors.

    Never raises: without CSP (including on Django 5.2, which has no CSP
    support) the result is an empty string and no attribute is rendered.
    """
    try:
        request = getattr(context, "request", None) or context.get("request")
        candidates = []
        if request is not None:
            try:
                from django.middleware.csp import get_nonce
            except ImportError:  # Django < 6.0
                get_nonce = None
            if get_nonce is not None:
                candidates.append(get_nonce(request))
            candidates.append(getattr(request, "csp_nonce", None))
        candidates.append(context.get("csp_nonce"))
        for candidate in candidates:
            # str() forces lazy nonces to be generated, which also tells the
            # CSP middleware to add 'nonce-...' to the response header.
            if candidate is not None and (value := str(candidate)):
                return value
    except Exception:
        pass
    return ""


@register.simple_tag(takes_context=True)
def orbit_nonce(context):
    """
    Output the request's CSP nonce value (empty when there is none).

    Usage: <script nonce="{% orbit_nonce %}">
    """
    return _resolve_csp_nonce(context)


@register.simple_tag(takes_context=True)
def orbit_nonce_attr(context):
    """
    Output ``nonce="..."`` when the request has a CSP nonce, otherwise nothing.

    Usage: <script src="..." {% orbit_nonce_attr %}></script>
    """
    nonce = _resolve_csp_nonce(context)
    return format_html('nonce="{}"', nonce) if nonce else ""


@register.filter
def get_item(dictionary, key):
    """
    Get an item from a dictionary using bracket notation in templates.

    Usage: {{ mydict|get_item:key }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)


@register.filter
def status_class(status_code):
    """
    Return a CSS class based on HTTP status code.
    """
    if status_code is None:
        return "text-slate-400"

    status_code = int(status_code)

    if status_code >= 500:
        return "text-rose-400"
    elif status_code >= 400:
        return "text-amber-400"
    elif status_code >= 300:
        return "text-blue-400"
    else:
        return "text-emerald-400"


@register.filter
def level_class(level):
    """
    Return a CSS class based on log level.
    """
    level_classes = {
        "DEBUG": "text-slate-400",
        "INFO": "text-cyan-400",
        "WARNING": "text-amber-400",
        "ERROR": "text-rose-400",
        "CRITICAL": "text-rose-500",
    }
    return level_classes.get(level, "text-slate-400")


@register.filter
def duration_class(duration_ms):
    """
    Return a CSS class based on duration.
    """
    if duration_ms is None:
        return "text-slate-400"

    if duration_ms > 500:
        return "text-rose-400"
    elif duration_ms > 100:
        return "text-amber-400"
    else:
        return "text-slate-400"


@register.simple_tag
def type_icon(entry_type):
    """
    Return the Lucide icon name for an entry type.

    Delegates to OrbitEntry.TYPE_ICONS so the dashboard, feed and sidebar all
    share one source of truth for every entry type.
    """
    from orbit.models import OrbitEntry

    return OrbitEntry.TYPE_ICONS.get(entry_type, "circle")


@register.simple_tag
def type_color(entry_type):
    """
    Return the color name for an entry type (single source of truth in the model).
    """
    from orbit.models import OrbitEntry

    return OrbitEntry.TYPE_COLORS.get(entry_type, "slate")
