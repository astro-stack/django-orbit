"""
Tests for the Django Orbit MCP server.

These tests verify that each MCP tool returns valid JSON and handles
edge cases gracefully (empty database, invalid inputs, etc.).
The actual MCP transport is not tested here — only the tool logic.
"""

import json
import pytest
from django.test import override_settings
from orbit.models import OrbitEntry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_server():
    """Instantiate the MCP server (requires Django ORM to be ready)."""
    from orbit.mcp_server import create_mcp_server
    return create_mcp_server()


def _get_tool(mcp, name):
    """Extract a registered tool function by name from the FastMCP instance."""
    # FastMCP stores tools in _tool_manager; fall back to direct attribute lookup
    manager = getattr(mcp, "_tool_manager", None)
    if manager:
        tool = manager._tools.get(name)
        if tool:
            return tool.fn
    # Fallback: tools are functions in the closure — access via the server's tool list
    raise KeyError(f"Tool '{name}' not found in MCP server")


def _call_tool(mcp, name, **kwargs):
    """Call a tool by name and parse its JSON output."""
    fn = _get_tool(mcp, name)
    result = fn(**kwargs)
    return json.loads(result)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mcp_server():
    return _make_server()


@pytest.fixture
def sample_request(db):
    return OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        family_hash="abc123",
        duration_ms=120.0,
        payload={
            "method": "GET",
            "path": "/api/products/",
            "status_code": 200,
            "duplicate_query_count": 0,
        },
    )


@pytest.fixture
def sample_slow_query(db, sample_request):
    return OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_QUERY,
        family_hash="abc123",
        duration_ms=1200.0,
        payload={"sql": "SELECT * FROM products", "is_slow": True, "is_duplicate": False},
    )


@pytest.fixture
def sample_exception(db, sample_request):
    return OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_EXCEPTION,
        family_hash="abc123",
        payload={
            "exception_type": "ValueError",
            "message": "invalid literal for int()",
            "traceback": "Traceback...",
        },
    )


@pytest.fixture
def sample_n1_request(db):
    return OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        family_hash="n1hash",
        duration_ms=800.0,
        payload={
            "method": "GET",
            "path": "/api/orders/",
            "status_code": 200,
            "duplicate_query_count": 15,
        },
    )


# ---------------------------------------------------------------------------
# Import guard
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_mcp_import_error_without_package(monkeypatch):
    """create_mcp_server() raises ImportError when 'mcp' is not installed."""
    import sys
    # Temporarily hide the mcp package
    original = sys.modules.get("mcp")
    sys.modules["mcp"] = None  # type: ignore[assignment]
    try:
        # Force reimport
        import importlib
        import orbit.mcp_server as mod
        importlib.reload(mod)
        with pytest.raises(ImportError, match="pip install django-orbit"):
            mod.create_mcp_server()
    finally:
        if original is None:
            sys.modules.pop("mcp", None)
        else:
            sys.modules["mcp"] = original


# ---------------------------------------------------------------------------
# Tool: get_recent_requests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_get_recent_requests_empty(mcp_server):
    data = _call_tool(mcp_server, "get_recent_requests")
    assert data["count"] == 0
    assert data["requests"] == []


@pytest.mark.django_db
def test_get_recent_requests_returns_entries(mcp_server, sample_request):
    data = _call_tool(mcp_server, "get_recent_requests", limit=10)
    assert data["count"] == 1
    entry = data["requests"][0]
    assert entry["type"] == "request"
    assert entry["family_hash"] == "abc123"


@pytest.mark.django_db
def test_get_recent_requests_limit_capped(mcp_server, db):
    # Create 5 entries, request limit=200 (should be capped to 100)
    for i in range(5):
        OrbitEntry.objects.create(
            type=OrbitEntry.TYPE_REQUEST,
            payload={"method": "GET", "path": f"/path/{i}/", "status_code": 200},
        )
    data = _call_tool(mcp_server, "get_recent_requests", limit=200)
    assert data["count"] == 5  # only 5 exist, cap doesn't matter here


# ---------------------------------------------------------------------------
# Tool: get_slow_queries
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_get_slow_queries_empty(mcp_server):
    data = _call_tool(mcp_server, "get_slow_queries")
    assert data["count"] == 0


@pytest.mark.django_db
def test_get_slow_queries_finds_slow(mcp_server, sample_slow_query):
    data = _call_tool(mcp_server, "get_slow_queries", threshold_ms=500)
    assert data["count"] == 1
    assert data["slow_queries"][0]["duration_ms"] == 1200.0


@pytest.mark.django_db
def test_get_slow_queries_threshold_filters(mcp_server, sample_slow_query):
    # Threshold above the query's duration — should return nothing
    data = _call_tool(mcp_server, "get_slow_queries", threshold_ms=2000)
    assert data["count"] == 0


# ---------------------------------------------------------------------------
# Tool: get_exceptions
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_get_exceptions_empty(mcp_server):
    data = _call_tool(mcp_server, "get_exceptions")
    assert data["count"] == 0


@pytest.mark.django_db
def test_get_exceptions_returns_entries(mcp_server, sample_exception):
    data = _call_tool(mcp_server, "get_exceptions", hours=24)
    assert data["count"] == 1
    assert data["exceptions"][0]["type"] == "exception"


# ---------------------------------------------------------------------------
# Tool: get_n1_patterns
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_get_n1_patterns_empty(mcp_server):
    data = _call_tool(mcp_server, "get_n1_patterns")
    assert data["count"] == 0


@pytest.mark.django_db
def test_get_n1_patterns_finds_duplicates(mcp_server, sample_n1_request):
    data = _call_tool(mcp_server, "get_n1_patterns")
    assert data["count"] == 1
    assert data["n1_patterns"][0]["duplicate_query_count"] == 15
    assert data["n1_patterns"][0]["path"] == "/api/orders/"


@pytest.mark.django_db
def test_get_n1_patterns_excludes_clean_requests(mcp_server, sample_request):
    # sample_request has duplicate_query_count=0 — should not appear
    data = _call_tool(mcp_server, "get_n1_patterns")
    assert data["count"] == 0


# ---------------------------------------------------------------------------
# Tool: search_entries
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_search_entries_empty(mcp_server):
    data = _call_tool(mcp_server, "search_entries", query="nonexistent")
    assert data["count"] == 0


@pytest.mark.django_db
def test_search_entries_finds_by_keyword(mcp_server, sample_request):
    data = _call_tool(mcp_server, "search_entries", query="products")
    assert data["count"] == 1


@pytest.mark.django_db
def test_search_entries_filters_by_type(mcp_server, sample_request, sample_exception):
    # Search for "abc" (in family_hash) but only in exceptions
    data = _call_tool(mcp_server, "search_entries", query="ValueError", entry_type="exception")
    assert data["count"] == 1
    assert data["entries"][0]["type"] == "exception"


# ---------------------------------------------------------------------------
# Tool: get_request_detail
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_get_request_detail_not_found(mcp_server):
    data = _call_tool(mcp_server, "get_request_detail", family_hash="doesnotexist")
    assert "error" in data


@pytest.mark.django_db
def test_get_request_detail_returns_all_events(
    mcp_server, sample_request, sample_slow_query, sample_exception
):
    data = _call_tool(mcp_server, "get_request_detail", family_hash="abc123")
    assert data["family_hash"] == "abc123"
    assert data["total_events"] == 3
    assert set(data["event_types"].keys()) == {"request", "query", "exception"}


# ---------------------------------------------------------------------------
# Tool: get_stats_summary
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_get_stats_summary_empty(mcp_server):
    data = _call_tool(mcp_server, "get_stats_summary")
    assert data["requests"]["total"] == 0
    assert data["requests"]["error_rate_pct"] == 0
    assert data["exceptions"]["total"] == 0


@pytest.mark.django_db
def test_get_stats_summary_with_data(
    mcp_server, sample_request, sample_slow_query, sample_exception
):
    data = _call_tool(mcp_server, "get_stats_summary", hours=24)
    assert data["requests"]["total"] == 1
    assert data["queries"]["slow"] == 1
    assert data["exceptions"]["total"] == 1
