"""
CSP nonce support: Orbit renders ``nonce="..."`` on its script/style tags when
the host runs Django 6's built-in CSP middleware or django-csp, and renders
nothing otherwise (including on Django 5.2, which has no CSP support).
"""

import re
import sys

import django
from django.conf import settings
from django.template import Context, RequestContext, Template
from django.test import RequestFactory, override_settings
from django.urls import reverse

import pytest

pytestmark = pytest.mark.django_db

PAGES = ["orbit:dashboard", "orbit:stats", "orbit:health"]
TAG = re.compile(r"<(?:script|link)\b[^>]*>", re.I)


class FakeDjangoCspMiddleware:
    """Mimics django-csp, which sets ``request.csp_nonce``."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.csp_nonce = "fake-django-csp-nonce"
        return self.get_response(request)


def _render(template, context):
    return Template("{% load orbit_tags %}" + template).render(context)


def _asset_tags(html):
    return [
        tag
        for tag in TAG.findall(html)
        if "/static/orbit/" in tag and "application/json" not in tag
    ]


@pytest.mark.parametrize("name", PAGES)
def test_pages_render_no_nonce_without_csp(client, name):
    html = client.get(reverse(name)).content.decode()
    assert "nonce" not in html
    assert _asset_tags(html)


@pytest.mark.parametrize("name", PAGES)
def test_pages_render_nonce_from_django_csp_style_attribute(client, name):
    middleware = list(settings.MIDDLEWARE)
    with override_settings(
        MIDDLEWARE=["tests.test_csp_nonce.FakeDjangoCspMiddleware", *middleware]
    ):
        html = client.get(reverse(name)).content.decode()
    tags = _asset_tags(html)
    assert tags
    for tag in tags:
        assert 'nonce="fake-django-csp-nonce"' in tag


@pytest.mark.skipif(django.VERSION < (6, 0), reason="Django built-in CSP is 6.0+")
@pytest.mark.parametrize("name", PAGES)
def test_pages_use_django_builtin_csp_nonce(client, name):
    from django.utils.csp import CSP

    middleware = list(settings.MIDDLEWARE)
    with override_settings(
        MIDDLEWARE=[
            "django.middleware.csp.ContentSecurityPolicyMiddleware",
            *middleware,
        ],
        SECURE_CSP={
            "default-src": [CSP.SELF],
            "script-src": [CSP.SELF, CSP.NONCE, CSP.UNSAFE_EVAL],
            "style-src": [CSP.SELF, CSP.NONCE],
        },
    ):
        response = client.get(reverse(name))
    html = response.content.decode()
    header = response["Content-Security-Policy"]
    nonce = re.search(r"'nonce-([^']+)'", header).group(1)
    tags = _asset_tags(html)
    assert tags
    for tag in tags:
        assert f'nonce="{nonce}"' in tag


@pytest.mark.skipif(django.VERSION < (6, 0), reason="Django built-in CSP is 6.0+")
def test_django_builtin_csp_header_is_unchanged_without_a_nonce_policy(client):
    from django.utils.csp import CSP

    middleware = list(settings.MIDDLEWARE)
    with override_settings(
        MIDDLEWARE=[
            "django.middleware.csp.ContentSecurityPolicyMiddleware",
            *middleware,
        ],
        SECURE_CSP={"default-src": [CSP.SELF]},
    ):
        response = client.get(reverse("orbit:dashboard"))
    # Orbit evaluated the nonce, but a policy without the sentinel is untouched.
    assert response["Content-Security-Policy"] == "default-src 'self'"


def test_tag_prefers_request_then_context_variable():
    request = RequestFactory().get("/")
    assert _render("[{% orbit_nonce %}]", RequestContext(request)) == "[]"

    request.csp_nonce = "from-request"
    context = RequestContext(request, {"csp_nonce": "from-context"})
    assert _render("{% orbit_nonce %}", context) == "from-request"

    assert _render("{% orbit_nonce %}", Context({"csp_nonce": "ctx"})) == "ctx"


def test_attr_tag_renders_escaped_attribute_or_nothing():
    assert _render("<s {% orbit_nonce_attr %}>", Context()) == "<s >"
    out = _render("<s {% orbit_nonce_attr %}>", Context({"csp_nonce": 'a"b<c'}))
    assert out == '<s nonce="a&quot;b&lt;c">'


def test_tag_works_without_django_csp_module(monkeypatch):
    """Django 5.2 has no django.middleware.csp: the import must not break."""
    monkeypatch.setitem(sys.modules, "django.middleware.csp", None)
    request = RequestFactory().get("/")
    assert _render("{% orbit_nonce_attr %}", RequestContext(request)) == ""
    request.csp_nonce = "n1"
    assert _render("{% orbit_nonce %}", RequestContext(request)) == "n1"


def test_tag_never_raises_on_broken_request():
    class Broken:
        @property
        def csp_nonce(self):
            raise RuntimeError("boom")

    context = Context({"request": Broken()})
    assert _render("{% orbit_nonce %}", context) == ""


def test_pages_disable_htmx_eval_and_inline_styles(client):
    html = client.get(reverse("orbit:dashboard")).content.decode()
    meta = re.search(r"<meta name=\"htmx-config\" content='([^']+)'", html).group(1)
    assert '"allowEval": false' in meta
    assert '"includeIndicatorStyles": false' in meta


def test_stats_page_preloads_apexcharts_css_to_avoid_inline_style(client):
    html = client.get(reverse("orbit:stats")).content.decode()
    assert re.search(r'<link[^>]*id="apexcharts-css"[^>]*apexcharts\.css', html)
