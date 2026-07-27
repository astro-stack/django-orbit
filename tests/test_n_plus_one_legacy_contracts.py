"""Regression contracts for historical deterministic-query evidence."""

import json

import pytest

from orbit.models import OrbitEntry

pytestmark = pytest.mark.django_db


def _n_plus_one_pattern():
    return {
        "kind": "n_plus_one_candidate",
        "confidence": "high",
        "query_summary": "SELECT review",
        "occurrences": 4,
        "unique_parameter_sets": 4,
    }


def _call_mcp_tool(name, **kwargs):
    from orbit.mcp_server import create_mcp_server

    server = create_mcp_server()
    tool = server._tool_manager._tools[name]
    return json.loads(tool.fn(**kwargs))


def test_agentic_ranking_recognizes_legacy_pattern_without_materialized_count():
    from orbit.agentic import find_n_plus_one_candidates

    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        family_hash="duplicate-only",
        payload={"path": "/duplicate/", "duplicate_query_count": 100},
    )
    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        family_hash="legacy-classified",
        payload={
            "path": "/legacy-n1/",
            "duplicate_query_count": 3,
            "query_patterns": [_n_plus_one_pattern()],
        },
    )

    data = find_n_plus_one_candidates(hours=72, limit=1)

    assert data["candidates"][0]["family_hash"] == "legacy-classified"
    assert data["candidates"][0]["classification"] == "n_plus_one_candidate"


def test_mcp_ranking_recognizes_legacy_pattern_without_materialized_count():
    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        family_hash="duplicate-only",
        payload={"path": "/duplicate/", "duplicate_query_count": 100},
    )
    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        family_hash="legacy-classified",
        payload={
            "path": "/legacy-n1/",
            "duplicate_query_count": 3,
            "query_patterns": [_n_plus_one_pattern()],
        },
    )

    data = _call_mcp_tool("get_n1_patterns", limit=1)

    assert data["n1_patterns"][0]["family_hash"] == "legacy-classified"
    assert data["n1_patterns"][0]["classification"] == "n_plus_one_candidate"


def test_agent_entry_serialization_redacts_caller_and_traceback_directories():
    from orbit.agentic import agent_safe_serialize_entry

    entry = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_EXCEPTION,
        payload={
            "caller": {"filename": "C:/Users/alice/project/views.py"},
            "traceback": [
                {"filename": "/home/alice/project/services/charge.py", "lineno": 9}
            ],
        },
    )

    payload = agent_safe_serialize_entry(entry, redact_paths=True)["payload"]

    assert payload["caller"]["filename"] == "views.py"
    assert payload["traceback"][0]["filename"] == "charge.py"
    assert "alice" not in str(payload)
    assert "project" not in str(payload)


def test_mcp_query_output_redacts_caller_directories():
    entry = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_QUERY,
        duration_ms=800,
        payload={
            "sql": "SELECT 1",
            "is_slow": True,
            "caller": {"filename": "/home/alice/project/query.py"},
        },
    )

    data = _call_mcp_tool("get_slow_queries", limit=10)
    result = next(item for item in data["slow_queries"] if item["id"] == str(entry.id))

    assert result["payload"]["caller"]["filename"] == "query.py"
    assert "alice" not in str(result)


def test_legacy_n_plus_one_pattern_is_shown_as_n_plus_one_in_feed(client):
    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        family_hash="legacy-feed",
        payload={
            "method": "GET",
            "path": "/legacy-feed/",
            "status_code": 200,
            "duplicate_query_count": 3,
            "query_patterns": [_n_plus_one_pattern()],
        },
    )

    html = client.get("/orbit/feed/?type=request").content.decode()

    assert "N+1" in html


def test_daily_health_brief_counts_only_classified_n_plus_one_requests():
    from orbit.agentic import daily_health_brief

    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        payload={"path": "/duplicate/", "duplicate_query_count": 4},
    )
    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        payload={
            "path": "/legacy-n1/",
            "duplicate_query_count": 3,
            "query_patterns": [_n_plus_one_pattern()],
        },
    )

    data = daily_health_brief(hours=72)

    assert data["summary"]["n_plus_one_candidates"] == 1
    assert len(data["duplicate_query_requests"]) == 2


def test_materialized_n_plus_one_count_is_classified_without_findings():
    from orbit.agentic import find_n_plus_one_candidates

    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        family_hash="materialized-n1",
        payload={"path": "/n1/", "n_plus_one_count": 2},
    )

    data = find_n_plus_one_candidates(hours=72)

    assert data["candidates"][0]["classification"] == "n_plus_one_candidate"
    assert data["candidates"][0]["n_plus_one_findings"] == []


def test_mcp_redacts_query_pattern_caller_key_directories():
    entry = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        family_hash="caller-key-redaction",
        payload={
            "path": "/orders/",
            "query_patterns": [
                {
                    **_n_plus_one_pattern(),
                    "caller_key": "C:/Users/alice/project/orders/views.py:42:list",
                }
            ],
        },
    )

    data = _call_mcp_tool("get_recent_requests", limit=10)
    result = next(item for item in data["requests"] if item["id"] == str(entry.id))

    assert result["payload"]["query_patterns"][0]["caller_key"] == "views.py:42:list"
    assert "alice" not in str(result)
    assert "project" not in str(result)
