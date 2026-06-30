"""
Database adapter serialization/replay helpers for Orbit.

Django can adapt Python values into driver-level wrapper objects before they
reach ``connection.execute_wrapper()``. JSONField values on PostgreSQL are the
important case: a dict may arrive as psycopg/psycopg2 Json/Jsonb. Orbit stores a
small JSON-safe marker for supported wrappers and later rebinds that marker with
Django's active connection operations before running on-demand EXPLAIN.
"""

from __future__ import annotations

import json as _json
from collections.abc import Mapping
from typing import Any, Dict, Optional

ADAPTER_MARKER_KEY = "__orbit_adapter__"
_MISSING = object()


def _detect_json(value: Any) -> bool:
    """Return True if value is a recognized psycopg JSON/JSONB adapter."""
    module = getattr(type(value), "__module__", "") or ""
    if not module.startswith("psycopg"):
        return False
    return type(value).__name__ in ("Json", "Jsonb")


def _unwrap_json(value: Any) -> Optional[Dict[str, Any]]:
    """Extract the inner Python object from a psycopg Json/Jsonb wrapper."""
    for attr in ("obj", "adapted", "_obj", "wrapped"):
        try:
            inner = getattr(value, attr, _MISSING)
        except Exception:
            continue
        if inner is _MISSING:
            continue
        if inner is None or isinstance(
            inner, (dict, list, tuple, str, int, float, bool)
        ):
            return {ADAPTER_MARKER_KEY: "json", "value": unwrap_adapters(inner)}
    return None


def _connection_vendor(connection_or_vendor: Any) -> str:
    return str(getattr(connection_or_vendor, "vendor", connection_or_vendor) or "")


def _adapt_json_with_connection(inner: Any, connection_or_vendor: Any) -> Any:
    ops = getattr(connection_or_vendor, "ops", None)
    adapter = getattr(ops, "adapt_json_value", None)
    if adapter is not None:
        try:
            return adapter(inner, encoder=None)
        except TypeError:
            try:
                return adapter(inner)
            except Exception:
                pass
        except Exception:
            pass

    vendor = _connection_vendor(connection_or_vendor)
    if vendor == "postgresql":
        try:
            from psycopg2.extras import Json  # type: ignore[import]

            return Json(inner)
        except Exception:
            pass
    return _json.dumps(inner)


def _rebind_json(marker: Dict[str, Any], connection_or_vendor: Any) -> Any:
    return _adapt_json_with_connection(marker.get("value"), connection_or_vendor)


_REGISTRY: Dict[str, tuple] = {
    "json": (_detect_json, _unwrap_json, _rebind_json),
}


def is_supported_adapter(value: Any) -> Optional[str]:
    """Return the adapter kind string if value is recognized, otherwise None."""
    for kind, (detect, _unwrap, _rebind) in _REGISTRY.items():
        try:
            if detect(value):
                return kind
        except Exception:
            pass
    return None


def unwrap_adapter(value: Any) -> Any:
    """Return an Orbit adapter marker for a recognized adapter, else value."""
    kind = is_supported_adapter(value)
    if kind is None:
        return value

    _detect, unwrap_fn, _rebind = _REGISTRY[kind]
    try:
        result = unwrap_fn(value)
    except Exception:
        result = None
    return result if result is not None else value


def unwrap_adapters(value: Any) -> Any:
    """Recursively unwrap supported adapter objects without mutating input."""
    unwrapped = unwrap_adapter(value)
    if unwrapped is not value:
        return unwrapped
    if isinstance(value, Mapping):
        return {key: unwrap_adapters(child) for key, child in value.items()}
    if isinstance(value, tuple):
        return tuple(unwrap_adapters(child) for child in value)
    if isinstance(value, list):
        return [unwrap_adapters(child) for child in value]
    return value


def is_adapter_marker(value: Any) -> bool:
    """Return True if value is an Orbit adapter marker dict."""
    return isinstance(value, dict) and isinstance(value.get(ADAPTER_MARKER_KEY), str)


def rebind_adapter(marker: Dict[str, Any], connection_or_vendor: Any) -> Any:
    """Reconstruct a bindable value from an Orbit adapter marker."""
    kind = marker.get(ADAPTER_MARKER_KEY)
    if kind not in _REGISTRY:
        return marker.get("value")

    _detect, _unwrap, rebind_fn = _REGISTRY[kind]
    try:
        return rebind_fn(marker, connection_or_vendor)
    except Exception:
        return marker.get("value")


def rebind_params(params: Any, connection_or_vendor: Any) -> Any:
    """Recursively rebind Orbit adapter markers without mutating params."""
    if is_adapter_marker(params):
        return rebind_adapter(params, connection_or_vendor)
    if isinstance(params, Mapping):
        return {
            key: rebind_params(value, connection_or_vendor)
            for key, value in params.items()
        }
    if isinstance(params, tuple):
        return tuple(rebind_params(value, connection_or_vendor) for value in params)
    if isinstance(params, list):
        return [rebind_params(value, connection_or_vendor) for value in params]
    return params


def _looks_like_legacy_adapter_repr(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(("Jsonb(", "Json("))


def _has_unbindable_param(value: Any, depth: int = 0) -> bool:
    if is_adapter_marker(value):
        return False
    if _looks_like_legacy_adapter_repr(value):
        return True
    if isinstance(value, Mapping):
        if depth > 0:
            return True
        return any(_has_unbindable_param(child, depth + 1) for child in value.values())
    if isinstance(value, tuple):
        return any(_has_unbindable_param(child, depth + 1) for child in value)
    if isinstance(value, list):
        if depth > 0 and not all(isinstance(child, (list, tuple)) for child in value):
            return True
        return any(_has_unbindable_param(child, depth + 1) for child in value)
    return False


def has_unbindable_param(params: Any) -> bool:
    """Return True when params contain legacy JSON values that cannot rebind."""
    return _has_unbindable_param(params, depth=0)
