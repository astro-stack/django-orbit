import uuid

from django.http import HttpResponse
from django.test import RequestFactory, override_settings

import pytest

from orbit.middleware import OrbitMiddleware
from orbit.models import OrbitEntry
from orbit.recorders import OrbitQueryWrapper

pytestmark = pytest.mark.django_db


def test_query_wrapper_adds_safe_signature_evidence():
    wrapper = OrbitQueryWrapper(family_hash="fam-wrapper")

    def execute(sql, params, many, context):
        return object()

    wrapper(
        execute,
        "SELECT * FROM users WHERE email = %s",
        ["private@example.com"],
        False,
        {"alias": "default"},
    )

    query = wrapper.queries[0]
    assert query["query_signature_version"] == 1
    assert query["query_signature"]
    assert query["parameter_shape"] == ["str"]
    assert query["sequence_index"] == 0
    assert "private@example.com" not in query["parameter_fingerprint"]


@override_settings(
    ORBIT_CONFIG={
        "N_PLUS_ONE_ENABLED": True,
        "N_PLUS_ONE_MIN_OCCURRENCES": 4,
        "N_PLUS_ONE_MAX_QUERIES": 100,
        "STORAGE_LIMIT": 1000,
    }
)
def test_middleware_persists_n_plus_one_findings():
    def get_response(request):
        for _ in range(4):
            OrbitEntry.objects.filter(id=uuid.uuid4()).exists()
        return HttpResponse("ok")

    request = RequestFactory().get("/n-plus-one-probe/")
    response = OrbitMiddleware(get_response)(request)

    captured = (
        OrbitEntry.objects.requests()
        .filter(payload__path="/n-plus-one-probe/")
        .latest("created_at")
    )

    assert response.status_code == 200
    assert captured.payload["duplicate_query_count"] == 3
    assert captured.payload["n_plus_one_count"] == 1
    assert captured.payload["query_patterns"][0]["kind"] == "n_plus_one_candidate"
    assert captured.payload["query_patterns"][0]["confidence"] == "high"


@override_settings(
    ORBIT_CONFIG={
        "N_PLUS_ONE_ENABLED": False,
        "STORAGE_LIMIT": 1000,
    }
)
def test_middleware_can_disable_pattern_analysis():
    def get_response(request):
        for _ in range(4):
            OrbitEntry.objects.filter(id=uuid.uuid4()).exists()
        return HttpResponse("ok")

    request = RequestFactory().get("/disabled-n-plus-one-probe/")
    OrbitMiddleware(get_response)(request)

    captured = (
        OrbitEntry.objects.requests()
        .filter(payload__path="/disabled-n-plus-one-probe/")
        .latest("created_at")
    )

    assert captured.payload["duplicate_query_count"] == 3
    assert captured.payload["query_patterns"] == []
    assert captured.payload["n_plus_one_count"] == 0
