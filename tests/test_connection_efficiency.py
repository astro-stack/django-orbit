"""
Connection efficiency tests for Django Orbit (GitHub issue #15).

Orbit was previously exhausting database connections because each watcher
write called connection.introspection.table_names() to check whether the
orbit_orbitentry table existed.  On a busy endpoint, dozens of watcher
events could fire per request, each opening a new introspection query.

Fix: _table_exists() now caches the result in the module-level boolean
_orbit_table_ready after the table is confirmed to exist, so table_names()
is called *at most once* per process lifetime.

This file documents and regression-tests that behaviour.
"""

import pytest
from unittest.mock import patch, call
from django.db import connection
import orbit.watchers as watchers
from orbit.models import OrbitEntry


# ---------------------------------------------------------------------------
# Override conftest autouse fixture for tests that don't need real DB
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_orbit_entries(request):
    if request.node.get_closest_marker("django_db"):
        OrbitEntry.objects.all().delete()
    yield
    if request.node.get_closest_marker("django_db"):
        OrbitEntry.objects.all().delete()


# ---------------------------------------------------------------------------
# Benchmark: table_names() called at most once per process lifetime
# ---------------------------------------------------------------------------

def test_table_names_called_at_most_once_across_burst(monkeypatch):
    """
    Simulates 50 watcher events in rapid succession.
    table_names() must be called exactly once; all subsequent calls use
    the _orbit_table_ready cache.
    """
    monkeypatch.setattr(watchers, "_orbit_table_ready", False)

    call_log = []

    def tracking_table_names(*args, **kwargs):
        call_log.append(1)
        return ["orbit_orbitentry"]

    with patch.object(connection.introspection, "table_names",
                      side_effect=tracking_table_names):
        with patch.object(OrbitEntry.objects, "create"):
            for i in range(50):
                watchers._table_exists()

    assert len(call_log) == 1, (
        f"table_names() was called {len(call_log)} times for 50 _table_exists() "
        "invocations — should be exactly 1 after caching kicks in."
    )


def test_table_names_not_called_when_cache_is_warm(monkeypatch):
    """
    When _orbit_table_ready is already True, table_names() is never called.
    This is the hot path for every request after the first.
    """
    monkeypatch.setattr(watchers, "_orbit_table_ready", True)

    with patch.object(connection.introspection, "table_names") as mock_table_names:
        for _ in range(100):
            watchers._table_exists()

    mock_table_names.assert_not_called()


def test_each_record_function_calls_table_exists_once(monkeypatch):
    """
    Each record_* function must call _table_exists() before writing.
    Verify by patching _table_exists to a counter and asserting it is
    called exactly once per record function invocation.
    """
    call_log = []

    def counting_table_exists():
        call_log.append(1)
        return True  # Table exists — allow write

    monkeypatch.setattr(watchers, "_table_exists", counting_table_exists)

    from django.core.mail import EmailMessage

    with patch.object(OrbitEntry.objects, "create"):
        watchers.record_command("check", (), {}, exit_code=0)
        watchers.record_cache_operation("get", "key", hit=True, duration_ms=1.0)
        watchers.record_http_client_request(
            method="GET", url="https://example.com", status_code=200, duration_ms=10.0
        )
        watchers.record_mail(EmailMessage(subject="s", body="b", to=["a@b.com"]))
        watchers.record_celery_task(
            task_id="x", task_name="t", args=(), kwargs={}, status="success"
        )
        watchers.record_redis_operation(operation="GET", key="k", duration_ms=0.2)
        watchers.record_permission_check(user="u", permission="p", result=True)
        watchers.record_transaction(using="default", duration_ms=2.0, status="committed")

    # 8 calls total; record_signal excluded because RECORD_SIGNALS=False in test config
    assert len(call_log) == 8, (
        f"Expected 8 _table_exists() calls (one per enabled record function), got {len(call_log)}"
    )


def test_no_extra_connections_per_watcher_when_cache_warm(monkeypatch):
    """
    With the cache warm, watcher writes must NOT trigger any
    connection.introspection calls (i.e., zero extra connection probes).
    """
    monkeypatch.setattr(watchers, "_orbit_table_ready", True)

    with patch.object(connection.introspection, "table_names") as mock_tn, \
         patch.object(OrbitEntry.objects, "create"):
        watchers.record_command("check", (), {}, exit_code=0)
        watchers.record_cache_operation("set", "mykey", hit=False, duration_ms=0.5)
        watchers.record_transaction(using="default", duration_ms=1.0, status="committed")

    mock_tn.assert_not_called()


# ---------------------------------------------------------------------------
# Document expected behaviour in a request burst scenario
# ---------------------------------------------------------------------------

def test_burst_of_watcher_events_only_one_introspection_query(monkeypatch):
    """
    Scenario: a single HTTP request triggers many watcher events
    (cache hit, model save, HTTP client call, permission check, etc.)

    Expected: table_names() is called AT MOST ONCE regardless of how many
    watcher events fire, because the result is cached in _orbit_table_ready.

    This documents the fix for GitHub issue #15 (DB connections exhausted).
    """
    monkeypatch.setattr(watchers, "_orbit_table_ready", False)
    introspection_calls = []

    def counting_table_names(*args, **kwargs):
        introspection_calls.append(1)
        return ["orbit_orbitentry"]

    from django.dispatch import Signal

    with patch.object(connection.introspection, "table_names",
                      side_effect=counting_table_names), \
         patch.object(OrbitEntry.objects, "create"):

        # Simulate a busy request: cache ops, model events, permission checks, HTTP calls
        for _ in range(10):
            watchers.record_cache_operation("get", f"key_{_}", hit=True, duration_ms=0.1)
        for _ in range(5):
            watchers.record_http_client_request(
                method="GET", url=f"https://example.com/{_}",
                status_code=200, duration_ms=20.0
            )
        for _ in range(5):
            watchers.record_permission_check(
                user="alice", permission=f"app.perm_{_}", result=True
            )
        for _ in range(3):
            watchers.record_transaction(
                using="default", duration_ms=float(_), status="committed"
            )

    assert len(introspection_calls) == 1, (
        f"23 watcher events triggered {len(introspection_calls)} introspection queries "
        "— expected exactly 1. Without caching this would be 23, exhausting connections."
    )
