"""
Smoke tests for the v0.9.0 UX overhaul: grouped navigation, lazy Stats sections,
version sourcing, and the Export-button removal.
"""

import pytest
from django.test import override_settings
from django.urls import reverse

from orbit import __version__ as ORBIT_VERSION
from orbit.models import OrbitEntry


@pytest.mark.django_db
def test_dashboard_has_grouped_nav_and_standalone_all_events(client):
    html = client.get(reverse("orbit:dashboard")).content.decode()

    # Three collapsible groups
    for group in ("Core", "Infrastructure", "Application"):
        assert group in html

    # "All Events" is rendered exactly once (standalone, not duplicated inside a group)
    assert html.count(">All Events<") == 1


@pytest.mark.django_db
def test_dashboard_shows_package_version_not_stale(client):
    html = client.get(reverse("orbit:dashboard")).content.decode()
    assert f"v{ORBIT_VERSION}" in html
    assert "v0.6.3" not in html


@pytest.mark.django_db
def test_health_shows_package_version_not_stale(client):
    html = client.get(reverse("orbit:health")).content.decode()
    assert f"v{ORBIT_VERSION}" in html
    assert "v0.6.3" not in html


@pytest.mark.django_db
def test_detail_panel_has_x_cloak_to_prevent_flash(client):
    """The slide-over must be hidden until Alpine initializes (no FOUC)."""
    html = client.get(reverse("orbit:dashboard")).content.decode()
    assert "x-cloak" in html


@pytest.mark.django_db
def test_export_filtered_button_removed_but_endpoint_kept(client):
    html = client.get(reverse("orbit:dashboard")).content.decode()
    assert "Export Filtered" not in html
    assert "exportAll" not in html

    # Per-entry export endpoint still works
    entry = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST, payload={"status": 200}
    )
    assert client.get(reverse("orbit:export", args=[entry.id])).status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize("section", ["trends", "database", "cache", "jobs", "security"])
def test_stats_section_endpoints_render(client, section):
    url = reverse("orbit:stats_section", args=[section])
    assert client.get(url, {"range": "24h"}).status_code == 200


@pytest.mark.django_db
def test_unknown_stats_section_returns_404(client):
    assert client.get(reverse("orbit:stats_section", args=["nope"])).status_code == 404


@pytest.mark.django_db
def test_stats_page_renders_headline(client):
    html = client.get(reverse("orbit:stats")).content.decode()
    assert "Apdex Score" in html
    # Heavy sections are lazy-loaded via HTMX, not inlined
    assert "stats/section/trends" in html


@pytest.mark.django_db
@override_settings(
    ORBIT_CONFIG={
        "ENABLED": True,
        "MCP_ENABLED": True,
        "MCP_INCLUDE_PAYLOADS": False,
        "RECORD_LLM": True,
        "LLM_CAPTURE_CONTENT": False,
        "LLM_CAPTURE_TOOL_CALL_ARGUMENTS": False,
    }
)
def test_health_page_shows_agent_safety_status(client):
    html = client.get(reverse("orbit:health")).content.decode()

    assert "Agent & MCP Safety" in html
    assert "metadata only" in html
    assert "not captured" in html


@pytest.mark.django_db
def test_detail_panel_exposes_copy_fix_handoff_button(client):
    entry = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        family_hash="fam-agent-prompt",
        payload={"method": "GET", "path": "/checkout/", "status_code": 500},
    )

    html = client.get(reverse("orbit:detail", args=[entry.id])).content.decode()

    assert "Copy fix handoff" in html
    assert reverse("orbit:agent_handoff", args=[entry.id]) in html


@pytest.mark.django_db
def test_detail_panel_explains_a_failed_request_with_evidence(client):
    entry = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        family_hash="fam-detail-guidance",
        payload={"method": "POST", "full_path": "/checkout/", "status_code": 500},
    )

    html = client.get(reverse("orbit:detail", args=[entry.id])).content.decode()

    assert "Investigation guide" in html
    assert "POST /checkout/ returned HTTP 500." in html
    assert "This request failed before a successful response was recorded." in html
    assert "Open the related entries or copy the agent prompt" in html


@pytest.mark.django_db
def test_detail_panel_explains_a_slow_query_without_claiming_a_cause(client):
    entry = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_QUERY,
        duration_ms=825,
        payload={"sql": "SELECT * FROM orders", "is_slow": True},
    )

    html = client.get(reverse("orbit:detail", args=[entry.id])).content.decode()

    assert "A SQL query took 825.0ms." in html
    assert "exceeded Orbit" in html
    assert "slow-query threshold" in html
    assert "Run Explain Plan" in html


@pytest.mark.django_db
def test_detail_panel_turns_an_informational_log_into_timeline_context(client):
    entry = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_LOG,
        payload={"level": "INFO", "message": "worker started"},
    )

    html = client.get(reverse("orbit:detail", args=[entry.id])).content.decode()

    assert "An info log was recorded: &quot;worker started&quot;." in html
    assert "Informational logs are timeline context" in html
    assert "No remediation is suggested from this log alone." in html


@pytest.mark.django_db
def test_detail_panel_explains_a_successful_request_as_a_baseline(client):
    entry = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        duration_ms=34,
        payload={"method": "GET", "path": "/health/", "status_code": 200},
    )

    html = client.get(reverse("orbit:detail", args=[entry.id])).content.decode()

    assert "GET /health/ returned HTTP 200 in 34.0ms." in html
    assert "no error, slow-query, or repeated-query signal" in html
    assert "No remediation is indicated" in html


@pytest.mark.django_db
def test_detail_panel_explains_a_signal_as_framework_context(client):
    entry = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_SIGNAL,
        payload={"signal": "django.core.signals.request_finished"},
    )

    html = client.get(reverse("orbit:detail", args=[entry.id])).content.decode()

    assert "A Django signal was dispatched: django.core.signals.request_finished." in html
    assert "Signals show framework activity, not a failure by themselves." in html
    assert "Ignore it unless it aligns with an error or slow request." in html


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("entry_type", "payload", "expected"),
    [
        (
            OrbitEntry.TYPE_CACHE,
            {"operation": "get", "hit": False},
            "A cache lookup missed.",
        ),
        (
            OrbitEntry.TYPE_GATE,
            {"result": "denied"},
            "An authorization check denied access.",
        ),
        (
            OrbitEntry.TYPE_JOB,
            {"status": "failed"},
            "A background job was recorded as failed.",
        ),
        (
            OrbitEntry.TYPE_TRANSACTION,
            {"status": "rolled_back"},
            "A database transaction was rolled back.",
        ),
    ],
)
def test_detail_panel_highlights_operational_signal_without_claiming_root_cause(
    client, entry_type, payload, expected
):
    entry = OrbitEntry.objects.create(type=entry_type, payload=payload)

    html = client.get(reverse("orbit:detail", args=[entry.id])).content.decode()

    assert expected in html


@pytest.mark.django_db
def test_agent_handoff_endpoint_includes_evidence_hypotheses_and_tests(client):
    entry = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        family_hash="fam-agent-handoff",
        payload={
            "method": "POST",
            "path": "/checkout/",
            "status_code": 500,
            "headers": {"Authorization": "secret-handoff-token"},
        },
    )
    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_EXCEPTION,
        family_hash="fam-agent-handoff",
        fingerprint="fp-agent-handoff",
        payload={
            "exception_type": "ValueError",
            "message": "payment token rejected",
        },
    )

    response = client.get(reverse("orbit:agent_handoff", args=[entry.id]))

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/plain")
    content = response.content.decode()
    assert content.startswith(
        "You are debugging a Django issue using Django Orbit runtime evidence."
    )
    assert "## Fix hypotheses" in content
    assert "## Regression test plan" in content
    assert "fam-agent-handoff" in content
    assert "secret-handoff-token" not in content


@pytest.mark.django_db
def test_agent_handoff_endpoint_rejects_unlinked_entries(client):
    entry = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_LOG, payload={"message": "orphan"}
    )

    response = client.get(reverse("orbit:agent_handoff", args=[entry.id]))

    assert response.status_code == 400
    assert "family_hash" in response.content.decode()


@pytest.mark.django_db
def test_agent_prompt_endpoint_returns_prompt_for_family(client):
    entry = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        family_hash="fam-agent-prompt",
        payload={"method": "GET", "path": "/checkout/", "status_code": 500},
    )
    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_EXCEPTION,
        family_hash="fam-agent-prompt",
        fingerprint="fp-agent-prompt",
        payload={"exception_type": "ValueError", "message": "bad checkout"},
    )

    response = client.get(reverse("orbit:agent_prompt", args=[entry.id]))

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/plain")
    content = response.content.decode()
    assert "You are debugging a Django issue" in content
    assert "fam-agent-prompt" in content


@pytest.mark.django_db
def test_agent_prompt_endpoint_rejects_unlinked_entries(client):
    entry = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_LOG, payload={"message": "orphan"}
    )

    response = client.get(reverse("orbit:agent_prompt", args=[entry.id]))

    assert response.status_code == 400
    assert "family_hash" in response.content.decode()
