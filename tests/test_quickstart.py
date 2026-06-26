import pytest
from orbit.cli import main as orbit_main
from orbit.demo_project import create_demo_project
from orbit.quickstart import (
    QuickstartOptions,
    build_install_plan,
    normalize_url_prefix,
    patch_settings_text,
    patch_urls_text,
    run_quickstart,
)

pytestmark = pytest.mark.django_db


def test_build_install_plan_defaults_to_safe_dry_run():
    plan = build_install_plan(QuickstartOptions())

    assert "pip install django-orbit" in plan
    assert "orbit quick --settings" in plan
    assert "python manage.py migrate orbit" in plan
    assert "http://localhost:8000/orbit/" in plan
    assert "dry-run" in plan


def test_build_install_plan_supports_mcp_extra_and_custom_prefix():
    plan = build_install_plan(
        QuickstartOptions(with_mcp=True, url_prefix="debug/orbit/")
    )

    assert "pip install django-orbit[mcp]" in plan
    assert 'path("debug/orbit/", include("orbit.urls"))' in plan
    assert "http://localhost:8000/debug/orbit/" in plan


def test_normalize_url_prefix_rejects_empty_prefix():
    assert normalize_url_prefix("/debug/orbit") == "debug/orbit/"
    assert normalize_url_prefix("orbit") == "orbit/"
    with pytest.raises(ValueError):
        normalize_url_prefix("/")


def test_patch_settings_text_adds_orbit_idempotently():
    settings = """
INSTALLED_APPS = [
    "django.contrib.admin",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
]
"""

    patched, changes = patch_settings_text(settings)
    repatched, second_changes = patch_settings_text(patched)

    assert '"orbit",' in patched
    assert patched.index('"orbit.middleware.OrbitMiddleware",') < patched.index(
        '"django.middleware.security.SecurityMiddleware",'
    )
    assert changes == [
        "added orbit to INSTALLED_APPS",
        "added OrbitMiddleware to MIDDLEWARE",
    ]
    assert repatched == patched
    assert second_changes == []


def test_patch_urls_text_adds_include_import_and_custom_prefix():
    urls = """
from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
]
"""

    patched, changes = patch_urls_text(urls, url_prefix="debug/orbit/")
    repatched, second_changes = patch_urls_text(patched, url_prefix="debug/orbit/")

    assert "from django.urls import include, path" in patched
    assert 'path("debug/orbit/", include("orbit.urls")),' in patched
    assert changes == [
        "added include import to urls.py",
        "mounted Orbit URLs at debug/orbit/",
    ]
    assert repatched == patched
    assert second_changes == []


def test_run_quickstart_dry_run_does_not_modify_files(tmp_path, capsys):
    settings_path = tmp_path / "settings.py"
    urls_path = tmp_path / "urls.py"
    original_settings = "INSTALLED_APPS = []\nMIDDLEWARE = []\n"
    original_urls = "from django.urls import path\nurlpatterns = []\n"
    settings_path.write_text(original_settings, encoding="utf-8")
    urls_path.write_text(original_urls, encoding="utf-8")

    exit_code = run_quickstart(
        ["--settings", str(settings_path), "--urls", str(urls_path)]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Dry run" in output
    assert "added orbit to INSTALLED_APPS" in output
    assert settings_path.read_text(encoding="utf-8") == original_settings
    assert urls_path.read_text(encoding="utf-8") == original_urls


def test_run_quickstart_print_diff_shows_unified_diff(tmp_path, capsys):
    settings_path = tmp_path / "settings.py"
    urls_path = tmp_path / "urls.py"
    settings_path.write_text("INSTALLED_APPS = []\nMIDDLEWARE = []\n", encoding="utf-8")
    urls_path.write_text(
        "from django.urls import path\nurlpatterns = []\n", encoding="utf-8"
    )

    exit_code = run_quickstart(
        [
            "--settings",
            str(settings_path),
            "--urls",
            str(urls_path),
            "--print-diff",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert f"--- {settings_path}" in output
    assert '+    "orbit",' in output
    assert '+    path("orbit/", include("orbit.urls")),' in output


def test_run_quickstart_check_fails_when_changes_are_needed(tmp_path, capsys):
    settings_path = tmp_path / "settings.py"
    urls_path = tmp_path / "urls.py"
    settings_path.write_text("INSTALLED_APPS = []\nMIDDLEWARE = []\n", encoding="utf-8")
    urls_path.write_text(
        "from django.urls import path\nurlpatterns = []\n", encoding="utf-8"
    )

    exit_code = run_quickstart(
        ["--settings", str(settings_path), "--urls", str(urls_path), "--check"]
    )

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "Check failed" in output
    assert "added orbit to INSTALLED_APPS" in output


def test_run_quickstart_check_passes_when_configured(tmp_path, capsys):
    settings_path = tmp_path / "settings.py"
    urls_path = tmp_path / "urls.py"
    settings_path.write_text(
        'INSTALLED_APPS = [\n    "orbit",\n]\nMIDDLEWARE = [\n    "orbit.middleware.OrbitMiddleware",\n]\n',
        encoding="utf-8",
    )
    urls_path.write_text(
        'from django.urls import include, path\nurlpatterns = [\n    path("orbit/", include("orbit.urls")),\n]\n',
        encoding="utf-8",
    )

    exit_code = run_quickstart(
        ["--settings", str(settings_path), "--urls", str(urls_path), "--check"]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Check passed" in output


def test_run_quickstart_write_updates_files(tmp_path):
    settings_path = tmp_path / "settings.py"
    urls_path = tmp_path / "urls.py"
    settings_path.write_text("INSTALLED_APPS = []\nMIDDLEWARE = []\n", encoding="utf-8")
    urls_path.write_text(
        "from django.urls import path\nurlpatterns = []\n", encoding="utf-8"
    )

    exit_code = run_quickstart(
        [
            "--settings",
            str(settings_path),
            "--urls",
            str(urls_path),
            "--url-prefix",
            "debug/orbit",
            "--write",
        ]
    )

    assert exit_code == 0
    assert '"orbit"' in settings_path.read_text(encoding="utf-8")
    assert 'path("debug/orbit/", include("orbit.urls"))' in urls_path.read_text(
        encoding="utf-8"
    )


def test_orbit_cli_quick_alias_delegates_to_quickstart(tmp_path, capsys):
    settings_path = tmp_path / "settings.py"
    urls_path = tmp_path / "urls.py"
    settings_path.write_text("INSTALLED_APPS = []\nMIDDLEWARE = []\n", encoding="utf-8")
    urls_path.write_text(
        "from django.urls import path\nurlpatterns = []\n", encoding="utf-8"
    )

    exit_code = orbit_main(
        ["quick", "--settings", str(settings_path), "--urls", str(urls_path), "--check"]
    )

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "Check failed" in output


def test_create_demo_project_scaffolds_web_and_mcp_instructions(tmp_path):
    target = tmp_path / "orbit-demo"

    result = create_demo_project(target, with_mcp=True)

    assert result.target == target
    assert (target / "manage.py").exists()
    assert (target / "orbit_demo" / "settings.py").exists()
    assert (target / "orbit_demo" / "urls.py").exists()
    assert (target / "orbit_demo" / "views.py").exists()
    readme = (target / "README.md").read_text(encoding="utf-8")
    urls = (target / "orbit_demo" / "urls.py").read_text(encoding="utf-8")
    assert "python manage.py runserver" in readme
    assert "python manage.py orbit_mcp" in readme
    assert 'path("orbit/", include("orbit.urls"))' in urls


def test_orbit_cli_demo_creates_demo_project(tmp_path, capsys):
    target = tmp_path / "demo-app"

    exit_code = orbit_main(["demo", "--target", str(target), "--with-mcp"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Created Django Orbit demo project" in output
    assert (target / "manage.py").exists()
    assert "python manage.py orbit_mcp" in output
