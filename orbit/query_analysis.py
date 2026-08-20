"""Deterministic SQL evidence and duplicate-query pattern analysis."""

import hashlib
import json
import re
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Tuple

QUERY_SIGNATURE_VERSION = 1
READ_OPERATIONS = {"SELECT", "WITH"}
WRITE_OPERATIONS = {"INSERT", "UPDATE", "DELETE", "MERGE", "REPLACE"}
N_PLUS_ONE_KINDS = {
    "n_plus_one_candidate",
    "per_row_aggregate_candidate",
}

_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT_RE = re.compile(r"--[^\r\n]*")
_STRING_LITERAL_RE = re.compile(r"'(?:''|[^'])*'")
_PLACEHOLDER_RE = re.compile(r"%\([^)]+\)s|%s|\$\d+|:[A-Za-z_][A-Za-z0-9_]*|\?")
_NUMBER_LITERAL_RE = re.compile(
    r"(?<![A-Za-z0-9_])[-+]?(?:\d+\.\d+|\d+)(?![A-Za-z0-9_])"
)
_WHITESPACE_RE = re.compile(r"\s+")
_OPERATION_RE = re.compile(r"^\s*([A-Za-z]+)")
_AGGREGATE_RE = re.compile(r"\b(COUNT|SUM|AVG|MIN|MAX|EXISTS)\s*\(", re.I)
_COLLECTION_RE = re.compile(r"\b(?:FROM|JOIN|UPDATE|INTO)\s+([A-Za-z0-9_.\"`]+)", re.I)


def normalize_query_shape(sql: str) -> str:
    """Return a low-cardinality SQL shape without dynamic literal values."""
    value = str(sql or "")
    value = _BLOCK_COMMENT_RE.sub(" ", value)
    value = _LINE_COMMENT_RE.sub(" ", value)
    value = _STRING_LITERAL_RE.sub("?", value)
    value = _PLACEHOLDER_RE.sub("?", value)
    value = _NUMBER_LITERAL_RE.sub("?", value)
    return _WHITESPACE_RE.sub(" ", value).strip().lower()


def _hash(value: str, length: int = 16) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()[:length]


def _safe_positive_int(value: Any, default: int, minimum: int) -> int:
    try:
        return max(minimum, int(value))
    except (TypeError, ValueError, OverflowError):
        return default


def _operation(sql: str) -> str:
    match = _OPERATION_RE.search(str(sql or ""))
    return match.group(1).upper() if match else "UNKNOWN"


def _aggregate(sql: str) -> Optional[str]:
    match = _AGGREGATE_RE.search(str(sql or ""))
    return match.group(1).upper() if match else None


def _parameter_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, bytes):
        return "bytes"
    if isinstance(value, str):
        return "str"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, dict):
        return "dict[{}]".format(len(value))
    if isinstance(value, (list, tuple, set)):
        return "{}[{}]".format(type(value).__name__, len(value))
    return type(value).__name__


def parameter_shape(params: Any) -> Any:
    """Describe parameter types and counts without retaining parameter values."""
    if params is None:
        return []
    if isinstance(params, dict):
        return ["dict[{}]".format(len(params))]
    if isinstance(params, (list, tuple)):
        return [_parameter_type(value) for value in params]
    return [_parameter_type(params)]


def _parameter_fingerprint(params: Any) -> str:
    try:
        serialized = json.dumps(
            params,
            sort_keys=True,
            separators=(",", ":"),
            default=lambda value: repr(value),
        )
    except Exception:
        serialized = repr(params)
    return _hash(serialized)


def _query_summary(operation: str, sql: str) -> str:
    collections = []
    for match in _COLLECTION_RE.finditer(str(sql or "")):
        collection = match.group(1)
        if collection not in collections:
            collections.append(collection)
        if len(collections) == 4:
            break
    return " ".join([operation] + collections).strip()


def caller_key_from_payload(caller: Any) -> str:
    """Build a portable grouping key from captured caller metadata."""
    if isinstance(caller, str):
        return caller.replace("\\", "/")
    if not isinstance(caller, dict):
        return ""
    filename = str(caller.get("filename") or "").replace("\\", "/")
    lineno = caller.get("lineno") or ""
    function = caller.get("function") or caller.get("name") or ""
    return "{}:{}:{}".format(filename, lineno, function)


def build_query_evidence(
    sql: str,
    params: Any,
    database: str = "default",
    caller_key: str = "",
) -> Dict[str, Any]:
    """Build safe, versioned evidence used by the pattern analyzer."""
    shape = normalize_query_shape(sql)
    operation = _operation(sql)
    aggregate = _aggregate(sql)
    evidence = {
        "query_signature": _hash(
            "{}|{}|{}".format(database or "default", operation, shape)
        ),
        "query_signature_version": QUERY_SIGNATURE_VERSION,
        "query_summary": _query_summary(operation, sql),
        "operation": operation,
        "parameter_shape": parameter_shape(params),
        "parameter_fingerprint": _parameter_fingerprint(params),
        "caller_key": str(caller_key or "").replace("\\", "/"),
    }
    if aggregate:
        evidence["aggregate"] = aggregate
    return evidence


def _ensure_evidence(query: Dict[str, Any]) -> Dict[str, Any]:
    if query.get("query_signature") and query.get("parameter_fingerprint"):
        return query
    caller_key = query.get("caller_key") or caller_key_from_payload(query.get("caller"))
    return {
        **query,
        **build_query_evidence(
            sql=query.get("sql") or "",
            params=query.get("params"),
            database=query.get("database") or "default",
            caller_key=caller_key,
        ),
    }


def _finding(
    group: List[Dict[str, Any]],
    truncated: bool,
) -> Dict[str, Any]:
    first = group[0]
    operation = first.get("operation") or "UNKNOWN"
    aggregate = first.get("aggregate")
    parameter_fingerprints = {item.get("parameter_fingerprint") for item in group}
    unique_parameters = len(parameter_fingerprints)
    caller_key = first.get("caller_key") or ""

    evidence = ["same_query_shape"]
    counter_evidence = []
    if caller_key:
        evidence.append("same_callsite")
    if unique_parameters > 1:
        evidence.append("varying_parameters")
    else:
        counter_evidence.append("identical_parameters")

    if operation in WRITE_OPERATIONS:
        kind = "write_loop"
        confidence = "high" if unique_parameters > 1 else "medium"
        counter_evidence.append("write_operation")
    elif unique_parameters == 1:
        kind = "exact_duplicate"
        confidence = "medium"
    elif aggregate:
        kind = "per_row_aggregate_candidate"
        confidence = "high" if caller_key else "medium"
        evidence.append("per_row_aggregate")
    else:
        kind = "n_plus_one_candidate"
        confidence = "high" if caller_key else "medium"

    result = {
        "schema_version": 1,
        "kind": kind,
        "confidence": confidence,
        "query_signature": first.get("query_signature"),
        "query_signature_version": first.get("query_signature_version"),
        "query_summary": first.get("query_summary"),
        "operation": operation,
        "database": first.get("database") or "default",
        "caller_key": caller_key or None,
        "occurrences": len(group),
        "avoidable_executions": max(0, len(group) - 1),
        "unique_parameter_sets": unique_parameters,
        "total_duration_ms": round(
            sum(float(item.get("duration_ms") or 0) for item in group), 3
        ),
        "evidence": evidence,
        "counter_evidence": counter_evidence,
        "capture_limits": (["query_analysis_truncated"] if truncated else []),
    }
    if aggregate:
        result["aggregate"] = aggregate
    return result


def analyze_query_patterns(
    queries: Iterable[Dict[str, Any]],
    min_occurrences: Any = 4,
    max_queries: Any = 1000,
) -> List[Dict[str, Any]]:
    """Classify repeated query shapes using deterministic, bounded evidence."""
    safe_min = _safe_positive_int(min_occurrences, default=4, minimum=2)
    safe_max = _safe_positive_int(
        max_queries,
        default=max(1000, safe_min),
        minimum=safe_min,
    )
    query_list = list(queries)
    truncated = len(query_list) > safe_max
    bounded = query_list[:safe_max]

    groups: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = defaultdict(list)
    for raw_query in bounded:
        query = _ensure_evidence(raw_query)
        key = (
            query.get("database") or "default",
            query.get("query_signature") or "",
            query.get("caller_key") or "",
        )
        groups[key].append(query)

    findings = [
        _finding(group, truncated)
        for group in groups.values()
        if len(group) >= safe_min
    ]
    return sorted(
        findings,
        key=lambda item: (
            item["kind"] not in N_PLUS_ONE_KINDS,
            -item["total_duration_ms"],
            -item["occurrences"],
        ),
    )


def valid_query_patterns(patterns: Any) -> List[Dict[str, Any]]:
    """Ignore malformed historical/imported pattern payloads."""
    if not isinstance(patterns, (list, tuple)):
        return []
    return [pattern for pattern in patterns if isinstance(pattern, dict)]


def n_plus_one_findings(findings: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return findings that carry actual N+1 evidence."""
    return [finding for finding in findings if finding.get("kind") in N_PLUS_ONE_KINDS]


def request_n_plus_one_findings(payload: Any) -> List[Dict[str, Any]]:
    """Read classified N+1 findings from current or historical request payloads."""
    if not isinstance(payload, dict):
        return []
    return n_plus_one_findings(valid_query_patterns(payload.get("query_patterns")))


def request_n_plus_one_count(payload: Any) -> int:
    """Use materialized count when available, with a historical-pattern fallback."""
    if not isinstance(payload, dict):
        return 0
    try:
        materialized = max(0, int(payload.get("n_plus_one_count", 0)))
    except (TypeError, ValueError):
        materialized = 0
    return max(materialized, len(request_n_plus_one_findings(payload)))
