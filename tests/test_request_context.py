import json
from copy import deepcopy

from django.test import override_settings

import pytest

from orbit import evidence
from orbit.models import OrbitEntry

pytestmark = pytest.mark.django_db


@pytest.fixture
def family():
    request = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        family_hash="compact-family",
        duration_ms=125.5,
        payload={
            "method": "POST",
            "path": "/checkout/?token=secret-path",
            "status_code": 503,
            "query_count": 1,
            "duplicate_query_count": 1,
            "had_exception": True,
            "headers": {"Authorization": "secret-header"},
            "body": {"email": "private@example.com"},
        },
    )
    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_QUERY,
        family_hash=request.family_hash,
        duration_ms=100,
        payload={
            "is_slow": True,
            "is_duplicate": True,
            "duplicate_count": 1,
            "database": "default",
            "sql": "SELECT 'secret-sql'",
        },
    )
    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_EXCEPTION,
        family_hash=request.family_hash,
        fingerprint="compact-fingerprint",
        payload={
            "exception_type": "ValueError",
            "request_method": "POST",
            "request_path": "/checkout/",
            "message": "secret-message",
            "traceback_string": 'File "/private/source/views.py", line 42',
        },
    )
    return request


@override_settings(ORBIT_CONFIG={"MCP_INCLUDE_PAYLOADS": True})
def test_summary_contains_only_observed_metadata(family):
    from orbit.request_context import summarize_request_family

    result = summarize_request_family(family.family_hash)

    assert result["schema_version"] == evidence.EVIDENCE_SCHEMA_VERSION
    assert result["status"] == "ok"
    assert result["resource"] == "request_family_summary"
    assert result["count"] == 3
    assert result["summary"]["request"] == {
        "id": str(family.id),
        "method": "POST",
        "path": "/checkout/",
        "status_code": 503,
        "duration_ms": 125.5,
        "query_count": 1,
        "duplicate_query_count": 1,
        "had_exception": True,
    }
    assert result["summary"]["event_counts"] == {
        "exception": 1,
        "query": 1,
        "request": 1,
    }
    assert result["summary"]["observed_signals"] == {
        "exceptions": 1,
        "http_server_errors": 1,
        "slow_queries": 1,
        "duplicate_queries": 1,
    }
    assert result["summary"]["counts_scope"] == "returned_events"
    assert result["evidence_quality"]["status"] == "complete"
    text = json.dumps(result)
    for forbidden in ("secret-", "private@example.com", "/private/source", "SELECT"):
        assert forbidden not in text
    assert "entries" not in result


@override_settings(ORBIT_CONFIG={"MCP_MAX_LIMIT": 2})
def test_summary_retains_truncation_and_counts_only_returned_events(family):
    from orbit.request_context import summarize_request_family

    result = summarize_request_family(family.family_hash, limit=1000)

    assert result["count"] == 2
    assert result["truncated"] is True
    assert sum(result["summary"]["event_counts"].values()) == 2
    assert "family_truncated" in result["evidence_quality"]["warnings"]
    assert "do_not_conclude_absence" in {
        action["code"] for action in result["evidence_quality"]["next_actions"]
    }
    actions = result["evidence_quality"]["next_actions"]
    assert actions[0] == {
        "code": "review_mcp_limit",
        "parameters": {
            "setting": "MCP_MAX_LIMIT",
            "current_limit": 2,
            "maximum": evidence.MAX_FAMILY_LIMIT,
        },
    }
    assert all(action["code"] != "retry_with_higher_limit" for action in actions)


@override_settings(ORBIT_CONFIG={"MCP_MAX_LIMIT": 3})
def test_retry_recommendation_stays_within_the_mcp_cap(family):
    from orbit.request_context import summarize_request_family

    result = summarize_request_family(family.family_hash, limit=2)

    assert result["evidence_quality"]["next_actions"][0] == {
        "code": "retry_with_higher_limit",
        "parameters": {"limit": 3},
    }


def test_summary_preserves_gaps_and_does_not_invent_a_request():
    from orbit.request_context import summarize_request_family

    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_LOG,
        family_hash="orphan-log",
        payload={"level": "ERROR", "message": "private domain failure"},
    )
    result = summarize_request_family("orphan-log")

    assert result["summary"]["request"] is None
    assert result["summary"]["observed_signals"] == {}
    assert result["evidence_quality"]["status"] == "partial"
    assert "unsupported_entry_types" in result["evidence_quality"]["warnings"]
    assert "private domain failure" not in json.dumps(result)


@pytest.mark.parametrize("limit", [0, -1, True, "2", float("inf")])
def test_invalid_limits_do_not_access_storage(monkeypatch, limit):
    from orbit.request_context import summarize_request_family

    def unexpected_read():
        pytest.fail("Invalid input must not access storage")

    monkeypatch.setattr(evidence, "_table_exists", unexpected_read)
    result = summarize_request_family("valid-family", limit=limit)

    assert result["status"] == "invalid"
    assert result["reason"] == "invalid_limit"
    assert result["summary"] is None


def test_invalid_family_does_not_echo_unsafe_input(monkeypatch):
    from orbit.request_context import summarize_request_family

    monkeypatch.setattr(evidence, "_table_exists", lambda: pytest.fail("No DB read"))
    result = summarize_request_family("unsafe\nfamily")

    assert result["status"] == "invalid"
    assert result["family_hash"] is None
    assert "unsafe" not in json.dumps(result)


def test_missing_family_has_no_success_summary():
    from orbit.request_context import summarize_request_family

    result = summarize_request_family("missing-family")

    assert result["status"] == "not_found"
    assert result["reason"] == "family_not_found"
    assert result["summary"] is None


@pytest.mark.parametrize("reason", ["storage_unavailable", "read_failed"])
def test_storage_failure_retains_recovery_actions(monkeypatch, reason):
    from orbit.request_context import summarize_request_family

    if reason == "storage_unavailable":
        monkeypatch.setattr(evidence, "_table_exists", lambda: False)
    else:
        monkeypatch.setattr(evidence, "_table_exists", lambda: True)

        def fail_alias():
            raise RuntimeError("secret-storage-error")

        monkeypatch.setattr(evidence, "get_storage_db_alias", fail_alias)
    result = summarize_request_family("unavailable-family")

    assert result["status"] == "unavailable"
    assert result["reason"] == reason
    assert result["summary"] is None
    assert result["evidence_quality"]["next_actions"]
    assert "secret-storage-error" not in json.dumps(result)


@pytest.mark.parametrize("configured", [True, "bad", float("inf"), 100000])
def test_limits_are_validated_and_capped_at_contract_max(monkeypatch, configured):
    from orbit.request_context import summarize_request_family

    limits = []
    original = evidence.read_family_evidence

    def capture_limit(family_hash, *, limit):
        limits.append(limit)
        return original(family_hash, limit=limit)

    monkeypatch.setattr(evidence, "read_family_evidence", capture_limit)
    with override_settings(ORBIT_CONFIG={"MCP_MAX_LIMIT": configured}):
        summarize_request_family("missing-family", limit=100000)

    expected = evidence.MAX_FAMILY_LIMIT if configured == 100000 else 100
    assert limits == [expected]


def test_compact_summary_is_substantially_smaller_than_event_detail(family):
    from orbit.request_context import summarize_request_family

    OrbitEntry.objects.bulk_create(
        [
            OrbitEntry(
                type=OrbitEntry.TYPE_QUERY,
                family_hash=family.family_hash,
                payload={
                    "is_slow": False,
                    "is_duplicate": False,
                    "duplicate_count": 0,
                    "database": "default",
                },
            )
            for _ in range(40)
        ]
    )
    detail = evidence.read_family_evidence(family.family_hash, limit=100)
    summary = summarize_request_family(family.family_hash)

    assert summary["count"] == detail["count"] == 43
    assert summary["evidence_quality"] == detail["evidence_quality"]
    assert len(json.dumps(summary)) < len(json.dumps(detail)) // 2


def test_summary_does_not_mutate_source_evidence(family, monkeypatch):
    from orbit.request_context import summarize_request_family

    source = evidence.read_family_evidence(family.family_hash, limit=100)
    before = deepcopy(source)
    monkeypatch.setattr(evidence, "read_family_evidence", lambda *a, **kw: source)

    summarize_request_family(family.family_hash)

    assert source == before


@pytest.mark.parametrize("status", [401, 302, None, True, 700])
def test_only_valid_error_statuses_produce_observed_http_signals(status):
    from orbit.request_context import summarize_request_family

    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        family_hash="status-family",
        payload={"status_code": status},
    )
    result = summarize_request_family("status-family")

    expected = {"http_client_errors": 1} if status == 401 else {}
    assert result["summary"]["observed_signals"] == expected


def test_contract_cap_recovery_does_not_recommend_impossible_retry():
    from orbit.request_context import _quality_for_cap

    cap = evidence.MAX_FAMILY_LIMIT
    source = {
        "count": cap,
        "evidence_quality": {
            "next_actions": [
                {"code": "retry_with_higher_limit", "parameters": {"limit": cap * 2}}
            ]
        },
    }
    before = deepcopy(source)

    result = _quality_for_cap(source, cap)

    assert result["next_actions"] == [
        {"code": "review_family_scope", "parameters": {"event_limit": cap}}
    ]
    assert source == before
