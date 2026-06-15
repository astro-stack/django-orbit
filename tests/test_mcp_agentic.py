"""
Tests for the agentic MCP tools added in M3 (C5): explain_query, get_request_timeline,
get_exception_groups, propose_n1_fix, get_entry_source_context.
"""

import json

import pytest

from orbit.models import OrbitEntry
from orbit.utils import compute_exception_fingerprint

pytestmark = pytest.mark.django_db


def _make_server():
    from orbit.mcp_server import create_mcp_server

    return create_mcp_server()


def _call(mcp, name, **kwargs):
    tool = mcp._tool_manager._tools.get(name)
    assert tool is not None, f"tool {name} not registered"
    return json.loads(tool.fn(**kwargs))


def test_explain_query_tool():
    mcp = _make_server()
    q = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_QUERY,
        payload={"sql": "SELECT * FROM orbit_orbitentry", "params": []},
    )
    out = _call(mcp, "explain_query", entry_id=str(q.id))
    assert out["explain"]["supported"] is True
    assert out["explain"].get("plan")


def test_explain_query_tool_bad_id():
    mcp = _make_server()
    out = _call(mcp, "explain_query", entry_id="00000000-0000-0000-0000-000000000000")
    assert "error" in out


def test_get_request_timeline_tool():
    mcp = _make_server()
    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST, family_hash="f1", duration_ms=100.0,
        payload={"method": "GET", "status_code": 200},
    )
    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_QUERY, family_hash="f1", duration_ms=20.0,
        payload={"sql": "SELECT 1", "start_offset_ms": 10.0},
    )
    out = _call(mcp, "get_request_timeline", family_hash="f1")
    assert out["query_count"] == 1
    assert out["request_duration_ms"] == 100.0
    assert out["spans"][0]["start_offset_ms"] == 10.0


def test_get_exception_groups_tool():
    mcp = _make_server()
    info = {"exception_type": "ValueError", "traceback": [{"filename": "a.py", "name": "f"}]}
    fp = compute_exception_fingerprint(info)
    for i in range(3):
        OrbitEntry.objects.create(
            type=OrbitEntry.TYPE_EXCEPTION, fingerprint=fp,
            payload={"exception_type": "ValueError", "message": f"m{i}", "traceback": info["traceback"]},
        )
    out = _call(mcp, "get_exception_groups")
    assert out["count"] == 1
    assert out["groups"][0]["count"] == 3
    assert out["groups"][0]["exception_type"] == "ValueError"


def test_propose_n1_fix_tool():
    mcp = _make_server()
    for _ in range(4):
        OrbitEntry.objects.create(
            type=OrbitEntry.TYPE_QUERY, family_hash="n1", duration_ms=5.0,
            payload={"sql": "SELECT * FROM app_book WHERE author_id = 1",
                     "caller": {"filename": "views.py", "lineno": 10}},
        )
    out = _call(mcp, "propose_n1_fix", family_hash="n1")
    assert out["n1_patterns"] == 1
    s = out["suggestions"][0]
    assert s["repeated"] == 4
    assert "select_related" in s["suggestion"] or "prefetch_related" in s["suggestion"]
    assert "views.py:10" in s["source"]


def test_get_entry_source_context_query_and_exception():
    mcp = _make_server()
    q = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_QUERY,
        payload={"sql": "SELECT 1", "caller": {"filename": "v.py", "lineno": 3, "function": "view"}},
    )
    out = _call(mcp, "get_entry_source_context", entry_id=str(q.id))
    assert out["type"] == "query"
    assert out["caller"]["filename"] == "v.py"

    e = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_EXCEPTION,
        payload={"exception_type": "KeyError", "message": "x", "traceback": [{"filename": "b.py", "name": "g"}]},
    )
    out2 = _call(mcp, "get_entry_source_context", entry_id=str(e.id))
    assert out2["type"] == "exception"
    assert out2["traceback"][0]["filename"] == "b.py"
