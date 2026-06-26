"""
Smoke tests for the v0.9.0 UX overhaul: grouped navigation, lazy Stats sections,
version sourcing, and the Export-button removal.
"""

import pytest
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
def test_request_detail_renders_hybrid_diagnosis_card(client):
    family = "ui-detail-diagnosis"
    request_entry = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        family_hash=family,
        payload={
            "method": "POST",
            "path": "/checkout/",
            "full_path": "/checkout/?step=pay",
            "status_code": 500,
            "query_count": 4,
            "duplicate_query_count": 2,
        },
        duration_ms=780,
    )
    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_EXCEPTION,
        family_hash=family,
        payload={"exception_type": "ValueError", "message": "payment token rejected"},
    )
    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_QUERY,
        family_hash=family,
        payload={
            "sql": "SELECT * FROM checkout_order WHERE user_id = %s",
            "is_duplicate": True,
            "duplicate_count": 2,
        },
        duration_ms=120,
    )

    response = client.get(reverse("orbit:detail", args=[request_entry.id]))

    assert response.status_code == 200
    insight = response.context_data["detail_insight"]
    assert insight["severity"] == "error"
    assert "POST /checkout/" in insight["plain_summary"]
    assert "500" in insight["technical_signal"]
    html = response.content.decode()
    assert "What this means" in html
    assert "Technical signal" in html
    assert "Next move" in html
    assert "Create an incident bundle" in html


@pytest.mark.django_db
def test_exception_detail_points_to_group_and_traceback(client):
    entry = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_EXCEPTION,
        fingerprint="fp-detail",
        payload={
            "exception_type": "KeyError",
            "message": "missing customer_id",
            "request_path": "/orders/",
            "traceback": [
                {
                    "filename": "orders/views.py",
                    "lineno": 42,
                    "name": "checkout",
                    "line": "customer_id = data['customer_id']",
                }
            ],
        },
    )

    response = client.get(reverse("orbit:detail", args=[entry.id]))

    insight = response.context_data["detail_insight"]
    assert insight["severity"] == "error"
    assert "KeyError" in insight["plain_summary"]
    assert "orders/views.py:42" in insight["technical_signal"]
    assert "fingerprint" in insight["next_move"]


@pytest.mark.django_db
def test_query_detail_explains_slow_duplicate_signal(client):
    entry = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_QUERY,
        payload={
            "sql": "SELECT * FROM demo_book WHERE author_id = %s",
            "is_slow": True,
            "is_duplicate": True,
            "duplicate_count": 6,
            "caller": {"filename": "books/views.py", "lineno": 88},
        },
        duration_ms=640,
    )

    response = client.get(reverse("orbit:detail", args=[entry.id]))

    insight = response.context_data["detail_insight"]
    assert insight["severity"] == "warning"
    assert "slow duplicated SQL query" in insight["plain_summary"]
    assert "books/views.py:88" in insight["technical_signal"]
    assert "Explain plan" in insight["next_move"]
