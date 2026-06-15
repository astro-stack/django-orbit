"""
Django Orbit Template Tags
"""

from django import template

register = template.Library()


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
