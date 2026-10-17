from django.urls import reverse

import pytest

from orbit.models import OrbitEntry

pytestmark = pytest.mark.django_db


def test_metrics_share_type_and_filter_scope_and_count_exception_occurrences(client):
    OrbitEntry.objects.create(
        type="request", duration_ms=0, payload={"path": "/x/", "status_code": 500}
    )
    OrbitEntry.objects.create(type="exception", payload={"request_path": "/x/"})
    OrbitEntry.objects.create(type="exception", payload={"request_path": "/x/"})
    OrbitEntry.objects.create(
        type="query", duration_ms=50, payload={"is_slow": True, "is_duplicate": True}
    )
    response = client.get(reverse("orbit:feed"), {"path": "x"})
    metrics = response.context_data["explorer_metrics"]
    assert metrics["request_count"] == 1
    assert metrics["failed_request_count"] == 1
    assert metrics["exception_count"] == 2
    assert metrics["query_count"] == 0
    assert metrics["avg_response_time"] == 0
    assert metrics["error_rate_pct"] == 100


def test_metrics_empty_avg_is_null(client):
    response = client.get(reverse("orbit:feed"))
    metrics = response.context_data["explorer_metrics"]
    assert metrics["entry_count"] == 0
    assert metrics["avg_response_time"] is None
