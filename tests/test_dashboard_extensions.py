import pytest

pytestmark = pytest.mark.django_db

from orbit.dashboard_extensions import (
    clear_dashboard_extensions,
    list_dashboard_extensions,
    register_dashboard_extension,
)


@pytest.fixture(autouse=True)
def reset_extensions():
    clear_dashboard_extensions()
    yield
    clear_dashboard_extensions()


def test_registers_a_valid_local_dashboard_link():
    register_dashboard_extension("pro", "Orbit Pro", "/orbit/pro/")
    assert list_dashboard_extensions() == (
        {"key": "pro", "label": "Orbit Pro", "url": "/orbit/pro/"},
    )


def test_rejects_external_or_unsafe_links():
    with pytest.raises(ValueError):
        register_dashboard_extension("pro", "Orbit Pro", "https://example.com")
    with pytest.raises(ValueError):
        register_dashboard_extension("pro", "Orbit Pro", "/orbit/pro/?next=x")


def test_duplicate_key_replaces_its_own_extension_deterministically():
    register_dashboard_extension("pro", "Orbit Pro", "/orbit/pro/")
    register_dashboard_extension("pro", "Release Guard", "/orbit/release-guard/")
    assert list_dashboard_extensions() == (
        {"key": "pro", "label": "Release Guard", "url": "/orbit/release-guard/"},
    )
