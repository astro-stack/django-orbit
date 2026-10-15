"""Compact request context derived exclusively from the public Evidence API."""

from __future__ import annotations

from collections import Counter
from typing import Any

from orbit import evidence
from orbit.conf import get_config


def _event_cap() -> int:
    configured = get_config().get("MCP_MAX_LIMIT", 100)
    try:
        if isinstance(configured, bool):
            raise ValueError
        return max(1, min(int(configured), evidence.MAX_FAMILY_LIMIT))
    except (TypeError, ValueError, OverflowError):
        return 100


def _observed_signals(entries: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for entry in entries:
        attributes = entry["attributes"]
        if entry["type"] == "exception":
            counts["exceptions"] += 1
        elif entry["type"] == "query":
            if attributes.get("is_slow") is True:
                counts["slow_queries"] += 1
            if attributes.get("is_duplicate") is True:
                counts["duplicate_queries"] += 1
        elif entry["type"] == "request":
            status = attributes.get("status_code")
            if status is not None and 500 <= status <= 599:
                counts["http_server_errors"] += 1
            elif status is not None and 400 <= status <= 499:
                counts["http_client_errors"] += 1
    return dict(sorted(counts.items()))


def _request_summary(entries: list[dict[str, Any]]) -> dict[str, Any] | None:
    request = next((entry for entry in entries if entry["type"] == "request"), None)
    if request is None:
        return None
    attributes = request["attributes"]
    return {
        "id": request["id"],
        "duration_ms": request["duration_ms"],
        **{
            field: attributes.get(field)
            for field in (
                "method",
                "path",
                "status_code",
                "query_count",
                "duplicate_query_count",
                "had_exception",
            )
        },
    }


def _quality_for_cap(envelope: dict[str, Any], cap: int) -> dict[str, Any]:
    quality = envelope["evidence_quality"]
    actions = []
    for action in quality["next_actions"]:
        if action["code"] != "retry_with_higher_limit":
            actions.append(action)
        elif envelope["count"] < cap:
            actions.append(
                {
                    **action,
                    "parameters": {"limit": min(action["parameters"]["limit"], cap)},
                }
            )
        elif cap < evidence.MAX_FAMILY_LIMIT:
            actions.append(
                {
                    "code": "review_mcp_limit",
                    "parameters": {
                        "setting": "MCP_MAX_LIMIT",
                        "current_limit": cap,
                        "maximum": evidence.MAX_FAMILY_LIMIT,
                    },
                }
            )
        else:
            actions.append(
                {"code": "review_family_scope", "parameters": {"event_limit": cap}}
            )
    return {**quality, "next_actions": actions}


def summarize_request_family(
    family_hash: str, limit: int | None = None
) -> dict[str, Any]:
    """Summarize observed metadata while preserving evidence gaps and failures."""
    cap = _event_cap()
    # Pass invalid explicit limits to the contract validator before any DB read.
    if limit is None:
        limit = cap
    elif isinstance(limit, int) and not isinstance(limit, bool) and limit > 0:
        limit = min(limit, cap)
    envelope = evidence.read_family_evidence(family_hash, limit=limit)
    entries = envelope["entries"]
    summary = None
    if envelope["status"] == "ok":
        summary = {
            "counts_scope": "returned_events",
            "request": _request_summary(entries),
            "event_counts": dict(sorted(Counter(e["type"] for e in entries).items())),
            "observed_signals": _observed_signals(entries),
            "first_seen": entries[0]["created_at"] if entries else None,
            "last_seen": entries[-1]["created_at"] if entries else None,
        }
    return {
        **{key: value for key, value in envelope.items() if key != "entries"},
        "evidence_quality": _quality_for_cap(envelope, cap),
        "resource": "request_family_summary",
        "summary": summary,
    }
