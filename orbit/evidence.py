"""
Versioned, metadata-first access to normalized Orbit evidence.

This module is the public read boundary for integrations. It intentionally
returns plain dictionaries instead of ORM objects and never includes raw
payloads, summaries, tags, SQL, messages, headers, bodies, or tracebacks.
"""

from __future__ import annotations

import logging
import math
from typing import Any
from urllib.parse import urlsplit

from orbit.backends import get_storage_db_alias
from orbit.models import OrbitEntry
from orbit.watchers import _table_exists, cachalot_disabled

logger = logging.getLogger(__name__)

EVIDENCE_SCHEMA_VERSION = "orbit.evidence.v1"
DEFAULT_FAMILY_LIMIT = 1000
MAX_FAMILY_LIMIT = 5000
MAX_STRING_CHARS = 255
MAX_PATH_CHARS = 2048

_REQUIRED_ATTRIBUTES = {
    OrbitEntry.TYPE_REQUEST: (
        "method",
        "path",
        "status_code",
        "query_count",
        "duplicate_query_count",
        "had_exception",
    ),
    OrbitEntry.TYPE_QUERY: (
        "is_slow",
        "is_duplicate",
        "duplicate_count",
        "database",
    ),
    OrbitEntry.TYPE_EXCEPTION: (
        "exception_type",
        "request_method",
        "request_path",
    ),
}

_REASON_ACTIONS = {
    "family_not_found": ("verify_family_hash", "verify_capture_and_retention"),
    "storage_unavailable": ("verify_migrations_and_storage",),
    "read_failed": ("retry_read", "inspect_server_logs"),
}

__all__ = [
    "DEFAULT_FAMILY_LIMIT",
    "EVIDENCE_SCHEMA_VERSION",
    "MAX_FAMILY_LIMIT",
    "read_family_evidence",
    "serialize_entry",
]


def _bounded_string(
    value: Any,
    field: str,
    truncated_fields: list[str],
    *,
    max_chars: int = MAX_STRING_CHARS,
) -> str | None:
    if not isinstance(value, str):
        return None
    if len(value) <= max_chars:
        return value
    truncated_fields.append(field)
    return value[:max_chars]


def _path_string(
    value: Any,
    field: str,
    truncated_fields: list[str],
) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        path = urlsplit(value).path
    except ValueError:
        return None
    if not path:
        return None
    return _bounded_string(
        path,
        field,
        truncated_fields,
        max_chars=MAX_PATH_CHARS,
    )


def _bounded_identifier(
    value: Any,
    field: str,
    truncated_fields: list[str],
) -> str | None:
    if not isinstance(value, str) or not value or not value.isprintable():
        return None
    if any(character.isspace() for character in value):
        return None
    if len(value) > 64:
        truncated_fields.append(field)
        return value[:64]
    return value


def _safe_family_hash(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    if (
        not value
        or len(value) > 64
        or not value.isprintable()
        or any(character.isspace() for character in value)
    ):
        return None
    return value


def _non_negative_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _strict_bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _finite_number(value: Any) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value if math.isfinite(value) else None


def _request_attributes(
    payload: dict[str, Any], truncated_fields: list[str]
) -> dict[str, Any]:
    return {
        "method": _bounded_string(
            payload.get("method"), "attributes.method", truncated_fields
        ),
        "path": _path_string(payload.get("path"), "attributes.path", truncated_fields),
        "status_code": _non_negative_int(payload.get("status_code")),
        "query_count": _non_negative_int(payload.get("query_count")),
        "duplicate_query_count": _non_negative_int(
            payload.get("duplicate_query_count")
        ),
        "had_exception": _strict_bool(payload.get("had_exception")),
    }


def _query_attributes(
    payload: dict[str, Any], truncated_fields: list[str]
) -> dict[str, Any]:
    return {
        "is_slow": _strict_bool(payload.get("is_slow")),
        "is_duplicate": _strict_bool(payload.get("is_duplicate")),
        "duplicate_count": _non_negative_int(payload.get("duplicate_count")),
        "database": _bounded_string(
            payload.get("database"), "attributes.database", truncated_fields
        ),
    }


def _exception_attributes(
    payload: dict[str, Any], truncated_fields: list[str]
) -> dict[str, Any]:
    return {
        "exception_type": _bounded_string(
            payload.get("exception_type"),
            "attributes.exception_type",
            truncated_fields,
        ),
        "request_method": _bounded_string(
            payload.get("request_method"),
            "attributes.request_method",
            truncated_fields,
        ),
        "request_path": _path_string(
            payload.get("request_path"),
            "attributes.request_path",
            truncated_fields,
        ),
    }


def serialize_entry(entry: OrbitEntry) -> dict[str, Any]:
    """
    Normalize one Orbit entry into the stable ``orbit.evidence.v1`` schema.

    Missing or malformed values remain ``None`` so consumers cannot interpret
    absent evidence as a successful zero value.
    """
    payload = entry.payload if isinstance(entry.payload, dict) else {}
    truncated_fields: list[str] = []

    if entry.type == OrbitEntry.TYPE_REQUEST:
        attributes = _request_attributes(payload, truncated_fields)
    elif entry.type == OrbitEntry.TYPE_QUERY:
        attributes = _query_attributes(payload, truncated_fields)
    elif entry.type == OrbitEntry.TYPE_EXCEPTION:
        attributes = _exception_attributes(payload, truncated_fields)
    else:
        attributes = {}

    return {
        "id": str(entry.id),
        "type": entry.type,
        "family_hash": _bounded_identifier(
            entry.family_hash, "family_hash", truncated_fields
        ),
        "fingerprint": _bounded_identifier(
            entry.fingerprint, "fingerprint", truncated_fields
        ),
        "created_at": (
            entry.created_at.isoformat()
            if getattr(entry, "created_at", None) is not None
            else None
        ),
        "duration_ms": _finite_number(entry.duration_ms),
        "attributes": attributes,
        "truncated_fields": truncated_fields,
    }


def _action(code: str, **parameters: Any) -> dict[str, Any]:
    return {"code": code, "parameters": parameters}


def _incident_bundle_action(family_hash: str, reason: str) -> dict[str, Any]:
    return _action(
        "call_mcp_tool",
        tool="create_incident_bundle",
        arguments={
            "source_type": "family_hash",
            "source_value": family_hash,
            "format": "json",
        },
        reason=reason,
    )


def _unavailable_quality(reason: str | None) -> dict[str, Any]:
    if reason == "invalid_family_hash":
        next_actions = [_action("provide_valid_family_hash", max_chars=64)]
    elif reason == "invalid_limit":
        next_actions = [
            _action(
                "use_valid_limit",
                minimum=1,
                maximum=MAX_FAMILY_LIMIT,
                default=DEFAULT_FAMILY_LIMIT,
            )
        ]
    else:
        next_actions = [
            _action(action_code) for action_code in _REASON_ACTIONS.get(reason, ())
        ]
    next_actions.append(_action("do_not_conclude_absence"))
    return {
        "status": "unavailable",
        "warnings": [reason] if reason else [],
        "missing_fields": [],
        "truncated_fields": [],
        "unsupported_entry_types": [],
        "next_actions": next_actions,
    }


def _evidence_quality(
    family_hash: str,
    entries: list[dict[str, Any]],
    *,
    truncated: bool,
    limit: int,
) -> dict[str, Any]:
    warnings: list[str] = []
    missing_fields: list[str] = []
    truncated_fields: list[str] = []
    unsupported_entry_types: list[str] = []
    next_actions: list[dict[str, Any]] = []

    if truncated:
        warnings.append("family_truncated")
        if limit < MAX_FAMILY_LIMIT:
            next_limit = min(MAX_FAMILY_LIMIT, max(limit + 1, limit * 2))
            next_actions.append(_action("retry_with_higher_limit", limit=next_limit))
        else:
            next_actions.append(
                _incident_bundle_action(family_hash, "family_truncated")
            )

    for entry in entries:
        entry_type = entry["type"]
        attributes = entry["attributes"]
        required_attributes = _REQUIRED_ATTRIBUTES.get(entry_type)
        if required_attributes is None:
            unsupported_entry_types.append(entry_type)
        else:
            for field in required_attributes:
                if attributes.get(field) is None:
                    missing_fields.append(f"{entry_type}.attributes.{field}")
            if entry_type == OrbitEntry.TYPE_EXCEPTION and entry["fingerprint"] is None:
                missing_fields.append("exception.fingerprint")
        for field in entry["truncated_fields"]:
            truncated_fields.append(f"{entry_type}.{field}")

    missing_fields = sorted(set(missing_fields))
    truncated_fields = sorted(set(truncated_fields))
    unsupported_entry_types = sorted(set(unsupported_entry_types))

    if missing_fields:
        warnings.append("missing_fields")
        next_actions.append(_action("review_missing_fields", fields=missing_fields))
    if truncated_fields:
        warnings.append("truncated_fields")
        next_actions.append(_action("review_truncated_fields", fields=truncated_fields))
    if unsupported_entry_types:
        warnings.append("unsupported_entry_types")
        next_actions.append(
            _incident_bundle_action(family_hash, "unsupported_entry_types")
        )

    if warnings:
        next_actions.append(_action("do_not_conclude_absence"))

    return {
        "status": "partial" if warnings else "complete",
        "warnings": warnings,
        "missing_fields": missing_fields,
        "truncated_fields": truncated_fields,
        "unsupported_entry_types": unsupported_entry_types,
        "next_actions": next_actions,
    }


def _envelope(
    family_hash: Any,
    *,
    status: str,
    reason: str | None,
    entries: list[dict[str, Any]] | None = None,
    truncated: bool = False,
    limit: int = DEFAULT_FAMILY_LIMIT,
) -> dict[str, Any]:
    safe_entries = entries or []
    quality = (
        _evidence_quality(
            _safe_family_hash(family_hash),
            safe_entries,
            truncated=truncated,
            limit=limit,
        )
        if status == "ok"
        else _unavailable_quality(reason)
    )
    return {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "status": status,
        "reason": reason,
        "family_hash": _safe_family_hash(family_hash),
        "count": len(safe_entries),
        "truncated": truncated,
        "evidence_quality": quality,
        "entries": safe_entries,
    }


def read_family_evidence(
    family_hash: str,
    *,
    limit: int = DEFAULT_FAMILY_LIMIT,
) -> dict[str, Any]:
    """
    Read one request family through a deterministic, fail-silent adapter.

    The function performs no writes. Storage and ORM failures return a stable
    ``unavailable`` envelope rather than propagating into the host application.
    """
    if _safe_family_hash(family_hash) is None:
        return _envelope(
            family_hash,
            status="invalid",
            reason="invalid_family_hash",
            limit=limit,
        )
    if (
        isinstance(limit, bool)
        or not isinstance(limit, int)
        or not 1 <= limit <= MAX_FAMILY_LIMIT
    ):
        return _envelope(
            family_hash,
            status="invalid",
            reason="invalid_limit",
            limit=DEFAULT_FAMILY_LIMIT,
        )
    if not _table_exists():
        return _envelope(
            family_hash,
            status="unavailable",
            reason="storage_unavailable",
            limit=limit,
        )

    try:
        alias = get_storage_db_alias()
        queryset = (
            OrbitEntry.objects.using(alias)
            .filter(family_hash=family_hash)
            .order_by("created_at", "id")[: limit + 1]
        )
        with cachalot_disabled():
            records = list(queryset)
    except Exception:
        logger.warning("Django Orbit evidence read failed.")
        return _envelope(
            family_hash,
            status="unavailable",
            reason="read_failed",
            limit=limit,
        )

    if not records:
        return _envelope(
            family_hash,
            status="not_found",
            reason="family_not_found",
            limit=limit,
        )

    truncated = len(records) > limit
    entries = [serialize_entry(entry) for entry in records[:limit]]
    return _envelope(
        family_hash,
        status="ok",
        reason=None,
        entries=entries,
        truncated=truncated,
        limit=limit,
    )
