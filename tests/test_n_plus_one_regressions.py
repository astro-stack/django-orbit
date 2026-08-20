from django.urls import reverse

import pytest

from orbit.models import OrbitEntry

pytestmark = pytest.mark.django_db


def _finding(caller_key="/app/orders/views.py:42:list_orders"):
    return {
        "kind": "n_plus_one_candidate",
        "confidence": "high",
        "query_summary": "SELECT authors",
        "caller_key": caller_key,
        "occurrences": 4,
        "unique_parameter_sets": 4,
        "total_duration_ms": 12.0,
        "evidence": ["same_query_shape", "varying_parameters"],
    }


def test_historical_request_without_n1_key_cannot_outrank_candidate():
    from orbit.agentic import find_n_plus_one_candidates

    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        family_hash="historical",
        payload={
            "path": "/historical/",
            "duplicate_query_count": 100,
        },
    )
    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        family_hash="classified",
        payload={
            "path": "/classified/",
            "duplicate_query_count": 3,
            "n_plus_one_count": 1,
            "query_patterns": [_finding()],
        },
    )

    data = find_n_plus_one_candidates(hours=72, limit=1)

    assert data["candidates"][0]["family_hash"] == "classified"


@pytest.mark.parametrize(
    "caller_key",
    [
        "C:/Users/alice/app.py:10:run",
        "/home/alice/app.py:10:run",
    ],
)
def test_agent_safe_finding_reduces_shallow_paths_to_basename(caller_key):
    from orbit.agentic import agent_safe_serialize_query_finding

    serialized = agent_safe_serialize_query_finding(_finding(caller_key))

    assert serialized["caller_key"] == "app.py:10:run"
    assert "alice" not in str(serialized)


def test_feed_distinguishes_n_plus_one_from_duplicate_only(client):
    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        family_hash="feed-n1",
        payload={
            "method": "GET",
            "path": "/feed-n1/",
            "status_code": 200,
            "duplicate_query_count": 3,
            "n_plus_one_count": 1,
            "query_patterns": [_finding()],
        },
    )

    html = client.get(reverse("orbit:feed"), {"type": "request"}).content.decode()

    assert "N+1" in html


def test_malformed_query_patterns_are_ignored_by_agentic_and_detail(client):
    from orbit.agentic import find_n_plus_one_candidates

    request = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        family_hash="malformed-patterns",
        payload={
            "method": "GET",
            "path": "/malformed/",
            "status_code": 200,
            "duplicate_query_count": 2,
            "query_patterns": ["broken", None, 42],
        },
    )

    data = find_n_plus_one_candidates(hours=72)
    html = client.get(reverse("orbit:detail", args=[request.id]))

    candidate = next(
        item
        for item in data["candidates"]
        if item["family_hash"] == "malformed-patterns"
    )
    assert candidate["classification"] == "duplicate_only"
    assert candidate["query_patterns"] == []
    assert html.status_code == 200
