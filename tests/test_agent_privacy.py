"""Regression coverage for agent-facing derived text and export claims."""

import json

from django.utils import timezone

import pytest

from orbit.agentic import (
    _query_analysis,
    agent_safe_serialize_entry,
    create_incident_bundle,
    daily_health_brief,
    find_sensitive_payload_risks,
)
from orbit.models import OrbitEntry

PRIVATE_TEXT = "SYNTHETIC-PRIVATE-84721"
pytestmark = pytest.mark.django_db


def private_entry(entry_type):
    return OrbitEntry(
        type=entry_type,
        family_hash="privacy-family",
        fingerprint="privacy-fingerprint",
        created_at=timezone.now(),
        duration_ms=901,
        tags=f"private:{PRIVATE_TEXT}",
        payload={
            "method": "GET",
            "path": f"/private/{PRIVATE_TEXT}",
            "status_code": 500,
            "level": "ERROR",
            "message": PRIVATE_TEXT,
            "exception_type": "ValueError",
            "sql": f"SELECT * FROM accounts WHERE email = '{PRIVATE_TEXT}'",
            "is_slow": True,
            "is_duplicate": True,
            "subject": PRIVATE_TEXT,
            "operation": "get",
            "key": PRIVATE_TEXT,
            "password": PRIVATE_TEXT,
        },
    )


@pytest.mark.parametrize(
    "entry_type", ["request", "query", "log", "exception", "mail", "cache"]
)
@pytest.mark.parametrize(
    "configured,requested", [(True, False), (False, None), (False, True)]
)
def test_metadata_serializer_omits_derived_text(
    settings, entry_type, configured, requested
):
    settings.ORBIT_CONFIG = {"MCP_INCLUDE_PAYLOADS": configured}
    entry = private_entry(entry_type)

    data = agent_safe_serialize_entry(entry, include_payload=requested)

    assert PRIVATE_TEXT not in json.dumps(data)
    assert data["summary"] == ""
    assert data["tags"] == []
    assert data["derived_fields_omitted"] == ["summary", "tags"]
    assert data["payload_omitted"] is True
    assert "payload" not in data
    assert data["id"] == str(entry.id)
    assert data["family_hash"] == "privacy-family"
    assert data["fingerprint"] == "privacy-fingerprint"
    assert data["duration_ms"] == 901
    assert data["created_at"] == entry.created_at.isoformat()
    assert data["is_error"] == entry.is_error
    assert data["is_warning"] == entry.is_warning
    assert entry.payload["password"] == PRIVATE_TEXT
    assert PRIVATE_TEXT in entry.tags


@pytest.mark.parametrize("requested", [None, True])
def test_payload_enabled_preserves_text_and_key_based_masking(settings, requested):
    settings.ORBIT_CONFIG = {"MCP_INCLUDE_PAYLOADS": True}
    entry = private_entry("log")

    data = agent_safe_serialize_entry(entry, include_payload=requested)

    assert data["summary"] == entry.summary
    assert data["tags"] == [f"private:{PRIVATE_TEXT}"]
    assert data["payload"]["password"] == "***HIDDEN***"
    assert data["payload"]["message"] == PRIVATE_TEXT
    assert "derived_fields_omitted" not in data


@pytest.mark.parametrize("enabled", [False, True])
def test_query_analysis_respects_effective_policy(settings, enabled):
    settings.ORBIT_CONFIG = {"MCP_INCLUDE_PAYLOADS": enabled}
    entry = private_entry("query")

    data = _query_analysis([entry, entry, private_entry("log")])

    assert data["total"] == 2
    assert data["slow_count"] == 2
    assert data["duplicate_count"] == 2
    signature = data["duplicate_signatures"][0]
    assert signature["count"] == 2
    if enabled:
        assert signature["sql_preview"] == entry.payload["sql"][:180]
        assert data["top_slow"][0]["payload"]["sql"] == entry.payload["sql"]
    else:
        assert PRIVATE_TEXT not in json.dumps(data)
        assert signature["sql_preview"] == ""
        assert signature["sql_preview_omitted"] is True
        assert all(item["payload_omitted"] for item in data["top_slow"])


@pytest.fixture
def private_family(db):
    for entry_type in ("request", "query", "log", "exception"):
        entry = private_entry(entry_type)
        # Affected paths remain operational context, not a universal privacy boundary.
        entry.payload = {**entry.payload, "path": "/private/"}
        entry.save()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "source_type,source_value",
    [("family_hash", "privacy-family"), ("fingerprint", "privacy-fingerprint")],
)
@pytest.mark.parametrize("format", ["json", "markdown", "prompt"])
def test_metadata_bundle_db_export_omits_derived_secrets(
    settings, private_family, source_type, source_value, format
):
    settings.ORBIT_CONFIG = {"MCP_INCLUDE_PAYLOADS": False}

    result = create_incident_bundle(source_type, source_value, format=format)

    encoded = json.dumps(result) if isinstance(result, dict) else result
    assert PRIVATE_TEXT not in encoded
    assert "Raw sensitive values are not included" not in encoded
    assert "unknown" in encoded.lower()
    if format == "json":
        report = result["safety_report"]
        assert report["include_payloads"] is False
        assert report["raw_sensitive_values_exposed"] is None
        assert report["residual_risk"] == "unknown"
        assert report["redaction_coverage"]
        assert result["bundle_version"] == "agentic-v1"
        assert result["primary"]["diagnosis"]["severity"] == "error"


@pytest.mark.django_db
@pytest.mark.parametrize("enabled", [False, True])
def test_bundle_reports_coverage_not_universal_redaction(
    settings, private_family, enabled
):
    settings.ORBIT_CONFIG = {"MCP_INCLUDE_PAYLOADS": enabled}

    bundle = create_incident_bundle("family_hash", "privacy-family")

    report = bundle["safety_report"]
    assert report["include_payloads"] is enabled
    assert report["raw_sensitive_values_exposed"] is None
    assert report["residual_risk"] == "unknown"
    assert report["redaction_coverage"]
    assert report["limitations"]
    assert report["serializer"] == "agent_safe_serialize_entry"
    if enabled:
        assert PRIVATE_TEXT in json.dumps(bundle["primary"])
        assert bundle["primary"]["events"][0]["payload"]["password"] == "***HIDDEN***"


@pytest.mark.parametrize("tool", [daily_health_brief, find_sensitive_payload_risks])
def test_metadata_briefs_do_not_reintroduce_derived_text(
    settings, private_family, tool
):
    settings.ORBIT_CONFIG = {"MCP_INCLUDE_PAYLOADS": False}
    assert PRIVATE_TEXT not in json.dumps(tool())
