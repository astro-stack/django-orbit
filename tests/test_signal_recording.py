import pytest
from django.db.models.signals import post_save
from django.dispatch import Signal
from django.test import override_settings

import orbit.watchers as watchers
from orbit.models import OrbitEntry


@pytest.mark.django_db
@override_settings(ORBIT_CONFIG={})
def test_signal_capture_is_disabled_by_default():
    from orbit.conf import get_config

    assert get_config()["RECORD_SIGNALS"] is False
    assert get_config()["RECORD_ANONYMOUS_SIGNALS"] is False


@pytest.mark.django_db
@override_settings(
    ORBIT_CONFIG={
        "ENABLED": True,
        "RECORD_SIGNALS": True,
        "RECORD_ANONYMOUS_SIGNALS": False,
    }
)
def test_signal_recorder_skips_anonymous_framework_dispatches(monkeypatch):
    signal = Signal()
    monkeypatch.setattr(watchers, "_signal_registry", {})
    monkeypatch.setattr(watchers, "_table_exists", lambda: True)

    watchers.record_signal(signal, sender=None)

    assert not OrbitEntry.objects.filter(type=OrbitEntry.TYPE_SIGNAL).exists()


@pytest.mark.django_db
@override_settings(
    ORBIT_CONFIG={
        "ENABLED": True,
        "RECORD_SIGNALS": True,
        "RECORD_ANONYMOUS_SIGNALS": False,
    }
)
def test_signal_recorder_keeps_explicitly_named_application_signal(monkeypatch):
    signal = Signal()
    payment_sender = type("Payment", (), {"__module__": "payments.models"})
    monkeypatch.setattr(watchers, "_signal_registry", {})
    monkeypatch.setattr(watchers, "_table_exists", lambda: True)

    watchers.record_signal(signal, sender=payment_sender, order_id="order-42")

    entry = OrbitEntry.objects.get(type=OrbitEntry.TYPE_SIGNAL)
    assert entry.payload["signal"] == "payments.models.Payment.signal"
    assert entry.payload["kwargs"]["order_id"] == "'order-42'"


@pytest.mark.django_db
@override_settings(ORBIT_CONFIG={"ENABLED": True, "RECORD_SIGNALS": True})
def test_signal_recorder_skips_duplicate_orm_lifecycle_signal(monkeypatch):
    monkeypatch.setattr(
        watchers,
        "_signal_registry",
        {id(post_save): "django.db.models.signals.post_save"},
    )
    monkeypatch.setattr(watchers, "_table_exists", lambda: True)

    watchers.record_signal(post_save, sender=None)

    assert not OrbitEntry.objects.filter(type=OrbitEntry.TYPE_SIGNAL).exists()
