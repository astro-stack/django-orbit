
import pytest
from django.db import models
from django.dispatch import Signal
from orbit.models import OrbitEntry

@pytest.mark.django_db
def test_signal_entry_with_none_sender_does_not_crash():
    """
    Test regression for Issue #7: AttributeError when sender is None.
    Should handle sender=None gracefully in OrbitEntry.summary.
    """
    # 1. Create a dummy entry with None sender (simulating the payload)
    entry = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_SIGNAL,
        payload={
            "signal": "my_signal",
            "sender": None,  # This caused the crash
            "kwargs": {}
        }
    )

    # 2. Try to access the summary property
    # Before the fix, this raised AttributeError: 'NoneType' object has no attribute 'startswith'
    try:
        summary = entry.summary
        assert "?", summary  # It should return a safe string in format "signal → sender"
        assert "my_signal" in summary
    except AttributeError as e:
        pytest.fail(f"Crash accessing summary with None sender: {e}")
