import json

import pytest
from django.test import override_settings

from orbit.models import OrbitEntry

pytestmark = pytest.mark.django_db


@pytest.fixture
def request_entry(db):
    return OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        family_hash="fam-agentic",
        duration_ms=320.0,
        payload={
            "method": "POST",
            "path": "/checkout/",
            "full_path": "/checkout/?debug=1",
            "status_code": 500,
            "headers": {"Authorization": "Bearer secret", "Accept": "application/json"},
            "body": {"email": "user@example.com", "password": "secret"},
            "query_count": 3,
            "duplicate_query_count": 2,
        },
    )


@pytest.fixture
def related_entries(db, request_entry):
    slow_query = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_QUERY,
        family_hash="fam-agentic",
        duration_ms=900.0,
        payload={
            "sql": "SELECT * FROM orders WHERE user_id = %s",
            "params": [123],
            "duration_ms": 900.0,
            "is_slow": True,
            "is_duplicate": True,
            "duplicate_count": 2,
            "caller": {
                "filename": "/app/orders/views.py",
                "lineno": 42,
                "function": "checkout",
            },
        },
    )
    log = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_LOG,
        family_hash="fam-agentic",
        payload={"level": "ERROR", "message": "payment token rejected"},
    )
    exception = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_EXCEPTION,
        family_hash="fam-agentic",
        fingerprint="fp-checkout",
        payload={
            "exception_type": "ValueError",
            "message": "payment token rejected",
            "traceback": [
                {
                    "filename": "/app/orders/views.py",
                    "lineno": 45,
                    "name": "checkout",
                    "line": "raise ValueError()",
                }
            ],
            "traceback_string": "very long traceback",
        },
    )
    return slow_query, log, exception


def test_agent_safe_serialize_masks_and_truncates_payload(request_entry):
    from orbit.agentic import agent_safe_serialize_entry

    data = agent_safe_serialize_entry(request_entry, max_payload_chars=180)

    assert data["id"] == str(request_entry.id)
    assert data["summary"] == request_entry.summary
    assert data["payload_truncated"] is True
    encoded = json.dumps(data)
    assert "secret" not in encoded
    assert "***HIDDEN***" in encoded


def test_agent_safe_serialize_can_omit_payload(request_entry):
    from orbit.agentic import agent_safe_serialize_entry

    data = agent_safe_serialize_entry(request_entry, include_payload=False)

    assert "payload" not in data
    assert data["payload_omitted"] is True


def test_audit_mcp_exposure_reports_safety_config(settings):
    from orbit.agentic import audit_mcp_exposure

    settings.ORBIT_CONFIG = {
        "MCP_ENABLED": True,
        "MCP_INCLUDE_PAYLOADS": False,
        "MCP_MAX_LIMIT": 25,
    }

    data = audit_mcp_exposure()

    assert data["mcp_enabled"] is True
    assert data["include_payloads"] is False
    assert data["max_limit"] == 25
    assert data["safety"]["serializer"] == "agent_safe_serialize_entry"


def test_investigate_request_builds_diagnosis(request_entry, related_entries):
    from orbit.agentic import investigate_request

    data = investigate_request("fam-agentic")

    assert data["family_hash"] == "fam-agentic"
    assert data["request"]["id"] == str(request_entry.id)
    assert data["diagnosis"]["severity"] == "error"
    assert "exception" in data["diagnosis"]["signals"]
    assert "slow_query" in data["diagnosis"]["signals"]
    assert data["query_analysis"]["slow_count"] == 1
    assert data["query_analysis"]["duplicate_count"] == 1
    assert data["event_counts"] == {"request": 1, "query": 1, "log": 1, "exception": 1}


def test_investigate_exception_group_summarizes_blast_radius(
    request_entry, related_entries
):
    from orbit.agentic import investigate_exception_group

    data = investigate_exception_group("fp-checkout")

    assert data["fingerprint"] == "fp-checkout"
    assert data["count"] == 1
    assert data["representative"]["type"] == "exception"
    assert data["affected_paths"] == [{"path": "/checkout/", "count": 1}]
    assert data["diagnosis"]["severity"] == "error"


def test_create_incident_bundle_from_request(request_entry, related_entries):
    from orbit.agentic import create_incident_bundle

    data = create_incident_bundle("family_hash", "fam-agentic")

    assert data["source"] == {"type": "family_hash", "value": "fam-agentic"}
    assert data["primary"]["family_hash"] == "fam-agentic"
    assert data["agent_handoff"]["recommended_next_actions"]
    assert data["safety_report"]["payloads_masked"] is True


def test_create_incident_bundle_markdown_from_request(request_entry, related_entries):
    from orbit.agentic import create_incident_bundle

    markdown = create_incident_bundle("family_hash", "fam-agentic", format="markdown")

    assert isinstance(markdown, str)
    assert "# Django Orbit Incident Bundle" in markdown
    assert "fam-agentic" in markdown
    assert "payment token rejected" in markdown
    assert "secret" not in markdown


def test_create_incident_bundle_prompt_is_agent_ready(request_entry, related_entries):
    from orbit.agentic import create_incident_bundle

    prompt = create_incident_bundle("family_hash", "fam-agentic", format="prompt")

    assert prompt.startswith(
        "You are debugging a Django issue using Django Orbit runtime evidence."
    )
    assert "Write a failing regression test first" in prompt
    assert "fam-agentic" in prompt
    assert "orders/views.py" in prompt
    assert "secret" not in prompt


def test_preview_masked_entry_returns_agent_safe_payload(request_entry):
    from orbit.agentic import preview_masked_entry

    data = preview_masked_entry(str(request_entry.id))
    encoded = json.dumps(data)

    assert data["entry"]["id"] == str(request_entry.id)
    assert data["entry"]["payload_masked"] is True
    assert data["safety_report"]["payloads_masked"] is True
    assert "payload.headers.Authorization" in data["risk_keys"]
    assert "secret" not in encoded
    assert "***HIDDEN***" in encoded


def test_preview_masked_entry_handles_unknown_entry():
    from orbit.agentic import preview_masked_entry

    data = preview_masked_entry("00000000-0000-0000-0000-000000000000")

    assert data == {
        "error": "No entry found for id: 00000000-0000-0000-0000-000000000000"
    }


def test_find_sensitive_payload_risks_masks_candidates(request_entry):
    from orbit.agentic import find_sensitive_payload_risks

    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_LOG,
        payload={
            "message": "oauth callback",
            "client_secret": "raw-secret",
            "nested": {"access_token": "token-value"},
        },
    )

    data = find_sensitive_payload_risks(limit=5)
    encoded = json.dumps(data)

    assert data["count"] == 2
    assert all(candidate["risk_keys"] for candidate in data["candidates"])
    assert "raw-secret" not in encoded
    assert "token-value" not in encoded
    assert "secret" not in encoded.lower().replace("client_secret", "")


def test_list_agent_safe_fields_documents_payload_policy():
    from orbit.agentic import list_agent_safe_fields

    data = list_agent_safe_fields(OrbitEntry.TYPE_REQUEST)

    assert data["entry_type"] == "request"
    assert "id" in data["common_fields"]
    assert data["payload_policy"]["masked"] is True
    assert "headers.Authorization" in data["payload_policy"]["high_risk_paths"]


def test_list_agent_safe_fields_rejects_unknown_type():
    from orbit.agentic import list_agent_safe_fields

    data = list_agent_safe_fields("unknown")

    assert data == {"error": "Unsupported entry_type: unknown"}


def test_find_n_plus_one_candidates_ranks_duplicate_query_requests(
    request_entry, related_entries
):
    from orbit.agentic import find_n_plus_one_candidates

    data = find_n_plus_one_candidates(hours=72)

    assert data["count"] == 1
    candidate = data["candidates"][0]
    assert candidate["path"] == "/checkout/"
    assert candidate["method"] == "POST"
    assert candidate["duplicate_query_count"] == 2
    assert candidate["duplicate_signatures"][0]["count"] == 1
    assert "investigate_request" in {
        tool["tool"] for tool in candidate["suggested_tools"]
    }


def test_summarize_exception_groups_returns_recent_group_summary(
    request_entry, related_entries
):
    from orbit.agentic import summarize_exception_groups

    data = summarize_exception_groups(hours=72)

    assert data["count"] == 1
    group = data["groups"][0]
    assert group["fingerprint"] == "fp-checkout"
    assert group["count"] == 1
    assert group["affected_paths"] == [{"path": "/checkout/", "count": 1}]
    assert group["representative"]["type"] == "exception"


def test_investigate_endpoint_empty_result_is_stable():
    from orbit.agentic import investigate_endpoint

    data = investigate_endpoint("/missing/", method="GET", hours=72)

    assert data["endpoint"] == {"path": "/missing/", "method": "GET"}
    assert data["request_count"] == 0
    assert data["suggested_tools"] == []


def test_incident_bundle_json_includes_coding_agent_handoff(
    request_entry, related_entries
):
    from orbit.agentic import create_incident_bundle

    data = create_incident_bundle("family_hash", "fam-agentic")

    handoff = data["agent_handoff"]
    assert "context_for_coding_agents" in handoff
    assert "suggested_prompt" in handoff
    assert handoff["next_tool_sequence"][0]["tool"] == "investigate_request"
    assert "/app/orders/views.py" in data["likely_code_surfaces"]


def test_incident_bundle_markdown_is_coding_agent_ready(request_entry, related_entries):
    from orbit.agentic import create_incident_bundle

    markdown = create_incident_bundle("family_hash", "fam-agentic", format="markdown")

    assert "## Agent Handoff" in markdown
    assert "Codex, Claude or Cursor" in markdown
    assert "## Likely Code Surfaces" in markdown
    assert "investigate_request" in markdown
    assert "secret" not in markdown


def test_propose_fix_hypotheses_from_exception_group(request_entry, related_entries):
    from orbit.agentic import propose_fix_hypotheses

    data = propose_fix_hypotheses("fingerprint", "fp-checkout")

    assert data["source"] == {"type": "fingerprint", "value": "fp-checkout"}
    assert data["hypotheses"]
    assert data["hypotheses"][0]["confidence"] in {"high", "medium", "low"}
    assert any("orders/views.py" in item for item in data["likely_code_surfaces"])
    assert data["safety"]["does_not_modify_code"] is True


def test_propose_test_plan_from_request(request_entry, related_entries):
    from orbit.agentic import propose_test_plan

    data = propose_test_plan("family_hash", "fam-agentic")

    assert data["source"] == {"type": "family_hash", "value": "fam-agentic"}
    assert data["recommended_tests"]
    assert any(test["type"] == "integration" for test in data["recommended_tests"])
    assert any(
        "checkout" in test["target"].lower() for test in data["recommended_tests"]
    )
    assert data["safety"]["does_not_modify_code"] is True


def test_generate_pr_context_builds_release_ready_summary(
    request_entry, related_entries
):
    from orbit.agentic import generate_pr_context

    data = generate_pr_context("family_hash", "fam-agentic", hours=72)

    assert data["source"] == {"type": "family_hash", "value": "fam-agentic"}
    assert data["suggested_title"].startswith("Fix")
    assert "runtime evidence" in data["summary"].lower()
    assert data["evidence"]["severity"] == "error"
    assert data["fix_hypotheses"]
    assert data["test_plan"]
    assert data["release_risk"]["risk_level"] == "blocker"
    assert "/app/orders/views.py" in data["likely_code_surfaces"]
    assert "## Orbit Evidence" in data["pr_body_markdown"]
    assert "secret" not in json.dumps(data)


def test_generate_pr_context_markdown_returns_paste_ready_body(
    request_entry, related_entries
):
    from orbit.agentic import generate_pr_context

    markdown = generate_pr_context(
        "fingerprint", "fp-checkout", hours=72, format="markdown"
    )

    assert markdown.startswith("## Orbit Evidence")
    assert "### Suggested Tests" in markdown
    assert "### Release Risk" in markdown
    assert "secret" not in markdown


def test_generate_pr_context_propagates_unknown_source_error():
    from orbit.agentic import generate_pr_context

    data = generate_pr_context("family_hash", "missing")

    assert data == {"error": "No entries found for family_hash: missing"}


def test_investigate_endpoint_summarizes_recent_endpoint_health(
    request_entry, related_entries
):
    from orbit.agentic import investigate_endpoint

    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        family_hash="fam-checkout-ok",
        duration_ms=120.0,
        payload={"method": "POST", "path": "/checkout/", "status_code": 200},
    )

    data = investigate_endpoint("/checkout/", method="POST", hours=72)

    assert data["endpoint"] == {"path": "/checkout/", "method": "POST"}
    assert data["request_count"] == 2
    assert data["error_count"] == 1
    assert data["error_rate_pct"] == 50.0
    assert data["avg_duration_ms"] == 220.0
    assert data["slowest_requests"][0]["family_hash"] == "fam-agentic"
    assert data["query_analysis"]["total"] == 1
    assert data["top_exception_groups"][0]["fingerprint"] == "fp-checkout"
    assert "investigate_request" in {tool["tool"] for tool in data["suggested_tools"]}


def test_compare_endpoint_windows_detects_regression(db):
    from django.utils import timezone
    from orbit.agentic import compare_endpoint_windows

    baseline_time = timezone.now() - timezone.timedelta(hours=8)
    current_time = timezone.now() - timezone.timedelta(minutes=20)
    baseline = []
    current = []
    for index in range(4):
        baseline.append(
            OrbitEntry.objects.create(
                type=OrbitEntry.TYPE_REQUEST,
                family_hash=f"baseline-{index}",
                duration_ms=100.0,
                payload={"method": "POST", "path": "/checkout/", "status_code": 200},
            )
        )
    for index in range(4):
        status = 500 if index < 2 else 200
        current.append(
            OrbitEntry.objects.create(
                type=OrbitEntry.TYPE_REQUEST,
                family_hash=f"current-{index}",
                duration_ms=400.0,
                payload={
                    "method": "POST",
                    "path": "/checkout/",
                    "status_code": status,
                    "duplicate_query_count": 1 if index == 0 else 0,
                },
            )
        )
    OrbitEntry.objects.filter(id__in=[entry.id for entry in baseline]).update(
        created_at=baseline_time
    )
    OrbitEntry.objects.filter(id__in=[entry.id for entry in current]).update(
        created_at=current_time
    )
    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_EXCEPTION,
        family_hash="current-0",
        fingerprint="fp-current",
        payload={"exception_type": "ValueError", "message": "checkout failed"},
    )

    data = compare_endpoint_windows(
        "/checkout/", method="POST", baseline_hours=24, current_hours=2
    )

    assert data["endpoint"] == {"path": "/checkout/", "method": "POST"}
    assert data["classification"] == "regression"
    assert data["current"]["error_rate_pct"] == 50.0
    assert data["baseline"]["error_rate_pct"] == 0.0
    assert data["delta"]["error_rate_pct"] == 50.0
    assert "fp-current" in data["new_exception_fingerprints"]
    assert data["recommendation"].startswith("Investigate")


def test_compare_endpoint_windows_handles_insufficient_data(db):
    from orbit.agentic import compare_endpoint_windows

    data = compare_endpoint_windows("/missing/", method="GET")

    assert data["classification"] == "insufficient_data"
    assert data["current"]["request_count"] == 0
    assert data["baseline"]["request_count"] == 0


def test_daily_health_brief_prioritizes_actionable_runtime_signals(
    request_entry, related_entries
):
    from orbit.agentic import daily_health_brief

    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_JOB,
        family_hash="job-family",
        duration_ms=2000.0,
        payload={"name": "sync_orders", "status": "failed", "error": "timeout"},
    )
    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_LOG,
        payload={"level": "WARNING", "message": "cache warming skipped"},
    )

    data = daily_health_brief(hours=72, limit=5)

    assert data["hours"] == 72
    assert data["summary"]["requests"] == 1
    assert data["summary"]["exceptions"] == 1
    assert data["summary"]["failed_jobs"] == 1
    assert data["top_issues"][0]["severity"] == "error"
    assert any(issue["type"] == "job_failure" for issue in data["top_issues"])
    assert any(
        "generate_release_risk_brief" == tool["tool"]
        for tool in data["suggested_tools"]
    )


def test_generate_release_risk_brief_flags_blockers(request_entry, related_entries):
    from orbit.agentic import generate_release_risk_brief

    data = generate_release_risk_brief(hours=72)

    assert data["hours"] == 72
    assert data["risk_level"] == "blocker"
    assert "exception_groups" in data["blockers"]
    assert data["checks"]["error_requests"]["count"] == 1
    assert data["checks"]["slow_queries"]["count"] == 1
    assert data["recommendation"].startswith("Do not release")


def test_generate_release_risk_brief_all_clear_without_signals(db):
    from orbit.agentic import generate_release_risk_brief

    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        family_hash="fam-ok",
        duration_ms=80.0,
        payload={"method": "GET", "path": "/health/", "status_code": 200},
    )

    data = generate_release_risk_brief(hours=72)

    assert data["risk_level"] == "low"
    assert data["blockers"] == []
    assert data["recommendation"].startswith("No blocker")


def test_mcp_incident_bundle_markdown_returns_raw_text(request_entry, related_entries):
    from orbit.mcp_server import create_mcp_server
    from tests.test_mcp import _get_tool

    fn = _get_tool(create_mcp_server(), "create_incident_bundle")
    markdown = fn(
        source_type="family_hash", source_value="fam-agentic", format="markdown"
    )

    assert markdown.startswith("# Django Orbit Incident Bundle")
    assert not markdown.startswith('"')


def test_build_debug_brief_matches_ticket_text(request_entry, related_entries):
    from orbit.agentic import build_debug_brief

    data = build_debug_brief("checkout payment token rejected", hours=72)

    assert data["query"] == "checkout payment token rejected"
    assert data["matches"]["exceptions"][0]["id"] == str(related_entries[2].id)
    assert data["matches"]["requests"][0]["id"] == str(request_entry.id)
    assert data["suggested_tools"][0]["tool"] == "create_incident_bundle"


@pytest.mark.django_db
@override_settings(ORBIT_CONFIG={"MCP_ENABLED": True})
def test_high_level_mcp_tools_are_registered():
    from orbit.mcp_server import create_mcp_server
    from tests.test_mcp import _call_tool

    audit = _call_tool(create_mcp_server(), "audit_mcp_exposure")

    assert audit["mcp_enabled"] is True
    assert "investigate_request" in audit["high_level_tools"]
    assert "propose_fix_hypotheses" in audit["high_level_tools"]
    assert "propose_test_plan" in audit["high_level_tools"]
    assert "investigate_endpoint" in audit["high_level_tools"]
    assert "daily_health_brief" in audit["high_level_tools"]
    assert "generate_release_risk_brief" in audit["high_level_tools"]
