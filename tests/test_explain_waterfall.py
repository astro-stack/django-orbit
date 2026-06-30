"""
Tests for B2 (query EXPLAIN) and B4 (request waterfall).
"""

from django.urls import reverse

import pytest

from orbit.explain import explain_query
from orbit.models import OrbitEntry

pytestmark = pytest.mark.django_db


# ---- B2: EXPLAIN ----------------------------------------------------------


def test_explain_select_returns_plan():
    result = explain_query("SELECT * FROM orbit_orbitentry")
    assert result["supported"] is True
    assert result["vendor"] == "sqlite"
    assert result.get("plan")  # non-empty list of plan lines
    assert "error" not in result


def test_explain_empty_sql_unsupported():
    assert explain_query("")["supported"] is False


def test_explain_view_on_query_entry(client):
    entry = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_QUERY,
        payload={"sql": "SELECT * FROM orbit_orbitentry", "params": []},
    )
    html = client.get(reverse("orbit:explain", args=[entry.id])).content.decode()
    assert "sqlite" in html.lower()
    assert 'data-orbit-explain-status="success"' in html


def test_explain_view_rejects_non_query(client):
    entry = OrbitEntry.objects.create(type=OrbitEntry.TYPE_DUMP, payload={"x": 1})
    html = client.get(reverse("orbit:explain", args=[entry.id])).content.decode()
    assert "no sql" in html.lower()


def test_explain_disabled_by_config(client, settings):
    settings.ORBIT_CONFIG = {
        **getattr(settings, "ORBIT_CONFIG", {}),
        "ENABLE_EXPLAIN": False,
    }
    entry = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_QUERY, payload={"sql": "SELECT 1", "params": []}
    )
    html = client.get(reverse("orbit:explain", args=[entry.id])).content.decode()
    assert "disabled" in html.lower()
    assert 'data-orbit-explain-status="error"' in html


# ---- B4: waterfall --------------------------------------------------------


def _request_with_queries(family="famX"):
    req = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        family_hash=family,
        duration_ms=100.0,
        payload={"method": "GET", "full_path": "/x/", "status_code": 200},
    )
    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_QUERY,
        family_hash=family,
        duration_ms=20.0,
        payload={"sql": "SELECT 1", "start_offset_ms": 10.0, "is_slow": False},
    )
    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_QUERY,
        family_hash=family,
        duration_ms=40.0,
        payload={"sql": "SELECT 2", "start_offset_ms": 50.0, "is_slow": False},
    )
    return req


def test_waterfall_built_for_request():
    from orbit.views import OrbitDetailPartial

    req = _request_with_queries()
    related = list(OrbitEntry.objects.filter(family_hash="famX").exclude(id=req.id))
    wf = OrbitDetailPartial._build_waterfall(req, related)
    assert wf["count"] == 2
    assert wf["total_ms"] == 100.0
    # second query starts at 50% and is 40% wide
    spans = sorted(wf["spans"], key=lambda s: s["left"])
    assert spans[0]["left"] == 10.0 and spans[0]["width"] == 20.0
    assert spans[1]["left"] == 50.0 and spans[1]["width"] == 40.0


def test_waterfall_none_for_non_request():
    e = OrbitEntry.objects.create(type=OrbitEntry.TYPE_QUERY, duration_ms=5, payload={})
    from orbit.views import OrbitDetailPartial

    assert OrbitDetailPartial._build_waterfall(e, []) is None


def test_request_detail_renders_timeline(client):
    req = _request_with_queries()
    html = client.get(reverse("orbit:detail", args=[req.id])).content.decode()
    assert "Query timeline" in html
