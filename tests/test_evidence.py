import json
from contextlib import contextmanager
from copy import deepcopy
from unittest.mock import patch

import pytest

from orbit.models import OrbitEntry

pytestmark = pytest.mark.django_db


@pytest.fixture
def evidence_family():
    request = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        family_hash="family-evidence",
        duration_ms=125.5,
        tags=",secret-tag,",
        payload={
            "method": "POST",
            "path": "/checkout/?token=secret",
            "full_path": "/checkout/?token=secret",
            "status_code": 500,
            "query_count": 0,
            "duplicate_query_count": 2,
            "had_exception": True,
            "headers": {"Authorization": "Bearer secret"},
            "body": {"password": "secret"},
        },
    )
    query = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_QUERY,
        family_hash="family-evidence",
        duration_ms=850.0,
        payload={
            "is_slow": True,
            "is_duplicate": False,
            "duplicate_count": 0,
            "database": "default",
            "sql": "SELECT secret FROM payments",
            "params": ["secret"],
        },
    )
    exception = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_EXCEPTION,
        family_hash="family-evidence",
        fingerprint="abc123",
        payload={
            "exception_type": "ValueError",
            "request_method": "POST",
            "request_path": "/checkout/?token=secret",
            "message": "secret",
            "traceback_string": "secret traceback",
        },
    )
    return request, query, exception


def test_serialize_entry_exposes_only_normalized_request_metadata(evidence_family):
    from orbit.evidence import EVIDENCE_SCHEMA_VERSION, serialize_entry

    request = evidence_family[0]
    original_payload = deepcopy(request.payload)

    data = serialize_entry(request)

    assert EVIDENCE_SCHEMA_VERSION == "orbit.evidence.v1"
    assert data == {
        "id": str(request.id),
        "type": "request",
        "family_hash": "family-evidence",
        "fingerprint": None,
        "created_at": request.created_at.isoformat(),
        "duration_ms": 125.5,
        "attributes": {
            "method": "POST",
            "path": "/checkout/",
            "status_code": 500,
            "query_count": 0,
            "duplicate_query_count": 2,
            "had_exception": True,
        },
        "truncated_fields": [],
    }
    assert request.payload == original_payload
    encoded = json.dumps(data)
    assert "secret" not in encoded
    assert "summary" not in data
    assert "tags" not in data


def test_serialize_entry_normalizes_query_and_exception(evidence_family):
    from orbit.evidence import serialize_entry

    query = serialize_entry(evidence_family[1])
    exception = serialize_entry(evidence_family[2])

    assert query["attributes"] == {
        "is_slow": True,
        "is_duplicate": False,
        "duplicate_count": 0,
        "database": "default",
    }
    assert exception["fingerprint"] == "abc123"
    assert exception["attributes"] == {
        "exception_type": "ValueError",
        "request_method": "POST",
        "request_path": "/checkout/",
    }
    assert "secret" not in json.dumps([query, exception])


def test_serialize_entry_preserves_unknowns_as_none(db):
    from orbit.evidence import serialize_entry

    entry = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        family_hash="family-missing",
        payload={
            "method": 123,
            "status_code": True,
            "query_count": -1,
            "duplicate_query_count": "2",
            "had_exception": 1,
        },
    )

    assert serialize_entry(entry)["attributes"] == {
        "method": None,
        "path": None,
        "status_code": None,
        "query_count": None,
        "duplicate_query_count": None,
        "had_exception": None,
    }


def test_serialize_entry_bounds_strings_and_unknown_types(db):
    from orbit.evidence import serialize_entry

    request = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        family_hash="family-long",
        payload={"method": "M" * 300, "path": "/" + ("x" * 3000)},
    )
    log = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_LOG,
        family_hash="family-long",
        payload={"message": "secret"},
    )

    request_data = serialize_entry(request)
    log_data = serialize_entry(log)

    assert len(request_data["attributes"]["method"]) == 255
    assert len(request_data["attributes"]["path"]) == 2048
    assert request_data["truncated_fields"] == [
        "attributes.method",
        "attributes.path",
    ]
    assert log_data["attributes"] == {}
    assert "secret" not in json.dumps(log_data)


def test_serialize_entry_bounds_public_scalar_identifiers():
    from orbit.evidence import serialize_entry

    entry = OrbitEntry(
        type=OrbitEntry.TYPE_EXCEPTION,
        family_hash="invalid\nhash",
        fingerprint="f" * 100,
        payload={
            "exception_type": "ValueError",
            "request_method": "GET",
            "request_path": "/failure/",
        },
    )

    data = serialize_entry(entry)

    assert data["family_hash"] is None
    assert data["fingerprint"] == "f" * 64
    assert data["truncated_fields"] == ["fingerprint"]


def test_read_family_evidence_returns_deterministic_bounded_envelope(evidence_family):
    from orbit.evidence import read_family_evidence

    data = read_family_evidence("family-evidence", limit=2)

    assert data["schema_version"] == "orbit.evidence.v1"
    assert data["status"] == "ok"
    assert data["reason"] is None
    assert data["family_hash"] == "family-evidence"
    assert data["count"] == 2
    assert data["truncated"] is True
    assert data["evidence_quality"]["status"] == "partial"
    assert data["evidence_quality"]["warnings"] == ["family_truncated"]
    assert data["evidence_quality"]["next_actions"] == [
        {"code": "retry_with_higher_limit", "parameters": {"limit": 4}},
        {"code": "do_not_conclude_absence", "parameters": {}},
    ]
    assert [item["id"] for item in data["entries"]] == [
        str(evidence_family[0].id),
        str(evidence_family[1].id),
    ]


@pytest.mark.parametrize(
    ("family_hash", "limit", "reason"),
    [
        ("", 10, "invalid_family_hash"),
        (" " * 3, 10, "invalid_family_hash"),
        (123, 10, "invalid_family_hash"),
        ("x" * 65, 10, "invalid_family_hash"),
        ("family\nhash", 10, "invalid_family_hash"),
        ("family", 0, "invalid_limit"),
        ("family", True, "invalid_limit"),
        ("family", 5001, "invalid_limit"),
    ],
)
def test_read_family_evidence_rejects_invalid_inputs(family_hash, limit, reason):
    from orbit.evidence import read_family_evidence

    data = read_family_evidence(family_hash, limit=limit)

    assert data["status"] == "invalid"
    assert data["reason"] == reason
    assert data["entries"] == []
    assert data["evidence_quality"]["status"] == "unavailable"
    assert "do_not_conclude_absence" in {
        action["code"] for action in data["evidence_quality"]["next_actions"]
    }
    if reason == "invalid_family_hash":
        assert data["family_hash"] is None


def test_read_family_evidence_reports_not_found(db):
    from orbit.evidence import read_family_evidence

    data = read_family_evidence("missing-family")

    assert data["status"] == "not_found"
    assert data["reason"] == "family_not_found"
    assert data["count"] == 0
    assert data["truncated"] is False
    assert data["evidence_quality"]["warnings"] == ["family_not_found"]
    assert data["evidence_quality"]["next_actions"] == [
        {"code": "verify_family_hash", "parameters": {}},
        {"code": "verify_capture_and_retention", "parameters": {}},
        {"code": "do_not_conclude_absence", "parameters": {}},
    ]


def test_read_family_evidence_fails_silently_when_storage_is_unavailable(db):
    from orbit.evidence import read_family_evidence

    with patch("orbit.evidence._table_exists", return_value=False):
        data = read_family_evidence("family")

    assert data["status"] == "unavailable"
    assert data["reason"] == "storage_unavailable"
    assert data["evidence_quality"]["next_actions"] == [
        {"code": "verify_migrations_and_storage", "parameters": {}},
        {"code": "do_not_conclude_absence", "parameters": {}},
    ]


def test_read_family_evidence_fails_silently_on_database_error(db):
    from orbit.evidence import read_family_evidence

    with (
        patch("orbit.evidence._table_exists", return_value=True),
        patch("orbit.evidence.OrbitEntry.objects.using", side_effect=RuntimeError),
    ):
        data = read_family_evidence("family")

    assert data["status"] == "unavailable"
    assert data["reason"] == "read_failed"
    assert data["evidence_quality"]["next_actions"] == [
        {"code": "retry_read", "parameters": {}},
        {"code": "inspect_server_logs", "parameters": {}},
        {"code": "do_not_conclude_absence", "parameters": {}},
    ]


def test_read_family_evidence_marks_missing_metadata_as_partial(db):
    from orbit.evidence import read_family_evidence

    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        family_hash="family-partial",
        payload={"method": "GET", "path": "/health/"},
    )

    data = read_family_evidence("family-partial")

    assert data["status"] == "ok"
    assert data["evidence_quality"]["status"] == "partial"
    assert data["evidence_quality"]["warnings"] == ["missing_fields"]
    assert data["evidence_quality"]["missing_fields"] == [
        "request.attributes.duplicate_query_count",
        "request.attributes.had_exception",
        "request.attributes.query_count",
        "request.attributes.status_code",
    ]
    assert data["evidence_quality"]["next_actions"] == [
        {
            "code": "review_missing_fields",
            "parameters": {"fields": data["evidence_quality"]["missing_fields"]},
        },
        {"code": "do_not_conclude_absence", "parameters": {}},
    ]


def test_read_family_evidence_marks_unsupported_types_as_partial(db):
    from orbit.evidence import read_family_evidence

    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_LOG,
        family_hash="family-log",
        payload={"message": "not exposed"},
    )

    data = read_family_evidence("family-log")

    assert data["status"] == "ok"
    assert data["evidence_quality"]["status"] == "partial"
    assert data["evidence_quality"]["warnings"] == ["unsupported_entry_types"]
    assert data["evidence_quality"]["unsupported_entry_types"] == ["log"]
    assert data["evidence_quality"]["next_actions"] == [
        {
            "code": "call_mcp_tool",
            "parameters": {
                "tool": "create_incident_bundle",
                "arguments": {
                    "source_type": "family_hash",
                    "source_value": "family-log",
                    "format": "json",
                },
                "reason": "unsupported_entry_types",
            },
        },
        {"code": "do_not_conclude_absence", "parameters": {}},
    ]


def test_read_family_evidence_routes_maximum_truncation_to_incident_bundle(db):
    from orbit.evidence import MAX_FAMILY_LIMIT, read_family_evidence

    OrbitEntry.objects.bulk_create(
        [
            OrbitEntry(
                type=OrbitEntry.TYPE_LOG,
                family_hash="family-oversized",
                payload={},
            )
            for _ in range(MAX_FAMILY_LIMIT + 1)
        ]
    )

    data = read_family_evidence("family-oversized", limit=MAX_FAMILY_LIMIT)

    assert data["truncated"] is True
    assert data["evidence_quality"]["next_actions"][0] == {
        "code": "call_mcp_tool",
        "parameters": {
            "tool": "create_incident_bundle",
            "arguments": {
                "source_type": "family_hash",
                "source_value": "family-oversized",
                "format": "json",
            },
            "reason": "family_truncated",
        },
    }


def test_read_family_evidence_uses_storage_alias_and_disables_cache(evidence_family):
    from orbit.evidence import read_family_evidence

    calls = []

    @contextmanager
    def cache_disabled():
        calls.append("entered")
        yield
        calls.append("exited")

    with (
        patch("orbit.evidence._table_exists", return_value=True),
        patch("orbit.evidence.get_storage_db_alias", return_value="default") as alias,
        patch("orbit.evidence.cachalot_disabled", cache_disabled),
    ):
        data = read_family_evidence("family-evidence")

    alias.assert_called_once_with()
    assert calls == ["entered", "exited"]
    assert data["status"] == "ok"
    assert data["evidence_quality"] == {
        "status": "complete",
        "warnings": [],
        "missing_fields": [],
        "truncated_fields": [],
        "unsupported_entry_types": [],
        "next_actions": [],
    }
