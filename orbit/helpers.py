"""
Django Orbit Helpers

User-facing utilities for manual logging and debugging.
"""

import inspect
import traceback
from typing import Any, Optional

from orbit.conf import get_config


def dump(*args, **kwargs) -> None:
    """
    Record values to Orbit for debugging inspection.

    Similar to Laravel Telescope's dump() function.
    Can be called anywhere in your code to capture variable values.

    Usage:
        from orbit import dump

        dump(user)                    # Single value
        dump(user, request, order)    # Multiple values
        dump(user=user, cart=cart)    # Named values
        dump("Processing order", order_id=123)  # Mixed

    Args:
        *args: Values to dump
        **kwargs: Named values to dump

    Example:
        # In your view
        def checkout(request):
            cart = get_cart(request)
            dump(cart, user=request.user)  # Captured to Orbit
            ...
    """
    config = get_config()
    if not config.get("ENABLED", True):
        return

    if not config.get("RECORD_DUMPS", True):
        return

    from orbit.models import OrbitEntry

    # Get caller info
    frame = inspect.currentframe()
    caller_frame = frame.f_back if frame else None

    caller_info = {}
    if caller_frame:
        caller_info = {
            "filename": caller_frame.f_code.co_filename,
            "lineno": caller_frame.f_lineno,
            "function": caller_frame.f_code.co_name,
        }
        # Get the source line if possible
        try:
            import linecache

            line = linecache.getline(caller_info["filename"], caller_info["lineno"])
            caller_info["line"] = line.strip()
        except Exception:
            pass

    # Serialize values
    values = []

    for i, arg in enumerate(args):
        values.append(
            {
                "name": f"arg_{i}" if len(args) > 1 else "value",
                "value": _serialize_value(arg),
                "type": type(arg).__name__,
            }
        )

    for key, value in kwargs.items():
        values.append(
            {
                "name": key,
                "value": _serialize_value(value),
                "type": type(value).__name__,
            }
        )

    payload = {
        "values": values,
        "caller": caller_info,
        "count": len(values),
    }

    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_DUMP if hasattr(OrbitEntry, "TYPE_DUMP") else "dump",
        payload=payload,
    )


def _serialize_value(value: Any, max_depth: int = 3, max_items: int = 50) -> Any:
    """
    Serialize a value for JSON storage.
    Handles common Python types and Django models.
    """
    if max_depth <= 0:
        return f"<{type(value).__name__}...>"

    # Primitives
    if value is None or isinstance(value, (bool, int, float, str)):
        if isinstance(value, str) and len(value) > 500:
            return value[:500] + "..."
        return value

    # Lists/tuples
    if isinstance(value, (list, tuple)):
        items = [_serialize_value(v, max_depth - 1) for v in value[:max_items]]
        if len(value) > max_items:
            items.append(f"... ({len(value) - max_items} more)")
        return items

    # Dicts
    if isinstance(value, dict):
        result = {}
        for i, (k, v) in enumerate(value.items()):
            if i >= max_items:
                result["..."] = f"{len(value) - max_items} more items"
                break
            result[str(k)] = _serialize_value(v, max_depth - 1)
        return result

    # Sets
    if isinstance(value, (set, frozenset)):
        return list(value)[:max_items]

    # Django QuerySet
    if hasattr(value, "model") and hasattr(value, "query"):
        return {
            "__type__": "QuerySet",
            "model": str(value.model._meta.label),
            "count": value.count() if hasattr(value, "count") else "?",
            "query": str(value.query)[:500],
        }

    # Django Model instance
    if hasattr(value, "_meta") and hasattr(value._meta, "model_name"):
        result = {
            "__type__": "Model",
            "model": value._meta.label,
            "pk": str(value.pk) if value.pk else None,
        }
        # Add some field values
        for field in value._meta.fields[:10]:
            try:
                field_value = getattr(value, field.name)
                result[field.name] = _serialize_value(field_value, max_depth - 1)
            except Exception:
                result[field.name] = "<error>"
        return result

    # Request object
    if hasattr(value, "method") and hasattr(value, "path") and hasattr(value, "user"):
        return {
            "__type__": "HttpRequest",
            "method": value.method,
            "path": value.path,
            "user": str(value.user),
        }

    # Default: try repr or str
    try:
        repr_str = repr(value)
        if len(repr_str) > 200:
            repr_str = repr_str[:200] + "..."
        return {
            "__type__": type(value).__name__,
            "__repr__": repr_str,
        }
    except Exception:
        return f"<{type(value).__name__}>"


def log(message: str, level: str = "INFO", **context) -> None:
    """
    Log a message to Orbit.

    Simpler than Python's logging - goes directly to Orbit.

    Usage:
        from orbit import log

        log("User logged in", user_id=123)
        log("Payment processed", level="INFO", amount=99.99)
        log("Something went wrong", level="ERROR", error=str(e))
    """
    config = get_config()
    if not config.get("ENABLED", True):
        return

    from orbit.models import OrbitEntry

    # Get caller info
    frame = inspect.currentframe()
    caller_frame = frame.f_back if frame else None

    caller_info = {}
    if caller_frame:
        caller_info = {
            "filename": caller_frame.f_code.co_filename,
            "lineno": caller_frame.f_lineno,
            "function": caller_frame.f_code.co_name,
        }

    payload = {
        "level": level.upper(),
        "message": message,
        "context": context,
        "logger": caller_info.get("function", "orbit"),
        "caller": caller_info,
    }

    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_LOG,
        payload=payload,
    )
