"""Schema-command safety is independent of command telemetry."""

import subprocess
import sys
from contextvars import Context

from django.core.management.base import BaseCommand
from django.test import override_settings

import pytest

import orbit.watchers as watchers

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("ignored", [[], ["migrate"]])
def test_fresh_migrations_without_command_recording(ignored):
    script = f"""
from django.conf import settings
settings.configure(
    SECRET_KEY="synthetic-test-only",
    INSTALLED_APPS=["django.contrib.contenttypes", "orbit"],
    DATABASES={{"default": {{"ENGINE": "django.db.backends.sqlite3",
                            "NAME": ":memory:"}}}},
    USE_TZ=True,
    ORBIT_CONFIG={{"RECORD_COMMANDS": False, "RECORD_MODELS": True,
                  "IGNORE_COMMANDS": {ignored!r}, "RECORD_SIGNALS": False}},
)
import django
django.setup()
from django.core.management import call_command
call_command("migrate", verbosity=0)
from orbit.models import OrbitEntry
assert not OrbitEntry.objects.filter(type="command").exists()
import orbit.watchers as watchers
assert watchers.get_watcher_status()["command"]["disabled"]
assert watchers._table_exists()
print("migrations-safe")
"""
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, result.stderr
    assert "migrations-safe" in result.stdout


def _command(name, handler):
    return type(
        "Command",
        (BaseCommand,),
        {"__module__": f"django.core.management.commands.{name}", "handle": handler},
    )()


def _execute(command):
    return command.execute(
        verbosity=0, force_color=False, no_color=False, skip_checks=True
    )


@override_settings(ORBIT_CONFIG={"IGNORE_COMMANDS": ["migrate"]})
def test_ignored_schema_command_still_suspends_recording(monkeypatch):
    monkeypatch.setattr(watchers, "_orbit_table_ready", True)
    observed = []

    def handle(self, *args, **kwargs):
        observed.append(watchers._table_exists())

    _execute(_command("migrate", handle))
    assert observed == [False]
    assert watchers._table_exists()


def test_nested_schema_command_restores_outer_suspension(monkeypatch):
    monkeypatch.setattr(watchers, "_orbit_table_ready", True)
    observed = []

    def inner(self, *args, **kwargs):
        observed.append(watchers._table_exists())

    def outer(self, *args, **kwargs):
        observed.append(watchers._table_exists())
        _execute(_command("flush", inner))
        observed.append(watchers._table_exists())

    _execute(_command("migrate", outer))
    assert observed == [False, False, False]
    assert watchers._table_exists()


def test_failing_schema_command_restores_recording(monkeypatch):
    monkeypatch.setattr(watchers, "_orbit_table_ready", True)

    def handle(self, *args, **kwargs):
        assert not watchers._table_exists()
        raise RuntimeError("synthetic migration failure")

    with pytest.raises(RuntimeError, match="synthetic migration failure"):
        _execute(_command("migrate", handle))
    assert watchers._table_exists()


def test_schema_suspension_is_local_to_execution_context(monkeypatch):
    monkeypatch.setattr(watchers, "_orbit_table_ready", True)
    observed = []

    def handle(self, *args, **kwargs):
        observed.append(watchers._table_exists())
        observed.append(Context().run(watchers._table_exists))

    _execute(_command("migrate", handle))
    assert observed == [False, True]
