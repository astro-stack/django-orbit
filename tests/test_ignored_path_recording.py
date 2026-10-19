"""Watcher events raised while serving an ignored path must not be recorded."""

from django.http import HttpResponse
from django.test import RequestFactory

import pytest

from orbit.middleware import OrbitMiddleware
from orbit.models import OrbitEntry
from orbit.watchers import _recording_suspended, record_storage_operation


def _storage_lookup_view(request):
    # Mimics staticfiles finders checking for an asset during the request.
    record_storage_operation(
        "exists", "orbit/vendor/htmx.min.js", "FileSystem", 0.1, exists=True
    )
    return HttpResponse("ok")


@pytest.mark.django_db
def test_ignored_path_suppresses_watcher_events():
    middleware = OrbitMiddleware(_storage_lookup_view)

    middleware(RequestFactory().get("/static/orbit/vendor/htmx.min.js"))

    assert not OrbitEntry.objects.filter(type=OrbitEntry.TYPE_STORAGE).exists()
    assert _recording_suspended.get() is False


@pytest.mark.django_db
def test_recorded_path_keeps_watcher_events():
    middleware = OrbitMiddleware(_storage_lookup_view)

    middleware(RequestFactory().get("/checkout/"))

    assert OrbitEntry.objects.filter(type=OrbitEntry.TYPE_STORAGE).count() == 1
