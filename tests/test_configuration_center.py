import pytest
from django.test import override_settings
from django.urls import reverse

from orbit.conf import get_config_diagnostics


@pytest.mark.django_db
@override_settings(ORBIT={"ENABLED": False}, ORBIT_CONFIG={"ENABLED": True})
def test_config_diagnostics_explain_alias_precedence_and_conflicts():
    diagnostics = get_config_diagnostics()

    assert diagnostics["source"] == "ORBIT_CONFIG"
    assert diagnostics["effective"]["ENABLED"] is True
    assert diagnostics["both_defined"] is True
    assert diagnostics["conflicting_keys"] == ["ENABLED"]


@pytest.mark.django_db
@override_settings(ORBIT_CONFIG={"PROJECT_NAME": "Checkout"})
def test_config_diagnostics_use_orbit_config_as_canonical_source():
    diagnostics = get_config_diagnostics()

    assert diagnostics["source"] == "ORBIT_CONFIG"
    assert diagnostics["effective"]["PROJECT_NAME"] == "Checkout"


@pytest.mark.django_db
def test_configuration_center_is_auth_gated_and_linked_from_dashboard(client):
    page = client.get(reverse("orbit:configuration"))
    dashboard = client.get(reverse("orbit:dashboard"))

    assert page.status_code == 200
    assert "Configuration" in page.content.decode()
    assert "RECORD_STORAGE" in page.content.decode()
    assert "MCP_ENABLED" in page.content.decode()
    assert reverse("orbit:configuration") in dashboard.content.decode()


@pytest.mark.django_db
def test_configuration_builder_returns_validated_snippet(client):
    response = client.post(
        reverse("orbit:configuration"),
        {
            "PROJECT_NAME": "Payments",
            "ENVIRONMENT": "staging",
            "RECORD_REQUESTS": "on",
            "RECORD_QUERIES": "on",
            "RECORD_LLM": "on",
            "LLM_CAPTURE_CONTENT": "on",
            "N_PLUS_ONE_MIN_OCCURRENCES": "6",
        },
    )
    html = response.content.decode()

    assert response.status_code == 200
    assert "ORBIT_CONFIG = {" in html
    assert "&#x27;PROJECT_NAME&#x27;: &#x27;Payments&#x27;" in html
    assert "&#x27;N_PLUS_ONE_MIN_OCCURRENCES&#x27;: 6" in html
    assert "This preview is not active" in html


@pytest.mark.django_db
def test_configuration_builder_rejects_invalid_threshold(client):
    response = client.post(
        reverse("orbit:configuration"),
        {"N_PLUS_ONE_MIN_OCCURRENCES": "0"},
    )

    assert response.status_code == 200
    assert "Use a value between 2 and 100." in response.content.decode()


@pytest.mark.django_db
@override_settings(ORBIT_CONFIG="invalid")
def test_invalid_configuration_type_falls_back_without_breaking_orbit():
    diagnostics = get_config_diagnostics()

    assert diagnostics["effective"]["ENABLED"] is True
    assert diagnostics["invalid_sources"] == ["ORBIT_CONFIG"]


@pytest.mark.django_db
@override_settings(ORBIT={"ENABLED": False}, ORBIT_CONFIG={"ENABLED": True})
def test_configuration_center_states_canonical_precedence(client):
    html = client.get(reverse("orbit:configuration")).content.decode()

    assert "ORBIT_CONFIG</code> is the canonical name and overrides matching keys" in html
    assert "ORBIT</code> remains a compatibility alias for other keys" in html


@pytest.mark.django_db
@override_settings(
    ORBIT={"AUTH_CHECK": "django.utils.html.escape", "ENABLED": False},
    ORBIT_CONFIG={"PROJECT_NAME": "Checkout", "ENABLED": True},
)
def test_config_diagnostics_merges_aliases_with_canonical_key_precedence():
    diagnostics = get_config_diagnostics()

    assert diagnostics["source"] == "ORBIT_CONFIG"
    assert diagnostics["effective"]["PROJECT_NAME"] == "Checkout"
    assert diagnostics["effective"]["ENABLED"] is True
    assert diagnostics["effective"]["AUTH_CHECK"] == "django.utils.html.escape"
