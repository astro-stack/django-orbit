"""
Protocol-level tests for the Django Orbit MCP server.

Unlike ``test_mcp.py`` (which calls tool functions directly), these tests talk
to the real server through the MCP SDK's in-memory client/session transport:
``initialize`` -> ``tools/list`` -> ``tools/call``. They run on both mcp 1.x
(``mcp.shared.memory``) and mcp 2.x (``mcp.Client``).
"""

import asyncio
import json
import os
from contextlib import asynccontextmanager

import pytest

from orbit.models import OrbitEntry

pytest.importorskip("mcp")

# Tools run in the SDK event loop, so the DB must be visible across threads.
pytestmark = pytest.mark.django_db(transaction=True)

EXPECTED_TOOLS = {
    "audit_mcp_exposure",
    "get_recent_requests",
    "get_slow_queries",
    "get_exceptions",
    "get_n1_patterns",
    "search_entries",
    "get_request_detail",
    "get_capture_health",
    "get_stats_summary",
}


def _attr(obj, snake, camel):
    """Read a field that is snake_case in mcp 2.x and camelCase in mcp 1.x."""
    if hasattr(obj, snake):
        return getattr(obj, snake)
    return getattr(obj, camel)


@asynccontextmanager
async def _connected(server):
    """Yield an object with ``list_tools()`` / ``call_tool()`` for either SDK."""
    try:
        from mcp import Client  # mcp 2.x
    except ImportError:
        Client = None

    if Client is not None:
        async with Client(server) as client:
            yield client
    else:
        from mcp.shared.memory import create_connected_server_and_client_session

        async with create_connected_server_and_client_session(
            server._mcp_server
        ) as session:
            yield session


def _run(coro_fn):
    # Orbit's tools use the synchronous ORM inside the SDK's event loop, which is
    # what the orbit_mcp command allows via this variable.
    os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")
    return asyncio.run(coro_fn())


@pytest.fixture
def server():
    from orbit.mcp_server import create_mcp_server

    return create_mcp_server()


@pytest.fixture
def seeded(server):
    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        family_hash="proto123",
        duration_ms=80.0,
        payload={"method": "GET", "path": "/proto/", "status_code": 200},
    )


def test_list_tools_over_protocol(server):
    async def go():
        async with _connected(server) as client:
            return (await client.list_tools()).tools

    tools = _run(go)
    names = {t.name for t in tools}

    assert EXPECTED_TOOLS <= names
    for tool in tools:
        schema = _attr(tool, "input_schema", "inputSchema")
        assert schema["type"] == "object", tool.name
        assert tool.description, tool.name


def test_tools_advertise_read_only_annotation(server):
    async def go():
        async with _connected(server) as client:
            return (await client.list_tools()).tools

    for tool in _run(go):
        assert tool.annotations is not None, tool.name
        assert _attr(tool.annotations, "read_only_hint", "readOnlyHint") is True
        assert _attr(tool.annotations, "destructive_hint", "destructiveHint") is False


def test_call_stats_summary_over_protocol(server, seeded):
    async def go():
        async with _connected(server) as client:
            return await client.call_tool("get_stats_summary", {"hours": 24})

    result = _run(go)

    assert not _attr(result, "is_error", "isError")
    data = json.loads(result.content[0].text)
    assert data["period_hours"] == 24
    assert data["requests"]["total"] == 1


def test_call_recent_requests_over_protocol(server, seeded):
    async def go():
        async with _connected(server) as client:
            return await client.call_tool("get_recent_requests", {"limit": 5})

    result = _run(go)

    assert not _attr(result, "is_error", "isError")
    data = json.loads(result.content[0].text)
    assert data["count"] == 1
    assert data["requests"][0]["family_hash"] == "proto123"


def test_invalid_arguments_report_tool_error(server):
    async def go():
        async with _connected(server) as client:
            try:
                return await client.call_tool("get_stats_summary", {"hours": "x"})
            except Exception as exc:  # some SDK versions raise instead
                return exc

    result = _run(go)

    if isinstance(result, Exception):
        return
    assert _attr(result, "is_error", "isError") is True


@pytest.mark.parametrize("limit", [True, "2", 2.0])
def test_request_summary_rejects_coerced_limits(server, monkeypatch, limit):
    from orbit import evidence

    monkeypatch.setattr(
        evidence, "read_family_evidence", lambda *a, **kw: pytest.fail("No read")
    )

    async def go():
        async with _connected(server) as client:
            try:
                return await client.call_tool(
                    "summarize_request_family",
                    {"family_hash": "abc123", "limit": limit},
                )
            except Exception as exc:  # some SDK versions raise instead
                return exc

    result = _run(go)

    text = str(result) if isinstance(result, Exception) else result.content[0].text
    if not isinstance(result, Exception):
        assert _attr(result, "is_error", "isError") is True
    assert "valid integer" in text
