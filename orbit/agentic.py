"""
Agent-native investigation helpers for Django Orbit.

This module is the safety boundary for MCP tools and incident bundles. Keep all
agent-facing payload serialization here so masking, truncation and summaries stay
consistent across human and AI workflows.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any, Iterable

from django.db.models import Count, Q
from django.utils import timezone

from orbit.conf import get_config
from orbit.models import OrbitEntry
from orbit.utils import mask_sensitive_data, parse_tags, serialize_for_json

HIGH_LEVEL_TOOLS = [
    "audit_mcp_exposure",
    "investigate_request",
    "investigate_exception_group",
    "create_incident_bundle",
    "build_debug_brief",
    "propose_fix_hypotheses",
    "propose_test_plan",
]

DEFAULT_MAX_PAYLOAD_CHARS = 12000
DEFAULT_MAX_EVENTS = 100


def _config_int(name: str, default: int) -> int:
    value = get_config().get(name, default)
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return default


def _config_bool(name: str, default: bool) -> bool:
    return bool(get_config().get(name, default))


def _json_size(value: Any) -> int:
    return len(json.dumps(value, default=str, separators=(",", ":")))


def _truncate_payload(payload: Any, max_payload_chars: int) -> tuple[Any, bool, int]:
    """Return a JSON-safe payload bounded by a deterministic character budget."""
    safe_payload = serialize_for_json(mask_sensitive_data(payload or {}))
    size = _json_size(safe_payload)
    if size <= max_payload_chars:
        return safe_payload, False, size

    # Keep structure predictable for agents and avoid leaking omitted content.
    metadata = {
        "_truncated": True,
        "_original_size_chars": size,
        "_max_size_chars": max_payload_chars,
    }
    if "***HIDDEN***" in json.dumps(safe_payload, default=str):
        metadata["_redaction_marker"] = "***HIDDEN***"
    return metadata, True, size


def _safe_limit(limit: int | None, default: int = 20) -> int:
    configured_max = _config_int("MCP_MAX_LIMIT", 100)
    if limit is None:
        limit = default
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = default
    return max(1, min(limit, configured_max))


def agent_safe_serialize_entry(
    entry: OrbitEntry,
    *,
    include_payload: bool | None = None,
    max_payload_chars: int | None = None,
) -> dict[str, Any]:
    """
    Serialize an OrbitEntry for agent consumption.

    The serializer always masks sensitive keys before output and annotates payload
    truncation/omission so agents know when evidence is incomplete.
    """
    if include_payload is None:
        include_payload = _config_bool("MCP_INCLUDE_PAYLOADS", True)
    if max_payload_chars is None:
        max_payload_chars = _config_int("MCP_MAX_PAYLOAD_CHARS", DEFAULT_MAX_PAYLOAD_CHARS)

    data: dict[str, Any] = {
        "id": str(entry.id),
        "type": entry.type,
        "summary": entry.summary,
        "duration_ms": entry.duration_ms,
        "family_hash": entry.family_hash,
        "fingerprint": entry.fingerprint,
        "tags": parse_tags(entry.tags),
        "created_at": entry.created_at.isoformat(),
        "is_error": entry.is_error,
        "is_warning": entry.is_warning,
        "payload_masked": True,
    }

    if not include_payload:
        data["payload_omitted"] = True
        return data

    payload, truncated, original_size = _truncate_payload(entry.payload, max_payload_chars)
    data.update(
        {
            "payload": payload,
            "payload_truncated": truncated,
            "payload_size_chars": original_size,
        }
    )
    return data


def _serialize_entries(entries: Iterable[OrbitEntry], *, limit: int | None = None) -> list[dict[str, Any]]:
    safe_limit = _safe_limit(limit, DEFAULT_MAX_EVENTS)
    return [agent_safe_serialize_entry(entry) for entry in list(entries)[:safe_limit]]


def _event_counts(entries: Iterable[OrbitEntry]) -> dict[str, int]:
    counts = Counter(entry.type for entry in entries)
    return dict(sorted(counts.items()))


def _diagnose(entries: list[OrbitEntry]) -> dict[str, Any]:
    signals: list[str] = []
    if any(entry.type == OrbitEntry.TYPE_EXCEPTION for entry in entries):
        signals.append("exception")
    if any(entry.type == OrbitEntry.TYPE_LOG and entry.is_error for entry in entries):
        signals.append("error_log")
    if any(entry.type == OrbitEntry.TYPE_QUERY and entry.payload.get("is_slow") for entry in entries):
        signals.append("slow_query")
    if any(entry.type == OrbitEntry.TYPE_QUERY and entry.payload.get("is_duplicate") for entry in entries):
        signals.append("duplicate_query")
    if any(entry.type == OrbitEntry.TYPE_REQUEST and entry.is_error for entry in entries):
        signals.append("http_error")
    if any(entry.type == OrbitEntry.TYPE_JOB and entry.is_error for entry in entries):
        signals.append("job_error")

    severity = "ok"
    if "exception" in signals or "http_error" in signals or "job_error" in signals:
        severity = "error"
    elif "error_log" in signals or "slow_query" in signals or "duplicate_query" in signals:
        severity = "warning"

    hypotheses = []
    if "exception" in signals:
        hypotheses.append("An exception occurred in the request or related background flow.")
    if "slow_query" in signals:
        hypotheses.append("At least one SQL query exceeded the configured slow-query threshold.")
    if "duplicate_query" in signals:
        hypotheses.append("Duplicate SQL queries suggest a possible N+1 or missing eager loading pattern.")
    if "error_log" in signals:
        hypotheses.append("Error-level logs near the event may contain the domain-specific failure reason.")
    if not hypotheses:
        hypotheses.append("No strong failure signal was found in the captured Orbit entries.")

    return {
        "severity": severity,
        "signals": signals,
        "hypotheses": hypotheses,
    }


def _query_analysis(entries: list[OrbitEntry]) -> dict[str, Any]:
    queries = [entry for entry in entries if entry.type == OrbitEntry.TYPE_QUERY]
    slow = [entry for entry in queries if entry.payload.get("is_slow")]
    duplicate = [entry for entry in queries if entry.payload.get("is_duplicate")]
    top_slow = sorted(queries, key=lambda entry: entry.duration_ms or 0, reverse=True)[:5]
    duplicate_signatures = Counter(
        (entry.payload.get("sql") or "")[:180]
        for entry in duplicate
    )
    return {
        "total": len(queries),
        "slow_count": len(slow),
        "duplicate_count": len(duplicate),
        "top_slow": _serialize_entries(top_slow, limit=5),
        "duplicate_signatures": [
            {"sql_preview": sql, "count": count}
            for sql, count in duplicate_signatures.most_common(5)
            if sql
        ],
    }


def _timeline(entries: list[OrbitEntry]) -> list[dict[str, Any]]:
    ordered = sorted(entries, key=lambda entry: entry.created_at)
    first = ordered[0].created_at if ordered else None
    result = []
    for entry in ordered:
        offset_ms = None
        if first is not None:
            offset_ms = round((entry.created_at - first).total_seconds() * 1000, 3)
        item = agent_safe_serialize_entry(entry, include_payload=False)
        item["offset_ms"] = offset_ms
        result.append(item)
    return result


def _recommended_next_actions(diagnosis: dict[str, Any]) -> list[str]:
    actions = ["Review the timeline and representative error context before editing code."]
    signals = set(diagnosis.get("signals", []))
    if "exception" in signals:
        actions.append("Inspect the representative traceback and add a regression test for the failing path.")
    if "duplicate_query" in signals:
        actions.append("Check ORM relationships for select_related() or prefetch_related() opportunities.")
    if "slow_query" in signals:
        actions.append("Run EXPLAIN for the slowest SELECT query and review indexes/filter shape.")
    if "error_log" in signals:
        actions.append("Use nearby error logs to narrow the domain condition that triggered the failure.")
    return actions


def audit_mcp_exposure() -> dict[str, Any]:
    """Return the effective agent-facing exposure policy."""
    config = get_config()
    return {
        "mcp_enabled": bool(config.get("MCP_ENABLED", True)),
        "include_payloads": bool(config.get("MCP_INCLUDE_PAYLOADS", True)),
        "max_limit": _config_int("MCP_MAX_LIMIT", 100),
        "max_payload_chars": _config_int("MCP_MAX_PAYLOAD_CHARS", DEFAULT_MAX_PAYLOAD_CHARS),
        "high_level_tools": HIGH_LEVEL_TOOLS,
        "safety": {
            "serializer": "agent_safe_serialize_entry",
            "payloads_masked": True,
            "sensitive_keys": config.get("MASK_KEYS", []),
            "truncation": "Payloads larger than MCP_MAX_PAYLOAD_CHARS are replaced with size metadata.",
        },
    }


def investigate_request(family_hash: str, limit: int | None = None) -> dict[str, Any]:
    """Build a bounded diagnosis for one request family."""
    entries = list(OrbitEntry.objects.for_family(family_hash)[: _safe_limit(limit, DEFAULT_MAX_EVENTS)])
    if not entries:
        return {"error": f"No entries found for family_hash: {family_hash}"}

    request = next((entry for entry in entries if entry.type == OrbitEntry.TYPE_REQUEST), entries[0])
    diagnosis = _diagnose(entries)
    return {
        "family_hash": family_hash,
        "request": agent_safe_serialize_entry(request),
        "diagnosis": diagnosis,
        "event_counts": _event_counts(entries),
        "query_analysis": _query_analysis(entries),
        "timeline": _timeline(entries),
        "events": _serialize_entries(entries, limit=limit),
        "recommended_next_actions": _recommended_next_actions(diagnosis),
    }


def _affected_paths_for_families(family_hashes: list[str]) -> list[dict[str, Any]]:
    if not family_hashes:
        return []
    rows = (
        OrbitEntry.objects.filter(type=OrbitEntry.TYPE_REQUEST, family_hash__in=family_hashes)
        .values("payload__path")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )
    return [
        {"path": row.get("payload__path") or "?", "count": row["count"]}
        for row in rows
    ]


def investigate_exception_group(fingerprint: str, limit: int | None = None) -> dict[str, Any]:
    """Summarize one exception fingerprint with blast-radius context."""
    safe_limit = _safe_limit(limit, 50)
    qs = OrbitEntry.objects.exceptions().filter(fingerprint=fingerprint).order_by("-created_at")
    representative = qs.first()
    if representative is None:
        return {"error": f"No exception group found for fingerprint: {fingerprint}"}

    exceptions = list(qs[:safe_limit])
    family_hashes = [entry.family_hash for entry in exceptions if entry.family_hash]
    related = list(OrbitEntry.objects.filter(family_hash__in=family_hashes).order_by("created_at")[:DEFAULT_MAX_EVENTS])
    diagnosis = _diagnose(related or exceptions)
    return {
        "fingerprint": fingerprint,
        "count": qs.count(),
        "first_seen": qs.order_by("created_at").first().created_at.isoformat(),
        "last_seen": representative.created_at.isoformat(),
        "representative": agent_safe_serialize_entry(representative),
        "affected_paths": _affected_paths_for_families(family_hashes),
        "diagnosis": diagnosis,
        "recent_occurrences": _serialize_entries(exceptions, limit=safe_limit),
        "recommended_next_actions": _recommended_next_actions(diagnosis),
    }



def _resolve_source(source_type: str, source_value: str, hours: int = 72) -> dict[str, Any]:
    if source_type == "family_hash":
        return investigate_request(source_value)
    if source_type == "fingerprint":
        return investigate_exception_group(source_value)
    if source_type in {"ticket", "query", "text"}:
        return build_debug_brief(source_value, hours=hours)
    return {"error": f"Unsupported source_type: {source_type}"}


def _diagnosis_from_primary(primary: dict[str, Any]) -> dict[str, Any]:
    diagnosis = primary.get("diagnosis")
    if isinstance(diagnosis, dict):
        return diagnosis
    nested = primary.get("primary")
    if isinstance(nested, dict) and isinstance(nested.get("diagnosis"), dict):
        return nested["diagnosis"]
    return {}


def _collect_code_surfaces(value: Any) -> list[str]:
    surfaces: list[str] = []

    def _walk(item: Any) -> None:
        if isinstance(item, dict):
            filename = item.get("filename")
            if filename and str(filename) not in surfaces:
                surfaces.append(str(filename))
            caller = item.get("caller")
            if isinstance(caller, dict):
                caller_filename = caller.get("filename")
                if caller_filename and str(caller_filename) not in surfaces:
                    surfaces.append(str(caller_filename))
            for child in item.values():
                _walk(child)
        elif isinstance(item, list):
            for child in item:
                _walk(child)

    _walk(value)
    return surfaces[:10]


def _bundle_to_markdown(bundle: dict[str, Any]) -> str:
    primary = bundle.get("primary", {})
    diagnosis = _diagnosis_from_primary(primary)
    source = bundle.get("source", {})
    lines = [
        "# Django Orbit Incident Bundle",
        "",
        f"- Source: `{source.get('type')}` = `{source.get('value')}`",
        f"- Generated: `{bundle.get('generated_at')}`",
        f"- Severity: `{diagnosis.get('severity', 'unknown')}`",
        "",
        "## Signals",
    ]
    signals = diagnosis.get("signals") or []
    if signals:
        lines.extend(f"- `{signal}`" for signal in signals)
    else:
        lines.append("- No strong signal captured.")

    lines.extend(["", "## Hypotheses"])
    for hypothesis in diagnosis.get("hypotheses") or ["No hypothesis available."]:
        lines.append(f"- {hypothesis}")

    if primary.get("family_hash"):
        request = primary.get("request") or {}
        lines.extend([
            "",
            "## Request",
            f"- Family hash: `{primary.get('family_hash')}`",
            f"- Summary: {request.get('summary', '?')}",
        ])
    if primary.get("fingerprint"):
        representative = primary.get("representative") or {}
        lines.extend([
            "",
            "## Exception Group",
            f"- Fingerprint: `{primary.get('fingerprint')}`",
            f"- Count: `{primary.get('count')}`",
            f"- Representative: {representative.get('summary', '?')}",
        ])

    events = primary.get("events") or primary.get("recent_occurrences") or []
    if events:
        lines.extend(["", "## Evidence"])
        for event in events[:5]:
            lines.append(f"- `{event.get('type')}` {event.get('summary', '?')}")


    query_analysis = primary.get("query_analysis") or {}
    if query_analysis:
        lines.extend([
            "",
            "## Query Analysis",
            f"- Total queries: `{query_analysis.get('total', 0)}`",
            f"- Slow queries: `{query_analysis.get('slow_count', 0)}`",
            f"- Duplicate queries: `{query_analysis.get('duplicate_count', 0)}`",
        ])

    lines.extend(["", "## Recommended Next Actions"])
    for action in bundle.get("agent_handoff", {}).get("recommended_next_actions") or []:
        lines.append(f"- {action}")

    lines.extend([
        "",
        "## Safety",
        "- Payloads are masked before export.",
        "- Oversized payloads are replaced with truncation metadata.",
    ])
    return "\n".join(lines) + "\n"

def create_incident_bundle(source_type: str, source_value: str, hours: int = 72, format: str = "json") -> dict[str, Any] | str:
    """Create an on-demand agent handoff bundle without persisting state."""
    primary = _resolve_source(source_type, source_value, hours=hours)
    if "error" in primary:
        return primary

    diagnosis = _diagnosis_from_primary(primary)
    bundle = {
        "bundle_version": "agentic-v1",
        "generated_at": timezone.now().isoformat(),
        "source": {"type": source_type, "value": source_value},
        "primary": primary,
        "safety_report": {
            "payloads_masked": True,
            "payload_truncation_enabled": True,
            "serializer": "agent_safe_serialize_entry",
        },
        "agent_handoff": {
            "recommended_next_actions": _recommended_next_actions(diagnosis),
            "suggested_tools": [
                {"tool": "investigate_request", "when": "Use when a family_hash is identified."},
                {"tool": "investigate_exception_group", "when": "Use when an exception fingerprint is identified."},
                {"tool": "propose_fix_hypotheses", "when": "Use after the bundle identifies the dominant failure signal."},
                {"tool": "propose_test_plan", "when": "Use before handing the issue to a coding agent."},
            ],
        },
    }
    if format == "markdown":
        return _bundle_to_markdown(bundle)
    if format != "json":
        return {"error": f"Unsupported incident bundle format: {format}"}
    return bundle


def _search_terms(query: str) -> list[str]:
    terms = []
    for raw in query.replace("/", " ").replace("_", " ").split():
        term = raw.strip().strip('"\'.,:;()[]{}').lower()
        if len(term) >= 3 and term not in terms:
            terms.append(term)
    return terms[:8]


def _build_search_q(terms: list[str]) -> Q:
    condition = Q()
    for term in terms:
        condition |= Q(payload__icontains=term) | Q(tags__icontains=term)
    return condition


def build_debug_brief(query: str, hours: int = 72, limit: int | None = None) -> dict[str, Any]:
    """Match ticket/error text to recent Orbit evidence and suggest next tools."""
    safe_limit = _safe_limit(limit, 10)
    terms = _search_terms(query)
    since = timezone.now() - timezone.timedelta(hours=max(1, int(hours or 72)))
    if not terms:
        return {
            "query": query,
            "terms": [],
            "matches": {"requests": [], "exceptions": [], "logs": []},
            "suggested_tools": [],
        }

    condition = _build_search_q(terms)
    base = OrbitEntry.objects.filter(created_at__gte=since).filter(condition).order_by("-created_at")
    requests = list(base.filter(type=OrbitEntry.TYPE_REQUEST)[:safe_limit])
    exceptions = list(base.filter(type=OrbitEntry.TYPE_EXCEPTION)[:safe_limit])
    logs = list(base.filter(type=OrbitEntry.TYPE_LOG)[:safe_limit])

    suggested = []
    if exceptions:
        fp = exceptions[0].fingerprint
        if fp:
            suggested.append({"tool": "create_incident_bundle", "source_type": "fingerprint", "source_value": fp})
            suggested.append({"tool": "investigate_exception_group", "fingerprint": fp})
    if requests:
        family_hash = requests[0].family_hash
        if family_hash:
            suggested.append({"tool": "create_incident_bundle", "source_type": "family_hash", "source_value": family_hash})
            suggested.append({"tool": "investigate_request", "family_hash": family_hash})

    return {
        "query": query,
        "terms": terms,
        "hours": hours,
        "matches": {
            "requests": _serialize_entries(requests, limit=safe_limit),
            "exceptions": _serialize_entries(exceptions, limit=safe_limit),
            "logs": _serialize_entries(logs, limit=safe_limit),
        },
        "suggested_tools": suggested,
    }

def propose_fix_hypotheses(source_type: str, source_value: str, hours: int = 72) -> dict[str, Any]:
    """Rank likely fix directions from Orbit evidence without editing code."""
    primary = _resolve_source(source_type, source_value, hours=hours)
    if "error" in primary:
        return primary

    diagnosis = _diagnosis_from_primary(primary)
    signals = set(diagnosis.get("signals", []))
    hypotheses = []
    if "exception" in signals:
        hypotheses.append({
            "title": "Fix the failing exception path",
            "confidence": "high",
            "evidence": "Orbit captured an exception in the matched request or exception group.",
            "recommended_action": "Inspect the representative traceback and add a regression test before changing code.",
        })
    if "duplicate_query" in signals:
        hypotheses.append({
            "title": "Remove possible N+1 query pattern",
            "confidence": "medium",
            "evidence": "Duplicate SQL queries were captured in the request family.",
            "recommended_action": "Review ORM relationship loading and consider select_related() or prefetch_related().",
        })
    if "slow_query" in signals:
        hypotheses.append({
            "title": "Optimize slow SQL path",
            "confidence": "medium",
            "evidence": "At least one query exceeded the slow-query threshold.",
            "recommended_action": "Run EXPLAIN and check index/filter shape for the slowest SELECT.",
        })
    if "error_log" in signals:
        hypotheses.append({
            "title": "Use domain log message as failure clue",
            "confidence": "medium",
            "evidence": "Error-level logs were captured near the failure.",
            "recommended_action": "Trace the log message to the application branch that emitted it.",
        })
    if not hypotheses:
        hypotheses.append({
            "title": "Collect more focused runtime evidence",
            "confidence": "low",
            "evidence": "Orbit did not capture a strong failure signal for this source.",
            "recommended_action": "Reproduce the issue with request, query, log and exception recording enabled.",
        })

    return {
        "source": {"type": source_type, "value": source_value},
        "hypotheses": hypotheses,
        "likely_code_surfaces": _collect_code_surfaces(primary),
        "safety": {"does_not_modify_code": True, "uses_masked_payloads": True},
    }


def propose_test_plan(source_type: str, source_value: str, hours: int = 72) -> dict[str, Any]:
    """Suggest tests that should cover the observed runtime failure."""
    primary = _resolve_source(source_type, source_value, hours=hours)
    if "error" in primary:
        return primary

    diagnosis = _diagnosis_from_primary(primary)
    signals = set(diagnosis.get("signals", []))
    request = primary.get("request") or {}
    request_payload = request.get("payload") or {}
    path = request_payload.get("path") or request_payload.get("full_path") or source_value
    tests = [{
        "type": "integration",
        "target": str(path),
        "purpose": "Reproduce the observed runtime path with Orbit evidence as the fixture for expected behavior.",
    }]
    if "exception" in signals:
        tests.append({
            "type": "unit",
            "target": "exception branch",
            "purpose": "Cover the failing branch from the representative traceback with a focused regression test.",
        })
    if "duplicate_query" in signals or "slow_query" in signals:
        tests.append({
            "type": "performance",
            "target": str(path),
            "purpose": "Assert query count or slow-query behavior does not regress after the fix.",
        })
    if "error_log" in signals:
        tests.append({
            "type": "integration",
            "target": "logged failure condition",
            "purpose": "Exercise the domain condition that emitted the error log.",
        })

    return {
        "source": {"type": source_type, "value": source_value},
        "recommended_tests": tests,
        "safety": {"does_not_modify_code": True, "uses_masked_payloads": True},
    }

