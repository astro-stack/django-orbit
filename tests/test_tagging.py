"""
Tests for B1 — tagging + tag search.
"""

import pytest
from django.urls import reverse

from orbit.models import OrbitEntry
from orbit.utils import normalize_tags, parse_tags

pytestmark = pytest.mark.django_db


def test_normalize_and_parse_roundtrip():
    assert normalize_tags(["slow", "checkout"]) == ",slow,checkout,"
    assert normalize_tags([]) == ""
    assert normalize_tags(["a", "a", " b "]) == ",a,b,"  # dedupe + strip
    assert parse_tags(",slow,checkout,") == ["slow", "checkout"]
    assert parse_tags("") == []


def test_tag_list_property():
    e = OrbitEntry.objects.create(type=OrbitEntry.TYPE_DUMP, tags=",x,y,", payload={})
    assert e.tag_list == ["x", "y"]


def test_tag_callback_applied_on_save(settings):
    settings.ORBIT_CONFIG = {
        **getattr(settings, "ORBIT_CONFIG", {}),
        "TAG_CALLBACK": lambda entry: ["auto", entry.type],
    }
    e = OrbitEntry.objects.create(type=OrbitEntry.TYPE_REQUEST, payload={})
    assert set(e.tag_list) == {"auto", "request"}


def test_tag_callback_failure_never_breaks_save(settings):
    def boom(entry):
        raise RuntimeError("nope")

    settings.ORBIT_CONFIG = {**getattr(settings, "ORBIT_CONFIG", {}), "TAG_CALLBACK": boom}
    e = OrbitEntry.objects.create(type=OrbitEntry.TYPE_DUMP, payload={})
    assert e.pk is not None  # saved despite callback error


def test_feed_filter_by_tag_param(client):
    OrbitEntry.objects.create(type=OrbitEntry.TYPE_DUMP, tags=",checkout,", payload={"x": 1})
    OrbitEntry.objects.create(type=OrbitEntry.TYPE_DUMP, tags=",other,", payload={"x": 2})
    html = client.get(reverse("orbit:feed"), {"type": "dump", "tag": "checkout"}).content.decode()
    assert html.count('data-entry-id="') == 1


def test_feed_tag_search_prefix(client):
    OrbitEntry.objects.create(type=OrbitEntry.TYPE_DUMP, tags=",checkout,", payload={"x": 1})
    OrbitEntry.objects.create(type=OrbitEntry.TYPE_DUMP, tags=",other,", payload={"x": 2})
    html = client.get(reverse("orbit:feed"), {"q": "tag:checkout"}).content.decode()
    assert html.count('data-entry-id="') == 1


def test_tag_filter_does_not_partial_match(client):
    # ",check," must not match a "checkout" tag (comma-wrapping prevents substrings)
    OrbitEntry.objects.create(type=OrbitEntry.TYPE_DUMP, tags=",checkout,", payload={})
    html = client.get(reverse("orbit:feed"), {"type": "dump", "tag": "check"}).content.decode()
    assert 'data-entry-id="' not in html
