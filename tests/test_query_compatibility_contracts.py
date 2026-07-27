"""Public compatibility contracts for duplicate and N+1 investigation."""

import json

import pytest
from django.urls import reverse

from orbit.models import OrbitEntry

pytestmark = pytest.mark.django_db


def _get_n1_patterns(**kwargs):
    from orbit.mcp_server import create_mcp_server

    server = create_mcp_server()
    tool = server._tool_manager._tools["get_n1_patterns"]
    return json.loads(tool.fn(**kwargs))


def test_mcp_keeps_historical_duplicate_only_requests_visible():
    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        family_hash="historical-duplicate",
        payload={"path": "/legacy/", "duplicate_query_count": 4},
    )

    data = _get_n1_patterns()

    assert data["count"] == 1
    assert data["n1_patterns"][0]["classification"] == "duplicate_only"
    assert data["n1_patterns"][0]["duplicate_query_count"] == 4


def test_duplicate_query_detail_is_scoped_to_its_request_family(client):
    sql = "SELECT * FROM demo_review WHERE book_id = %s"
    selected = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_QUERY,
        family_hash="request-a",
        payload={"sql": sql, "is_duplicate": True},
    )
    same_family = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_QUERY,
        family_hash="request-a",
        payload={"sql": sql, "is_duplicate": True},
    )
    other_family = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_QUERY,
        family_hash="request-b",
        payload={"sql": sql, "is_duplicate": True},
    )

    response = client.get(reverse("orbit:detail", args=[selected.id]))
    duplicates = list(response.context_data["duplicate_entries"])

    assert [entry.id for entry in duplicates] == [same_family.id]
    assert other_family.id not in [entry.id for entry in duplicates]
