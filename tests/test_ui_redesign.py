"""
Smoke tests for the v0.9.0 UX overhaul: grouped navigation, lazy Stats sections,
version sourcing, and the Export-button removal.
"""

from django.test import override_settings
from django.urls import reverse

import pytest

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
def test_detail_panel_exposes_copy_agent_prompt_button(client):
    entry = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        family_hash="fam-agent-prompt",
        payload={"method": "GET", "path": "/checkout/", "status_code": 500},
    )

    html = client.get(reverse("orbit:detail", args=[entry.id])).content.decode()

    assert "Copy agent prompt" in html
    assert reverse("orbit:agent_prompt", args=[entry.id]) in html


@pytest.mark.django_db
def test_detail_panel_guides_successful_request_from_recorded_fields(client):
    entry = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        duration_ms=7.5,
        payload={
            "method": "GET",
            "full_path": "/books/",
            "status_code": 200,
        },
    )

    html = client.get(reverse("orbit:detail", args=[entry.id])).content.decode()

    assert "GET /books/ returned HTTP 200 in 7.5 ms." in html
    assert "without recording an error signal" in html
    assert "Open related entries or Stats" in html
    assert "A http request was recorded." not in html


@pytest.mark.django_db
def test_detail_panel_guides_slow_query_with_actionable_next_step(client):
    entry = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_QUERY,
        duration_ms=1250.0,
        payload={"sql": "SELECT 1", "is_slow": True},
    )

    html = client.get(reverse("orbit:detail", args=[entry.id])).content.decode()

    assert "A SQL query took 1250.0 ms." in html
    assert "Explain Plan" in html
    assert "No problem signal was inferred" not in html


@pytest.mark.django_db
def test_detail_panel_guides_log_by_level_without_exposing_message(client):
    entry = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_LOG,
        payload={"level": "INFO", "message": "secret-token"},
    )

    html = client.get(reverse("orbit:detail", args=[entry.id])).content.decode()

    assert "A INFO log event was recorded." in html
    assert "No warning or error level was recorded" in html
    assert "secret-token" not in html


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
