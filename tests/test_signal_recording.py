from django.test import override_settings

import pytest

from orbit.conf import get_config


@pytest.mark.django_db
def test_signal_capture_is_disabled_by_default():
    with override_settings(ORBIT_CONFIG={}):
        assert get_config()["RECORD_SIGNALS"] is False


@pytest.mark.django_db
def test_signal_capture_can_be_enabled_explicitly():
    with override_settings(ORBIT_CONFIG={"RECORD_SIGNALS": True}):
        assert get_config()["RECORD_SIGNALS"] is True
