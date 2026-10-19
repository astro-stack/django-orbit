from django.db import connection
from django.test.utils import CaptureQueriesContext

import pytest

from orbit.explorer import exception_group_page
from orbit.models import OrbitEntry


def _make_exception(index, message="boom"):
    fingerprint = f"fp-{index}"
    return OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_EXCEPTION,
        fingerprint=fingerprint,
        payload={"exception_type": "ValueError", "message": message},
    )


def _group_page_query_count(group_count):
    OrbitEntry.objects.filter(type=OrbitEntry.TYPE_EXCEPTION).delete()
    for index in range(group_count):
        _make_exception(index)
        _make_exception(index)
    with CaptureQueriesContext(connection) as queries:
        groups, total = exception_group_page(OrbitEntry.objects.all(), 1, 100)
    assert total == group_count
    assert len(groups) == group_count
    return len(queries)


@pytest.mark.django_db
def test_exception_group_page_query_count_independent_of_group_count():
    assert _group_page_query_count(3) == _group_page_query_count(10)


@pytest.mark.django_db
def test_latest_for_groups_respects_base_queryset():
    old = _make_exception(1, "old")
    _make_exception(1, "new")
    scoped = OrbitEntry.objects.filter(id=old.id)
    latest = OrbitEntry.objects.latest_for_groups(["fp-1"], scoped)
    assert latest["fp-1"].id == old.id


@pytest.mark.django_db
def test_latest_for_groups_empty_keys_runs_no_query():
    with CaptureQueriesContext(connection) as queries:
        assert OrbitEntry.objects.latest_for_groups([]) == {}
    assert len(queries) == 0
