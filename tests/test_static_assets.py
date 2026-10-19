"""
The dashboard must be self-contained: every script, stylesheet and font is
served from Orbit's own package static files (no CDN, nothing unpinned).
"""

import re
from pathlib import Path

from django.contrib.staticfiles import finders
from django.urls import reverse

import pytest

pytestmark = pytest.mark.django_db

PAGES = ["orbit:dashboard", "orbit:stats", "orbit:health"]
EXTERNAL = re.compile(r"""<(?:script|link)\b[^>]*\b(?:src|href)=["'](?:https?:)?//""")
STATIC_REF = re.compile(r"""(?:src|href)=["']/static/(orbit/[^"']+)["']""")


@pytest.mark.parametrize("name", PAGES)
def test_pages_load_no_external_assets(client, name):
    html = client.get(reverse(name)).content.decode()
    assert not EXTERNAL.search(html)
    for host in ("cdn.tailwindcss.com", "unpkg.com", "jsdelivr", "googleapis"):
        assert host not in html


@pytest.mark.parametrize("name", PAGES)
def test_referenced_static_assets_exist(client, name):
    html = client.get(reverse(name)).content.decode()
    refs = STATIC_REF.findall(html)
    assert "orbit/css/orbit.css" in refs
    assert "orbit/vendor/htmx.min.js" in refs
    for ref in refs:
        assert finders.find(ref), f"{ref} is referenced but not shipped"


def test_stats_page_uses_vendored_apexcharts(client):
    html = client.get(reverse("orbit:stats")).content.decode()
    assert "orbit/vendor/apexcharts.min.js" in html


def test_stylesheet_references_shipped_fonts():
    css_path = Path(finders.find("orbit/css/orbit.css"))
    for font in re.findall(r"url\(\.\./(fonts/[^)]+)\)", css_path.read_text()):
        assert (css_path.parent.parent / font).is_file()


def test_vendor_licenses_document_every_vendored_file():
    vendor = Path(finders.find("orbit/vendor/LICENSES.md")).parent
    licenses = (vendor / "LICENSES.md").read_text()
    for asset in vendor.glob("*.js"):
        assert f"vendor/{asset.name}" in licenses
