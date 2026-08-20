"""
Tests for query diagnostics — agentic N+1 and slow-query investigation contracts.
Validates acceptance criteria from .Codex/workspace/spec.md.
"""

import json
import uuid

import pytest

from orbit.models import OrbitEntry

pytestmark = pytest.mark.django_db


def _n_plus_one_pattern(**overrides):
    pattern = {
        "kind": "n_plus_one_candidate",
        "confidence": "high",
        "query_summary": "SELECT reviews",
        "caller_key": "/srv/project/orders/views.py:42:list_orders",
        "occurrences": 4,
        "unique_parameter_sets": 4,
        "capture_limits": [],
    }
    pattern.update(overrides)
    return pattern


def _call_mcp_tool(name, **kwargs):
    from orbit.mcp_server import create_mcp_server

    server = create_mcp_server()
    tool = server._tool_manager._tools[name]
    return json.loads(tool.fn(**kwargs))


class TestExplainNPlusOne:
    def test_uses_only_the_requested_family_as_evidence(self):
        from orbit.agentic import explain_n_plus_one

        OrbitEntry.objects.create(
            type=OrbitEntry.TYPE_REQUEST,
            family_hash="target-family",
            payload={
                "method": "GET",
                "path": "/orders/",
                "query_patterns": [_n_plus_one_pattern()],
            },
        )
        OrbitEntry.objects.create(
            type=OrbitEntry.TYPE_QUERY,
            family_hash="target-family",
            duration_ms=12,
            payload={"sql": "SELECT * FROM reviews", "is_duplicate": True},
        )
        OrbitEntry.objects.create(
            type=OrbitEntry.TYPE_REQUEST,
            family_hash="other-family",
            payload={
                "method": "GET",
                "path": "/admin/",
                "query_patterns": [_n_plus_one_pattern(query_summary="SELECT secrets")],
            },
        )

        data = explain_n_plus_one("target-family")

        assert data["family_hash"] == "target-family"
        assert data["status"] == "candidate_detected"
        assert [finding["query_summary"] for finding in data["findings"]] == [
            "SELECT reviews"
        ]
        assert data["query_analysis"]["total"] == 1

    def test_accepts_historical_patterns_and_ignores_malformed_values(self):
        from orbit.agentic import explain_n_plus_one

        OrbitEntry.objects.create(
            type=OrbitEntry.TYPE_REQUEST,
            family_hash="historical-family",
            payload={
                "query_patterns": [
                    "legacy-corruption",
                    None,
                    42,
                    _n_plus_one_pattern(capture_limits=["query_analysis_truncated"]),
                    {"kind": "exact_duplicate", "capture_limits": ["ignored"]},
                ]
            },
        )

        data = explain_n_plus_one("historical-family")

        assert data["status"] == "candidate_detected"
        assert data["n_plus_one_count"] == 1
        assert len(data["findings"]) == 1
        assert data["capture_limits"] == ["query_analysis_truncated"]

    @pytest.mark.parametrize("family_hash", ["missing-family", ""])
    def test_returns_a_stable_error_for_unknown_family(self, family_hash):
        from orbit.agentic import explain_n_plus_one

        assert explain_n_plus_one(family_hash) == {
            "error": f"No entries found for family_hash: {family_hash}"
        }


class TestInvestigateSlowQuery:
    def test_scopes_related_query_evidence_to_matching_signature_and_family(self):
        from orbit.agentic import investigate_slow_query

        selected = OrbitEntry.objects.create(
            type=OrbitEntry.TYPE_QUERY,
            family_hash="checkout-family",
            duration_ms=950,
            payload={
                "sql": "SELECT * FROM orders WHERE customer_id = %s",
                "is_slow": True,
            },
        )
        same_family_match = OrbitEntry.objects.create(
            type=OrbitEntry.TYPE_QUERY,
            family_hash="checkout-family",
            duration_ms=20,
            payload={"sql": "SELECT * FROM orders WHERE customer_id = %s"},
        )
        same_family_other = OrbitEntry.objects.create(
            type=OrbitEntry.TYPE_QUERY,
            family_hash="checkout-family",
            payload={"sql": "SELECT * FROM products"},
        )
        other_family_match = OrbitEntry.objects.create(
            type=OrbitEntry.TYPE_QUERY,
            family_hash="other-family",
            payload={"sql": "SELECT * FROM orders WHERE customer_id = %s"},
        )

        data = investigate_slow_query(str(selected.id))

        related_ids = {item["id"] for item in data["related_queries"]}
        assert data["family_hash"] == "checkout-family"
        assert data["same_signature_executions"] == 2
        assert related_ids == {str(selected.id), str(same_family_match.id)}
        assert str(same_family_other.id) not in related_ids
        assert str(other_family_match.id) not in related_ids

    @pytest.mark.parametrize("entry_id", ["not-a-uuid", str(uuid.uuid4())])
    def test_returns_a_stable_error_for_unknown_or_invalid_query_id(self, entry_id):
        from orbit.agentic import investigate_slow_query

        assert investigate_slow_query(entry_id) == {
            "error": f"No query entry found for id: {entry_id}"
        }


class TestMcpSerialization:
    def test_tools_return_json_safe_and_path_redacted_diagnostics(self):
        query = OrbitEntry.objects.create(
            type=OrbitEntry.TYPE_QUERY,
            family_hash="mcp-family",
            duration_ms=800,
            payload={
                "sql": "SELECT * FROM orders WHERE customer_id = %s",
                "is_slow": True,
                "caller": {"filename": "/srv/private/orders/views.py"},
            },
        )
        OrbitEntry.objects.create(
            type=OrbitEntry.TYPE_REQUEST,
            family_hash="mcp-family",
            payload={"query_patterns": [_n_plus_one_pattern()]},
        )

        n_plus_one = _call_mcp_tool("explain_n_plus_one", family_hash="mcp-family")
        slow_query = _call_mcp_tool("investigate_slow_query", entry_id=str(query.id))
        encoded = json.dumps({"n_plus_one": n_plus_one, "slow_query": slow_query})

        assert n_plus_one["status"] == "candidate_detected"
        assert slow_query["entry_id"] == str(query.id)
        assert slow_query["query"]["payload"]["caller"]["filename"] == "views.py"
        assert "/srv/private" not in encoded

    def test_tools_serialize_unknown_identifiers_as_json_errors(self):
        n_plus_one = _call_mcp_tool("explain_n_plus_one", family_hash="not-found")
        slow_query = _call_mcp_tool("investigate_slow_query", entry_id="not-a-uuid")

        assert n_plus_one == {"error": "No entries found for family_hash: not-found"}
        assert slow_query == {"error": "No query entry found for id: not-a-uuid"}


class TestReviewerRegressionCases:
    def test_materialized_count_without_findings_remains_a_candidate(self):
        from orbit.agentic import explain_n_plus_one

        OrbitEntry.objects.create(
            type=OrbitEntry.TYPE_REQUEST,
            family_hash="count-only-family",
            payload={"n_plus_one_count": 2, "query_patterns": ["corrupt"]},
        )

        data = explain_n_plus_one("count-only-family")

        assert data["status"] == "candidate_detected"
        assert data["evidence_state"] == "materialized_count_only"
        assert data["findings"] == []

    def test_historical_sql_without_signature_is_related_to_new_signature(self):
        from orbit.agentic import investigate_slow_query

        selected = OrbitEntry.objects.create(
            type=OrbitEntry.TYPE_QUERY,
            family_hash="mixed-evidence-family",
            payload={
                "sql": "SELECT * FROM orders WHERE customer_id = %s",
                "query_signature": "new-signature",
                "is_slow": True,
            },
        )
        historical = OrbitEntry.objects.create(
            type=OrbitEntry.TYPE_QUERY,
            family_hash="mixed-evidence-family",
            payload={"sql": "SELECT * FROM orders WHERE customer_id = %s"},
        )

        data = investigate_slow_query(str(selected.id))

        assert {item["id"] for item in data["related_queries"]} == {
            str(selected.id),
            str(historical.id),
        }

    def test_mcp_redacts_traceback_text_and_tolerates_corrupt_query_payload(self):
        OrbitEntry.objects.create(
            type=OrbitEntry.TYPE_REQUEST,
            family_hash="traceback-redaction",
            payload={"traceback_string": 'File "/srv/private/app/views.py", line 4'},
        )
        OrbitEntry.objects.create(
            type=OrbitEntry.TYPE_QUERY,
            family_hash="traceback-redaction",
            payload=[],
        )

        diagnostics = _call_mcp_tool(
            "explain_n_plus_one", family_hash="traceback-redaction"
        )
        detail = _call_mcp_tool("get_request_detail", family_hash="traceback-redaction")
        encoded = json.dumps(detail)

        assert "/srv/private" not in encoded
        assert "views.py" in encoded
        assert diagnostics["query_analysis"]["total"] == 1
