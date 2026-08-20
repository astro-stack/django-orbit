import uuid

from django.http import HttpResponse
from django.test import RequestFactory, override_settings
from django.urls import reverse

import pytest

from orbit.middleware import OrbitMiddleware
from orbit.models import OrbitEntry
from orbit.query_analysis import analyze_query_patterns, build_query_evidence

pytestmark = pytest.mark.django_db


def _pattern(kind="n_plus_one_candidate", caller_key=None):
    return {
        "schema_version": 1,
        "kind": kind,
        "confidence": "high",
        "query_signature": "shape-1",
        "query_summary": "SELECT authors",
        "operation": "SELECT",
        "database": "default",
        "caller_key": caller_key,
        "occurrences": 4,
        "avoidable_executions": 3,
        "unique_parameter_sets": 4,
        "total_duration_ms": 12.0,
        "evidence": ["same_query_shape", "varying_parameters"],
        "counter_evidence": [],
        "capture_limits": [],
    }


def test_invalid_analysis_limits_fall_back_without_raising():
    queries = []
    for item_id in range(4):
        evidence = build_query_evidence(
            "SELECT * FROM products WHERE id = %s",
            [item_id],
            caller_key="/app/views.py:10:list_products",
        )
        queries.append(
            {
                "sql": "SELECT * FROM products WHERE id = %s",
                "params": [item_id],
                "duration_ms": 1,
                **evidence,
            }
        )

    findings = analyze_query_patterns(
        queries,
        min_occurrences="invalid",
        max_queries=None,
    )

    assert findings[0]["kind"] == "n_plus_one_candidate"


@override_settings(
    ORBIT_CONFIG={
        "N_PLUS_ONE_ENABLED": True,
        "N_PLUS_ONE_MIN_OCCURRENCES": "invalid",
        "N_PLUS_ONE_MAX_QUERIES": None,
        "STORAGE_LIMIT": 1000,
    }
)
def test_invalid_n_plus_one_config_never_breaks_host_request():
    def get_response(request):
        for _ in range(4):
            OrbitEntry.objects.filter(id=uuid.uuid4()).exists()
        return HttpResponse("ok")

    response = OrbitMiddleware(get_response)(
        RequestFactory().get("/invalid-n-plus-one-config/")
    )

    assert response.status_code == 200
    assert (
        OrbitEntry.objects.requests()
        .filter(payload__path="/invalid-n-plus-one-config/")
        .exists()
    )


def test_agentic_ranking_prioritizes_classified_candidate_over_duplicates():
    from orbit.agentic import find_n_plus_one_candidates

    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        family_hash="duplicate-heavy",
        duration_ms=100,
        payload={
            "method": "GET",
            "path": "/duplicate-heavy/",
            "duplicate_query_count": 100,
            "n_plus_one_count": 0,
            "query_patterns": [_pattern("exact_duplicate")],
        },
    )
    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        family_hash="classified-n1",
        duration_ms=20,
        payload={
            "method": "GET",
            "path": "/classified/",
            "duplicate_query_count": 3,
            "n_plus_one_count": 1,
            "query_patterns": [_pattern()],
        },
    )

    data = find_n_plus_one_candidates(hours=72, limit=1)

    assert data["candidates"][0]["family_hash"] == "classified-n1"
    assert data["candidates"][0]["classification"] == "n_plus_one_candidate"


def test_agent_safe_finding_does_not_expose_absolute_caller_path():
    from orbit.agentic import agent_safe_serialize_query_finding

    finding = _pattern(
        caller_key="C:/Users/private-user/work/project/orders/views.py:42:list"
    )

    serialized = agent_safe_serialize_query_finding(finding)

    assert "private-user" not in str(serialized)
    assert serialized["caller_key"] == "views.py:42:list"


def test_request_detail_renders_n_plus_one_confidence(client):
    request = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        family_hash="visible-n1",
        payload={
            "method": "GET",
            "path": "/visible/",
            "duplicate_query_count": 3,
            "n_plus_one_count": 1,
            "query_patterns": [_pattern()],
        },
    )

    html = client.get(reverse("orbit:detail", args=[request.id])).content.decode()

    assert "Probable N+1" in html
    assert "high confidence" in html
    assert "SELECT authors" in html
