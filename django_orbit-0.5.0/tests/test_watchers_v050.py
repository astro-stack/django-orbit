"""
Tests for Django Orbit v0.5.0 watchers.

Tests for:
- Celery Jobs
- Django-Q Jobs
- RQ Jobs
- APScheduler Jobs
- django-celery-beat
- Redis operations
- Gates/Permissions
"""

import pytest
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings


class TestCeleryJobWatcher(TestCase):
    """Test Celery job watcher."""

    @override_settings(ORBIT_CONFIG={"ENABLED": True, "RECORD_JOBS": True})
    def test_record_celery_task_success(self):
        """Test recording a successful Celery task."""
        from orbit.watchers import record_celery_task
        from orbit.models import OrbitEntry

        initial_count = OrbitEntry.objects.jobs().count()

        record_celery_task(
            task_id="test-task-123",
            task_name="myapp.tasks.send_email",
            args=("arg1", "arg2"),
            kwargs={"key": "value"},
            status="success",
            result="Email sent",
            duration_ms=150.5,
            retries=0,
        )

        assert OrbitEntry.objects.jobs().count() == initial_count + 1
        entry = OrbitEntry.objects.jobs().last()
        assert entry.payload["task_id"] == "test-task-123"
        assert entry.payload["name"] == "myapp.tasks.send_email"
        assert entry.payload["status"] == "success"
        assert entry.duration_ms == 150.5

    @override_settings(ORBIT_CONFIG={"ENABLED": True, "RECORD_JOBS": True})
    def test_record_celery_task_failure(self):
        """Test recording a failed Celery task."""
        from orbit.watchers import record_celery_task
        from orbit.models import OrbitEntry

        record_celery_task(
            task_id="test-task-456",
            task_name="myapp.tasks.process_payment",
            args=(),
            kwargs={},
            status="failure",
            exception="ConnectionError: Payment gateway unavailable",
            duration_ms=500.0,
            retries=2,
        )

        entry = OrbitEntry.objects.jobs().last()
        assert entry.payload["status"] == "failure"
        assert "ConnectionError" in entry.payload["error"]
        assert entry.payload["retries"] == 2

    @override_settings(ORBIT_CONFIG={"ENABLED": True, "RECORD_JOBS": False})
    def test_record_celery_task_disabled(self):
        """Test that jobs are not recorded when disabled."""
        from orbit.watchers import record_celery_task
        from orbit.models import OrbitEntry

        initial_count = OrbitEntry.objects.jobs().count()

        record_celery_task(
            task_id="test-disabled",
            task_name="test.task",
            args=(),
            kwargs={},
            status="success",
            duration_ms=100,
        )

        assert OrbitEntry.objects.jobs().count() == initial_count


class TestRedisWatcher(TestCase):
    """Test Redis watcher."""

    @override_settings(ORBIT_CONFIG={"ENABLED": True, "RECORD_REDIS": True})
    def test_record_redis_operation(self):
        """Test recording a Redis operation."""
        from orbit.watchers import record_redis_operation
        from orbit.models import OrbitEntry

        initial_count = OrbitEntry.objects.redis_ops().count()

        record_redis_operation(
            operation="GET",
            key="user:123:profile",
            duration_ms=2.5,
            result_size=256,
        )

        assert OrbitEntry.objects.redis_ops().count() == initial_count + 1
        entry = OrbitEntry.objects.redis_ops().last()
        assert entry.payload["operation"] == "GET"
        assert entry.payload["key"] == "user:123:profile"
        assert entry.payload["result_size"] == 256

    @override_settings(ORBIT_CONFIG={"ENABLED": True, "RECORD_REDIS": True})
    def test_record_redis_error(self):
        """Test recording a Redis operation with error."""
        from orbit.watchers import record_redis_operation
        from orbit.models import OrbitEntry

        record_redis_operation(
            operation="SET",
            key="test:key",
            error="Connection refused",
            duration_ms=5000,
        )

        entry = OrbitEntry.objects.redis_ops().last()
        assert entry.payload["error"] == "Connection refused"

    @override_settings(ORBIT_CONFIG={"ENABLED": True, "RECORD_REDIS": False})
    def test_record_redis_disabled(self):
        """Test that Redis ops are not recorded when disabled."""
        from orbit.watchers import record_redis_operation
        from orbit.models import OrbitEntry

        initial_count = OrbitEntry.objects.redis_ops().count()

        record_redis_operation(
            operation="GET",
            key="test:key",
            duration_ms=1.0,
        )

        assert OrbitEntry.objects.redis_ops().count() == initial_count


class TestGatesWatcher(TestCase):
    """Test Gates/Permissions watcher."""

    @override_settings(ORBIT_CONFIG={"ENABLED": True, "RECORD_GATES": True})
    def test_record_permission_granted(self):
        """Test recording a granted permission check."""
        from orbit.watchers import record_permission_check
        from orbit.models import OrbitEntry

        initial_count = OrbitEntry.objects.gates().count()

        record_permission_check(
            user="admin",
            permission="auth.add_user",
            obj=None,
            result=True,  # Boolean: True=granted
            backend="ModelBackend",
        )

        assert OrbitEntry.objects.gates().count() == initial_count + 1
        entry = OrbitEntry.objects.gates().last()
        assert entry.payload["user"] == "admin"
        assert entry.payload["permission"] == "auth.add_user"
        assert entry.payload["result"] == "granted"

    @override_settings(ORBIT_CONFIG={"ENABLED": True, "RECORD_GATES": True})
    def test_record_permission_denied(self):
        """Test recording a denied permission check."""
        from orbit.watchers import record_permission_check
        from orbit.models import OrbitEntry
        
        # Clear previous entries to avoid confusion
        OrbitEntry.objects.gates().delete()

        record_permission_check(
            user="guest",
            permission="admin.delete_logentry",
            obj=None,
            result=False,  # Boolean: False=denied
            backend="ModelBackend",
        )

        entry = OrbitEntry.objects.gates().last()
        assert entry is not None
        assert entry.payload["result"] == "denied"

    @override_settings(ORBIT_CONFIG={"ENABLED": True, "RECORD_GATES": True})
    def test_record_permission_with_object(self):
        """Test recording a permission check with object."""
        from orbit.watchers import record_permission_check
        from orbit.models import OrbitEntry

        record_permission_check(
            user="editor",
            permission="books.change_book",
            obj="Book:42",
            result=True,  # Boolean: True=granted
            backend="ObjectPermissionBackend",
        )

        entry = OrbitEntry.objects.gates().last()
        assert entry.payload["object"] == "Book:42"
        assert entry.payload["backend"] == "ObjectPermissionBackend"

    @override_settings(ORBIT_CONFIG={"ENABLED": True, "RECORD_GATES": False})
    def test_record_permission_disabled(self):
        """Test that permissions are not recorded when disabled."""
        from orbit.watchers import record_permission_check
        from orbit.models import OrbitEntry

        initial_count = OrbitEntry.objects.gates().count()

        record_permission_check(
            user="test",
            permission="test.perm",
            result=True,  # Boolean: True=granted
            backend="ModelBackend",
        )

        assert OrbitEntry.objects.gates().count() == initial_count


class TestInstallWatchers(TestCase):
    """Test watcher installation functions."""

    def test_install_celery_watcher_no_celery(self):
        """Test that Celery watcher handles missing Celery gracefully."""
        from orbit.watchers import install_celery_watcher
        
        with patch.dict('sys.modules', {'celery': None}):
            # Should not raise an exception
            install_celery_watcher()

    def test_install_djangoq_watcher_no_djangoq(self):
        """Test that Django-Q watcher handles missing django-q gracefully."""
        from orbit.watchers import install_djangoq_watcher
        
        with patch.dict('sys.modules', {'django_q': None, 'django_q.signals': None}):
            # Should not raise an exception
            install_djangoq_watcher()

    def test_install_rq_watcher_no_rq(self):
        """Test that RQ watcher handles missing rq gracefully."""
        from orbit.watchers import install_rq_watcher
        
        with patch.dict('sys.modules', {'rq': None}):
            # Should not raise an exception
            install_rq_watcher()

    def test_install_apscheduler_watcher_no_apscheduler(self):
        """Test that APScheduler watcher handles missing apscheduler gracefully."""
        from orbit.watchers import install_apscheduler_watcher
        
        with patch.dict('sys.modules', {'apscheduler': None, 'apscheduler.events': None}):
            # Should not raise an exception
            install_apscheduler_watcher()

    def test_install_celerybeat_watcher_no_celerybeat(self):
        """Test that celery-beat watcher handles missing django-celery-beat gracefully."""
        from orbit.watchers import install_celerybeat_watcher
        
        with patch.dict('sys.modules', {'django_celery_beat': None, 'django_celery_beat.models': None}):
            # Should not raise an exception
            install_celerybeat_watcher()

    def test_install_redis_watcher_no_redis(self):
        """Test that Redis watcher handles missing redis-py gracefully."""
        from orbit.watchers import install_redis_watcher
        
        with patch.dict('sys.modules', {'redis': None}):
            # Should not raise an exception
            install_redis_watcher()


class TestJobEntrySummary(TestCase):
    """Test job entry summary formatting."""

    def test_job_success_summary(self):
        """Test summary for successful job."""
        from orbit.models import OrbitEntry

        entry = OrbitEntry.objects.create(
            type=OrbitEntry.TYPE_JOB,
            payload={
                "name": "send_newsletter",
                "status": "success",
                "queue": "celery",
            },
            duration_ms=1500,
        )

        summary = entry.summary
        assert "send_newsletter" in summary
        assert "success" in summary.lower() or "✓" in summary

    def test_job_failure_summary(self):
        """Test summary for failed job."""
        from orbit.models import OrbitEntry

        entry = OrbitEntry.objects.create(
            type=OrbitEntry.TYPE_JOB,
            payload={
                "name": "process_order",
                "status": "failure",
                "error": "Database timeout",
            },
            duration_ms=5000,
        )

        summary = entry.summary
        assert "process_order" in summary


class TestRedisEntrySummary(TestCase):
    """Test Redis entry summary formatting."""

    def test_redis_get_summary(self):
        """Test summary for Redis GET operation."""
        from orbit.models import OrbitEntry

        entry = OrbitEntry.objects.create(
            type=OrbitEntry.TYPE_REDIS,
            payload={
                "operation": "GET",
                "key": "cache:user:123",
            },
            duration_ms=1.5,
        )

        summary = entry.summary
        assert "GET" in summary
        assert "cache:user:123" in summary

    def test_redis_set_summary(self):
        """Test summary for Redis SET operation."""
        from orbit.models import OrbitEntry

        entry = OrbitEntry.objects.create(
            type=OrbitEntry.TYPE_REDIS,
            payload={
                "operation": "SET",
                "key": "session:abc123",
            },
            duration_ms=2.0,
        )

        summary = entry.summary
        assert "SET" in summary


class TestGateEntrySummary(TestCase):
    """Test Gate entry summary formatting."""

    def test_gate_granted_summary(self):
        """Test summary for granted permission."""
        from orbit.models import OrbitEntry

        entry = OrbitEntry.objects.create(
            type=OrbitEntry.TYPE_GATE,
            payload={
                "user": "admin",
                "permission": "auth.add_user",
                "result": "granted",
            },
        )

        summary = entry.summary
        assert "auth.add_user" in summary or "granted" in summary.lower()

    def test_gate_denied_summary(self):
        """Test summary for denied permission."""
        from orbit.models import OrbitEntry

        entry = OrbitEntry.objects.create(
            type=OrbitEntry.TYPE_GATE,
            payload={
                "user": "guest",
                "permission": "admin.delete_logentry",
                "result": "denied",
            },
        )

        summary = entry.summary
        assert "admin.delete_logentry" in summary or "denied" in summary.lower()
