"""
Tests for M4 (C1) — the AI assist layer. A fake handler is injected via config so no
network call or API key is needed.
"""

import pytest
from django.urls import reverse

from orbit import ai as ai_mod
from orbit.models import OrbitEntry

pytestmark = pytest.mark.django_db


def _ai_config(captured):
    """Return an ORBIT_CONFIG AI block whose handler records the prompt it received."""
    def handler(system, user, cfg):
        captured["system"] = system
        captured["user"] = user
        return "Root cause: X.\n\nFix: do Y."

    return {"enabled": True, "api_key": "test", "handler": handler, "model": "test-model"}


def test_ai_disabled_by_default():
    assert ai_mod.ai_enabled() is False


def test_analyze_entry_disabled_returns_error():
    e = OrbitEntry.objects.create(type=OrbitEntry.TYPE_EXCEPTION, payload={"exception_type": "X"})
    out = ai_mod.analyze_entry(e)
    assert out["ok"] is False
    assert "disabled" in out["error"].lower()


def test_analyze_entry_uses_handler_and_caches(settings):
    captured = {}
    settings.ORBIT_CONFIG = {**getattr(settings, "ORBIT_CONFIG", {}), "AI": _ai_config(captured)}
    e = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_EXCEPTION,
        payload={"exception_type": "ValueError", "message": "bad", "traceback": []},
    )
    out = ai_mod.analyze_entry(e)
    assert out["ok"] is True and out["cached"] is False
    assert "Fix:" in out["text"]
    assert "ValueError" in captured["user"]  # prompt built from the entry

    # Cached on the entry: second call doesn't re-run the handler
    captured.clear()
    out2 = ai_mod.analyze_entry(OrbitEntry.objects.get(id=e.id))
    assert out2["cached"] is True
    assert captured == {}


def test_analyze_entry_masks_sensitive_data(settings):
    captured = {}
    settings.ORBIT_CONFIG = {**getattr(settings, "ORBIT_CONFIG", {}), "AI": _ai_config(captured)}
    e = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_DUMP,
        payload={"password": "supersecret", "note": "ok"},
    )
    ai_mod.analyze_entry(e)
    assert "supersecret" not in captured["user"]  # masked before sending
    assert "***HIDDEN***" in captured["user"]


def test_entry_supports_ai():
    exc = OrbitEntry.objects.create(type=OrbitEntry.TYPE_EXCEPTION, payload={})
    slow = OrbitEntry.objects.create(type=OrbitEntry.TYPE_QUERY, payload={"is_slow": True})
    normal_q = OrbitEntry.objects.create(type=OrbitEntry.TYPE_QUERY, payload={"is_slow": False})
    assert ai_mod.entry_supports_ai(exc) is True
    assert ai_mod.entry_supports_ai(slow) is True
    assert ai_mod.entry_supports_ai(normal_q) is False


def test_ai_explain_view_disabled(client):
    e = OrbitEntry.objects.create(type=OrbitEntry.TYPE_EXCEPTION, payload={})
    html = client.get(reverse("orbit:ai_explain", args=[e.id])).content.decode()
    assert "off" in html.lower() or "disabled" in html.lower()


def test_ai_explain_view_enabled(client, settings):
    captured = {}
    settings.ORBIT_CONFIG = {**getattr(settings, "ORBIT_CONFIG", {}), "AI": _ai_config(captured)}
    e = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_EXCEPTION,
        payload={"exception_type": "KeyError", "message": "x", "traceback": []},
    )
    html = client.get(reverse("orbit:ai_explain", args=[e.id])).content.decode()
    assert "AI analysis" in html
    assert "Fix:" in html


# ---- M5: summary (C3) / triage (C4) / NL search (C2) ----------------------

def test_summarize_family(settings):
    captured = {}
    settings.ORBIT_CONFIG = {**getattr(settings, "ORBIT_CONFIG", {}), "AI": _ai_config(captured)}
    req = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST, family_hash="ff", duration_ms=100,
        payload={"method": "GET", "path": "/x/", "status_code": 200},
    )
    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_QUERY, family_hash="ff", duration_ms=80,
        payload={"sql": "SELECT * FROM big"},
    )
    out = ai_mod.summarize_family(req)
    assert out["ok"] is True
    assert "Child events by type" in captured["user"]
    assert "SELECT * FROM big"[:20] in captured["user"]


def test_triage_exception(settings):
    captured = {}
    settings.ORBIT_CONFIG = {**getattr(settings, "ORBIT_CONFIG", {}), "AI": _ai_config(captured)}
    e = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_EXCEPTION, payload={"exception_type": "ValueError", "message": "x", "traceback": []},
    )
    out = ai_mod.triage_exception(e)
    assert out["ok"] is True
    assert "triag" in captured["system"].lower()


def test_summary_and_explain_cached_separately(settings):
    settings.ORBIT_CONFIG = {**getattr(settings, "ORBIT_CONFIG", {}), "AI": _ai_config({})}
    req = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST, family_hash="gg", duration_ms=10,
        payload={"method": "GET", "path": "/y/", "status_code": 200},
    )
    ai_mod.analyze_entry(req)
    ai_mod.summarize_family(req)
    req.refresh_from_db()
    assert set(req.payload["ai"].keys()) == {"explain", "summary"}


def test_nl_search_parses_filters(settings):
    def handler(system, user, cfg):
        return 'Here you go: {"type": "request", "status_min": 500, "since_minutes": 60}'

    settings.ORBIT_CONFIG = {
        **getattr(settings, "ORBIT_CONFIG", {}),
        "AI": {"enabled": True, "api_key": "t", "handler": handler},
    }
    out = ai_mod.nl_search("show 500s in the last hour")
    assert out["ok"] is True
    assert out["filters"] == {"type": "request", "status_min": 500, "since_minutes": 60}


def test_nl_search_view(client, settings):
    def handler(system, user, cfg):
        return '{"type": "exception"}'

    settings.ORBIT_CONFIG = {
        **getattr(settings, "ORBIT_CONFIG", {}),
        "AI": {"enabled": True, "api_key": "t", "handler": handler},
    }
    import json as _json

    resp = client.get(reverse("orbit:ai_search"), {"q": "errors"})
    data = _json.loads(resp.content)
    assert data["ok"] is True and data["filters"]["type"] == "exception"


def test_feed_extra_filters(client):
    OrbitEntry.objects.create(type=OrbitEntry.TYPE_REQUEST, payload={"status_code": 500, "path": "/checkout/"})
    OrbitEntry.objects.create(type=OrbitEntry.TYPE_REQUEST, payload={"status_code": 200, "path": "/home/"})
    html = client.get(reverse("orbit:feed"), {"type": "request", "status_min": "500"}).content.decode()
    assert html.count('data-entry-id="') == 1
    html2 = client.get(reverse("orbit:feed"), {"type": "request", "path_contains": "checkout"}).content.decode()
    assert html2.count('data-entry-id="') == 1
