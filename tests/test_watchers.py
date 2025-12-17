import pytest

from orbit.helpers import dump
from orbit.models import OrbitEntry


@pytest.mark.django_db
def test_dump_helper():
    """Test that dump() creates an OrbitEntry."""
    dump("hello", {"a": 1})

    assert OrbitEntry.objects.count() == 1
    entry = OrbitEntry.objects.first()
    assert entry.type == OrbitEntry.TYPE_DUMP

    # Check payload structure
    payload = entry.payload
    assert len(payload["values"]) == 2
    assert payload["values"][0]["type"] == "str"
    assert payload["values"][0]["value"] == "hello"


@pytest.mark.django_db
def test_dump_manager():
    """Test the dumps() manager method."""
    dump("test1")
    OrbitEntry.objects.create(type=OrbitEntry.TYPE_REQUEST, payload={})
    dump("test2")

    assert OrbitEntry.objects.count() == 3
    assert OrbitEntry.objects.dumps().count() == 2
