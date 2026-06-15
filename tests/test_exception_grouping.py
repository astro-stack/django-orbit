"""
Tests for B3 — exception grouping (fingerprint + DB-level aggregation).
"""

import pytest
from django.urls import reverse

from orbit.models import OrbitEntry
from orbit.utils import compute_exception_fingerprint


def _make_exception(exc_type, filename, func, message="boom"):
    info = {
        "exception_type": exc_type,
        "traceback": [{"filename": filename, "name": func, "lineno": 1, "line": "x"}],
    }
    fp = compute_exception_fingerprint(info)
    return OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_EXCEPTION,
        fingerprint=fp,
        payload={
            "exception_type": exc_type,
            "message": message,
            "fingerprint": fp,
            "traceback": info["traceback"],
            "request_path": "/checkout/",
            "request_method": "POST",
        },
    )


@pytest.mark.django_db
def test_fingerprint_is_stable_and_location_sensitive():
    a = compute_exception_fingerprint(
        {"exception_type": "ValueError", "traceback": [{"filename": "a.py", "name": "f"}]}
    )
    # Same type+location, different line/message → same fingerprint
    b = compute_exception_fingerprint(
        {"exception_type": "ValueError", "traceback": [{"filename": "a.py", "name": "f", "lineno": 99}]}
    )
    # Different location → different fingerprint
    c = compute_exception_fingerprint(
        {"exception_type": "ValueError", "traceback": [{"filename": "b.py", "name": "g"}]}
    )
    assert a == b
    assert a != c
    assert len(a) == 16


@pytest.mark.django_db
def test_exception_groups_aggregate_in_db():
    for i in range(3):
        _make_exception("ValueError", "app/views.py", "checkout", f"bad {i}")
    _make_exception("KeyError", "app/api.py", "lookup", "missing")

    groups = list(OrbitEntry.objects.exception_groups())
    assert len(groups) == 2  # two distinct errors
    by_count = sorted(g["count"] for g in groups)
    assert by_count == [1, 3]
    for g in groups:
        assert g["first_seen"] is not None
        assert g["last_seen"] is not None


@pytest.mark.django_db
def test_latest_for_groups_returns_representative():
    e1 = _make_exception("ValueError", "app/views.py", "checkout", "first")
    e2 = _make_exception("ValueError", "app/views.py", "checkout", "second")
    latest = OrbitEntry.objects.latest_for_groups([e1.fingerprint])
    assert e1.fingerprint in latest
    # Most recent occurrence is the representative
    assert latest[e1.fingerprint].id == e2.id


@pytest.mark.django_db
def test_fingerprintless_exceptions_are_not_hidden():
    """Regression: exceptions without a fingerprint must still appear (one group each)."""
    OrbitEntry.objects.create(type=OrbitEntry.TYPE_EXCEPTION, payload={"exception_type": "A", "message": "a"})
    OrbitEntry.objects.create(type=OrbitEntry.TYPE_EXCEPTION, payload={"exception_type": "B", "message": "b"})
    groups = list(OrbitEntry.objects.exception_groups())
    assert len(groups) == 2  # each ungrouped exception is its own group, not hidden
    assert all(g["count"] == 1 for g in groups)


@pytest.mark.django_db
def test_exception_feed_is_grouped(client):
    for i in range(4):
        _make_exception("ValueError", "app/views.py", "checkout", f"bad {i}")
    html = client.get(reverse("orbit:feed"), {"type": "exception"}).content.decode()
    assert "ValueError" in html
    assert "&times;4" in html or "×4" in html  # collapsed count
    # Only one row rendered for the 4 occurrences
    assert html.count('data-entry-id="') == 1


@pytest.mark.django_db
def test_exception_search_falls_back_to_flat_list(client):
    for i in range(3):
        _make_exception("ValueError", "app/views.py", "checkout", f"unique-msg-{i}")
    # Searching shows individual occurrences, not the grouped view
    html = client.get(reverse("orbit:feed"), {"type": "exception", "q": "unique-msg"}).content.decode()
    assert html.count('data-entry-id="') == 3
