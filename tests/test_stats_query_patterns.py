import pytest

from orbit.models import OrbitEntry
from orbit.stats import get_database_metrics


def _pattern(kind, confidence="high"):
    return {
        "kind": kind,
        "confidence": confidence,
        "occurrences": 5,
        "query_summary": "SELECT review WHERE book_id = ?",
    }


@pytest.mark.django_db
def test_database_metrics_separate_duplicates_from_n_plus_one():
    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_QUERY,
        payload={"is_duplicate": True, "sql": "SELECT 1"},
        duration_ms=1,
    )
    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        payload={
            "path": "/duplicate-only/",
            "duplicate_query_count": 4,
            "n_plus_one_count": 0,
            "query_patterns": [_pattern("exact_duplicate")],
        },
    )
    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        payload={
            "path": "/books/",
            "duplicate_query_count": 4,
            "n_plus_one_count": 2,
            "query_patterns": [
                _pattern("n_plus_one_candidate"),
                _pattern("per_row_aggregate_candidate", confidence="medium"),
            ],
        },
    )

    metrics = get_database_metrics("24h")

    assert metrics["duplicate_query_executions"] == 1
    assert metrics["duplicate_only_requests"] == 1
    assert metrics["n_plus_one_requests"] == 1
    assert metrics["n_plus_one_findings"] == 2
    assert metrics["n_plus_one_by_kind"] == {
        "n_plus_one_candidate": 1,
        "per_row_aggregate_candidate": 1,
    }
    assert metrics["n_plus_one_by_confidence"] == {"high": 1, "medium": 1}


@pytest.mark.django_db
def test_database_metrics_ignore_malformed_patterns_and_support_legacy_requests():
    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        payload={
            "path": "/legacy/",
            "duplicate_query_count": 3,
            "query_patterns": "not-a-list",
        },
    )

    metrics = get_database_metrics("24h")

    assert metrics["duplicate_only_requests"] == 1
    assert metrics["n_plus_one_requests"] == 0
    assert metrics["n_plus_one_findings"] == 0


@pytest.mark.django_db
def test_database_stats_fragment_labels_n_plus_one_and_duplicates_separately(client):
    response = client.get("/orbit/stats/section/database/?range=24h")
    html = response.content.decode()

    assert response.status_code == 200
    assert "N+1 Requests" in html
    assert "N+1 Findings" in html
    assert "Duplicate Executions" in html
    assert "Duplicate-only Requests" in html
