"""
Tests for B5 — sensitive-data masking.
"""

import pytest

from orbit.utils import MASK_PLACEHOLDER, mask_sensitive_data, sanitize_body, sanitize_headers

# An autouse fixture in conftest touches the DB, so mark the whole module.
pytestmark = pytest.mark.django_db


def test_mask_redacts_nested_and_substring_keys():
    data = {
        "username": "alice",
        "password": "hunter2",
        "nested": {"access_token": "abc", "count": 3},
        "items": [{"api_key": "k"}, {"name": "ok"}],
        "X-Auth-Token": "zzz",
    }
    masked = mask_sensitive_data(data, keys=["password", "token", "api_key", "auth"])

    assert masked["username"] == "alice"
    assert masked["password"] == MASK_PLACEHOLDER
    assert masked["nested"]["access_token"] == MASK_PLACEHOLDER
    assert masked["nested"]["count"] == 3
    assert masked["items"][0]["api_key"] == MASK_PLACEHOLDER
    assert masked["items"][1]["name"] == "ok"
    assert masked["X-Auth-Token"] == MASK_PLACEHOLDER


def test_mask_does_not_mutate_input():
    data = {"password": "x"}
    mask_sensitive_data(data, keys=["password"])
    assert data["password"] == "x"


def test_sanitize_body_substring_match():
    body = {"user_password": "p", "normal": "v"}
    out = sanitize_body(body, hide_keys=["password"])
    assert out["user_password"] == MASK_PLACEHOLDER
    assert out["normal"] == "v"


def test_sanitize_headers_substring_match():
    headers = {"X-Api-Key": "k", "Accept": "json"}
    out = sanitize_headers(headers, hide_keys=["api_key", "api-key"])
    assert out["X-Api-Key"] == MASK_PLACEHOLDER
    assert out["Accept"] == "json"


@pytest.mark.django_db
def test_mask_all_payloads_on_save(settings):
    from orbit.models import OrbitEntry

    settings.ORBIT_CONFIG = {**getattr(settings, "ORBIT_CONFIG", {}), "MASK_ALL_PAYLOADS": True}
    entry = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_DUMP,
        payload={"secret_value": "leak", "ok": "fine"},
    )
    entry.refresh_from_db()
    assert entry.payload["secret_value"] == MASK_PLACEHOLDER
    assert entry.payload["ok"] == "fine"


@pytest.mark.django_db
def test_mask_all_payloads_off_by_default(settings):
    from orbit.models import OrbitEntry

    settings.ORBIT_CONFIG = {**getattr(settings, "ORBIT_CONFIG", {})}
    settings.ORBIT_CONFIG.pop("MASK_ALL_PAYLOADS", None)
    entry = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_DUMP,
        payload={"secret_value": "kept"},
    )
    entry.refresh_from_db()
    assert entry.payload["secret_value"] == "kept"
