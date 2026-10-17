"""Integration checks for the shared Explorer response consumed by the UI."""

import json
from html.parser import HTMLParser

from django.urls import reverse

import pytest

from orbit.models import OrbitEntry

pytestmark = pytest.mark.django_db


class ExplorerResponse(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.feeds = 0
        self.metrics = 0
        self.reading_state = False
        self.state_text = ""
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.feeds += "data-orbit-feed" in attrs
        self.metrics += tag == "template" and "data-orbit-metrics" in attrs
        if tag == "script" and attrs.get("id") == "orbit-explorer-state":
            assert attrs.get("type") == "application/json"
            self.reading_state = True

    def handle_endtag(self, tag):
        if tag == "script":
            self.reading_state = False

    def handle_data(self, data):
        if self.reading_state:
            self.state_text += data

    @property
    def state(self):
        return json.loads(self.state_text)


def test_feed_and_metrics_share_one_wire_scope(client):
    OrbitEntry.objects.create(
        type="request",
        family_hash="wire-family",
        duration_ms=0,
        payload={"path": "/checkout/", "method": "POST", "status_code": 500},
    )
    for _ in range(2):
        OrbitEntry.objects.create(
            type="exception",
            family_hash="wire-family",
            fingerprint="wire-error",
            payload={"exception_type": "ValueError", "message": "synthetic"},
        )
    response = client.get(
        reverse("orbit:feed"), {"family": "wire-family", "per_page": 1}
    )
    assert response.status_code == 200
    parsed = ExplorerResponse(response.content.decode())
    assert (parsed.feeds, parsed.metrics) == (1, 1)
    assert parsed.state["total_entries"] == 3
    assert parsed.state["filters"]["family"] == "wire-family"
    assert parsed.state["grouped"] is False
    metrics = response.context_data["explorer_metrics"]
    assert metrics["request_count"] == 1
    assert metrics["failed_request_count"] == 1
    assert metrics["exception_count"] == 2
    assert metrics["avg_response_time"] == 0
    assert metrics["error_rate_pct"] == 100


def test_grouped_wire_distinguishes_occurrences_from_rows(client):
    for _ in range(2):
        OrbitEntry.objects.create(type="exception", fingerprint="one-group", payload={})
    response = client.get(reverse("orbit:feed"), {"type": "exception"})
    parsed = ExplorerResponse(response.content.decode())
    assert parsed.state["grouped"] is True
    assert parsed.state["total_count"] == 1
    assert parsed.state["total_entries"] == 2
    assert response.context_data["explorer_metrics"]["exception_count"] == 2


def test_invalid_new_filter_does_not_query_or_echo_input(
    client, django_assert_num_queries
):
    probe = "synthetic-private-invalid-range"
    with django_assert_num_queries(0):
        response = client.get(reverse("orbit:feed"), {"range": probe})
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_filters"
    assert "range" in response.json()["fields"]
    assert probe not in response.content.decode()


def test_filter_state_uses_inert_escaped_json(client):
    probe = '</script><script id="synthetic-injection">bad()</script>'
    response = client.get(reverse("orbit:feed"), {"q": probe})
    parsed = ExplorerResponse(response.content.decode())
    assert parsed.state["filters"]["q"] == probe
    assert '<script id="synthetic-injection">' not in response.content.decode()
