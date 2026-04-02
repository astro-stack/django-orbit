"""
Test that all watcher record functions silently skip writes when the
orbit_orbitentry table does not yet exist (e.g. during `manage.py migrate`
on a fresh PostgreSQL database).

Regression test for GitHub issue #16.
"""

import pytest
from unittest.mock import patch
from django.test import override_settings
from orbit.models import OrbitEntry
import orbit.watchers as watchers


# ---------------------------------------------------------------------------
# _table_exists() unit tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_table_exists_returns_false_when_table_missing(monkeypatch):
    """_table_exists() must return False when the table is absent."""
    monkeypatch.setattr(watchers, "_orbit_table_ready", False)
    from django.db import connection
    with patch.object(connection.introspection, "table_names", return_value=[]):
        result = watchers._table_exists()
    assert result is False
    assert watchers._orbit_table_ready is False


@pytest.mark.django_db
def test_table_exists_returns_true_when_table_present(monkeypatch):
    """_table_exists() must return True and cache the flag."""
    monkeypatch.setattr(watchers, "_orbit_table_ready", False)
    from django.db import connection
    with patch.object(connection.introspection, "table_names",
                      return_value=["orbit_orbitentry"]):
        result = watchers._table_exists()
    assert result is True
    assert watchers._orbit_table_ready is True


@pytest.mark.django_db
def test_table_exists_caches_result_once_true(monkeypatch):
    """Once the table is found, introspection is never called again."""
    monkeypatch.setattr(watchers, "_orbit_table_ready", False)
    call_count = []

    from django.db import connection

    def counting_table_names(*args, **kwargs):
        call_count.append(1)
        return ["orbit_orbitentry"]

    with patch.object(connection.introspection, "table_names",
                      side_effect=counting_table_names):
        watchers._table_exists()
        watchers._table_exists()
        watchers._table_exists()

    assert len(call_count) == 1, "introspection should be called at most once after caching"


# ---------------------------------------------------------------------------
# Helpers: assert OrbitEntry.objects.create is/isn't called
# (no real DB writes — avoids interference from conftest autouse fixtures)
# ---------------------------------------------------------------------------

def _assert_no_db_write(fn, *args, **kwargs):
    with patch.object(OrbitEntry.objects, "create") as mock_create:
        fn(*args, **kwargs)
    mock_create.assert_not_called()


def _assert_db_write_attempted(fn, *args, **kwargs):
    with patch.object(OrbitEntry.objects, "create") as mock_create:
        fn(*args, **kwargs)
    mock_create.assert_called_once()


# ---------------------------------------------------------------------------
# Override the conftest autouse fixture so non-django_db tests are not blocked
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_orbit_entries(request):
    """Override conftest clean_orbit_entries for this module.

    Tests in this file that are marked with django_db still get DB cleanup;
    tests that mock at the ORM level and don't need a real DB are left alone.
    """
    if request.node.get_closest_marker("django_db"):
        OrbitEntry.objects.all().delete()
    yield
    if request.node.get_closest_marker("django_db"):
        OrbitEntry.objects.all().delete()


# ---------------------------------------------------------------------------
# record_* must skip writes when the table is missing
# ---------------------------------------------------------------------------

def test_record_command_skips_when_table_missing(monkeypatch):
    monkeypatch.setattr(watchers, "_table_exists", lambda: False)
    _assert_no_db_write(watchers.record_command, "migrate", (), {}, exit_code=0)


def test_record_cache_operation_skips_when_table_missing(monkeypatch):
    monkeypatch.setattr(watchers, "_table_exists", lambda: False)
    _assert_no_db_write(watchers.record_cache_operation,
                        "get", "key", hit=False, duration_ms=1.0)


def test_record_model_event_skips_when_table_missing(monkeypatch):
    monkeypatch.setattr(watchers, "_table_exists", lambda: False)
    from django.contrib.auth import get_user_model
    _assert_no_db_write(watchers.record_model_event,
                        sender=get_user_model(), instance=None, action="create")


def test_record_http_client_request_skips_when_table_missing(monkeypatch):
    monkeypatch.setattr(watchers, "_table_exists", lambda: False)
    _assert_no_db_write(watchers.record_http_client_request,
                        method="GET", url="https://example.com",
                        status_code=200, duration_ms=50.0)


def test_record_mail_skips_when_table_missing(monkeypatch):
    monkeypatch.setattr(watchers, "_table_exists", lambda: False)
    from django.core.mail import EmailMessage
    msg = EmailMessage(subject="Test", body="Hello", to=["a@b.com"])
    _assert_no_db_write(watchers.record_mail, msg)


def test_record_signal_skips_when_table_missing(monkeypatch):
    monkeypatch.setattr(watchers, "_table_exists", lambda: False)
    from django.dispatch import Signal
    _assert_no_db_write(watchers.record_signal, Signal(), sender=None)


def test_record_celery_task_skips_when_table_missing(monkeypatch):
    monkeypatch.setattr(watchers, "_table_exists", lambda: False)
    _assert_no_db_write(watchers.record_celery_task,
                        task_id="abc123", task_name="myapp.tasks.do_work",
                        args=(), kwargs={}, status="success", duration_ms=10.0)


def test_record_redis_operation_skips_when_table_missing(monkeypatch):
    monkeypatch.setattr(watchers, "_table_exists", lambda: False)
    _assert_no_db_write(watchers.record_redis_operation,
                        operation="GET", key="mykey", duration_ms=0.5)


def test_record_permission_check_skips_when_table_missing(monkeypatch):
    monkeypatch.setattr(watchers, "_table_exists", lambda: False)
    _assert_no_db_write(watchers.record_permission_check,
                        user="user@example.com",
                        permission="myapp.view_thing",
                        result=True)


def test_record_transaction_skips_when_table_missing(monkeypatch):
    monkeypatch.setattr(watchers, "_table_exists", lambda: False)
    _assert_no_db_write(watchers.record_transaction,
                        using="default", duration_ms=5.0, status="committed")


# ---------------------------------------------------------------------------
# Sanity check: writes ARE attempted when the table exists
# ---------------------------------------------------------------------------

def test_record_command_attempts_write_when_table_present(monkeypatch):
    monkeypatch.setattr(watchers, "_table_exists", lambda: True)
    _assert_db_write_attempted(watchers.record_command, "check", (), {}, exit_code=0)


def test_record_http_client_request_attempts_write_when_table_present(monkeypatch):
    monkeypatch.setattr(watchers, "_table_exists", lambda: True)
    _assert_db_write_attempted(watchers.record_http_client_request,
                                method="POST", url="https://api.example.com/data",
                                status_code=201, duration_ms=80.0)


@override_settings(ORBIT_CONFIG={"ENABLED": True, "RECORD_TRANSACTIONS": True})
def test_record_transaction_attempts_write_when_table_present(monkeypatch):
    monkeypatch.setattr(watchers, "_table_exists", lambda: True)
    _assert_db_write_attempted(watchers.record_transaction,
                                using="default", duration_ms=3.0, status="committed")
