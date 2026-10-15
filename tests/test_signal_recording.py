from django.db.models.signals import post_save
from django.dispatch import Signal
from django.test import override_settings

import pytest

from orbit import watchers
from orbit.conf import get_config
from orbit.models import OrbitEntry


@pytest.mark.django_db
def test_signal_capture_is_disabled_by_default():
    with override_settings(ORBIT_CONFIG={}):
        assert get_config()["RECORD_SIGNALS"] is False


@pytest.mark.django_db
def test_signal_capture_can_be_enabled_explicitly():
    with override_settings(ORBIT_CONFIG={"RECORD_SIGNALS": True}):
        assert get_config()["RECORD_SIGNALS"] is True


@pytest.mark.django_db
@override_settings(ORBIT_CONFIG={})
def test_disabled_signal_capture_does_not_check_storage(monkeypatch):
    def unexpected_storage_check():
        pytest.fail("Disabled signal recording must not access storage")

    monkeypatch.setattr(watchers, "_table_exists", unexpected_storage_check)
    watchers.record_signal(Signal(), sender=None)

    assert not OrbitEntry.objects.filter(type=OrbitEntry.TYPE_SIGNAL).exists()


@pytest.mark.django_db
@override_settings(ORBIT_CONFIG={"RECORD_SIGNALS": True})
def test_opt_in_records_application_signal(monkeypatch):
    signal = Signal()
    monkeypatch.setattr(watchers, "_signal_registry", {id(signal): "orders.paid"})
    monkeypatch.setattr(watchers, "_table_exists", lambda: True)

    watchers.record_signal(signal, sender=None, order_id=42)

    entry = OrbitEntry.objects.get(type=OrbitEntry.TYPE_SIGNAL)
    assert entry.payload["signal"] == "orders.paid"
    assert entry.payload["kwargs"] == {"order_id": "42"}


@pytest.mark.django_db
@pytest.mark.parametrize("include_lifecycle", [False, True])
def test_lifecycle_signals_require_explicit_ignore_override(
    monkeypatch, include_lifecycle
):
    config = {"RECORD_SIGNALS": True}
    if include_lifecycle:
        config = {**config, "IGNORE_SIGNALS": []}
    monkeypatch.setattr(
        watchers,
        "_signal_registry",
        {id(post_save): "django.db.models.signals.post_save"},
    )
    monkeypatch.setattr(watchers, "_table_exists", lambda: True)

    with override_settings(ORBIT_CONFIG=config):
        watchers.record_signal(post_save, sender=None)

    assert (
        OrbitEntry.objects.filter(type=OrbitEntry.TYPE_SIGNAL).exists()
        is include_lifecycle
    )
