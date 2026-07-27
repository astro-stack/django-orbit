"""Contract tests for the neutral runtime adapter boundary."""

import pytest


pytestmark = pytest.mark.django_db


def test_manifest_declares_stable_django_adapter_capabilities():
    from orbit.extensions import get_runtime_adapter_manifest

    manifest = get_runtime_adapter_manifest()

    assert manifest["contract_version"] == "orbit.runtime-adapter.v1"
    assert manifest["adapter_id"] == "django-orbit"
    assert manifest["evidence_schema_versions"] == ["orbit.evidence.v1"]
    assert manifest["capabilities"]["family_evidence.read"]["status"] == "available"
    assert manifest["capabilities"]["capture_health.read"]["status"] == "available"
    assert "release_window.compare" not in manifest["capabilities"]


def test_family_resource_delegates_to_versioned_evidence(monkeypatch):
    from orbit.extensions import read_runtime_evidence

    expected = {"schema_version": "orbit.evidence.v1", "status": "ok"}
    monkeypatch.setattr("orbit.evidence.read_family_evidence", lambda value, limit: expected)

    assert read_runtime_evidence(
        "family_evidence", {"family_hash": "family-1"}, limit=7
    ) == expected


def test_capture_health_resource_delegates_without_reference(monkeypatch):
    from orbit.extensions import read_runtime_evidence

    expected = {"schema_version": "orbit.evidence.v1", "resource": "capture_health"}
    monkeypatch.setattr("orbit.evidence.read_capture_health", lambda: expected)

    assert read_runtime_evidence("capture_health", {}) == expected


@pytest.mark.parametrize(
    ("resource", "reference", "reason"),
    [
        ("unknown", {}, "unsupported_resource"),
        ("family_evidence", {}, "invalid_reference"),
        ("family_evidence", {"family_hash": "family"}, "invalid_limit"),
    ],
)
def test_invalid_runtime_evidence_requests_are_stable(resource, reference, reason):
    from orbit.extensions import read_runtime_evidence

    kwargs = {"limit": 0} if reason == "invalid_limit" else {}
    data = read_runtime_evidence(resource, reference, **kwargs)

    assert data["contract_version"] == "orbit.runtime-adapter.v1"
    assert data["status"] == "invalid"
    assert data["reason"] == reason


def test_adapter_preserves_partial_evidence_without_reclassifying(monkeypatch):
    from orbit.extensions import read_runtime_evidence

    partial = {
        "schema_version": "orbit.evidence.v1",
        "status": "ok",
        "evidence_quality": {"status": "partial", "warnings": ["family_truncated"]},
    }
    monkeypatch.setattr("orbit.evidence.read_family_evidence", lambda value, limit: partial)

    assert read_runtime_evidence("family_evidence", {"family_hash": "family"}) == partial
