"""Feed limits and filter state survive every pagination control."""

from html.parser import HTMLParser
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.test import RequestFactory
from django.urls import reverse

import pytest

from orbit.models import OrbitEntry
from orbit.views import OrbitFeedPartial

pytestmark = pytest.mark.django_db


class PaginationLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name == "hx-get" and urlsplit(value).path == reverse("orbit:feed"):
                self.urls.append(value)


def pagination_links(response):
    parser = PaginationLinks()
    parser.feed(response.content.decode())
    return parser.urls


@pytest.mark.parametrize("entry_type", ["log", "exception"])
@pytest.mark.parametrize(
    "params, expected_page, expected_size",
    [
        ({}, 1, 25),
        ({"page": "oops", "per_page": "oops"}, 1, 25),
        ({"page": "", "per_page": ""}, 1, 25),
        ({"page": "1.5", "per_page": "1.5"}, 1, 25),
        ({"page": "NaN", "per_page": "Infinity"}, 1, 25),
        ({"page": "0", "per_page": "0"}, 1, 1),
        ({"page": "-3", "per_page": "-10"}, 1, 1),
        ({"page": "9" * 5000, "per_page": "9" * 5000}, 1, 25),
        ({"page": "99999999999999999999", "per_page": "9999999999"}, 1, 100),
        ({"page": "1", "per_page": "100"}, 1, 100),
    ],
)
def test_feed_normalizes_limits(
    client, entry_type, params, expected_page, expected_size
):
    response = client.get(reverse("orbit:feed"), {**params, "type": entry_type})
    assert response.status_code == 200
    assert response.context_data["page"] == expected_page
    assert response.context_data["per_page"] == expected_size


def test_malformed_limits_normalized_before_database_path():
    request = RequestFactory().get(
        reverse("orbit:feed"),
        {"type": "exception", "page": "bad", "per_page": "0"},
    )
    with patch.object(OrbitEntry.objects, "all") as all_entries:
        with patch.object(OrbitFeedPartial, "_exception_groups_response") as grouped:
            OrbitFeedPartial().get(request)
    grouped.assert_called_once_with(request, 1, 1)
    all_entries.assert_not_called()


@pytest.mark.parametrize("entry_type", ["", "unknown", "LOG", "log&page=2"])
def test_unknown_type_normalizes_to_all(client, entry_type):
    entry = OrbitEntry.objects.create(type="log", payload={"message": "visible"})
    response = client.get(reverse("orbit:feed"), {"type": entry_type})
    assert response.context_data["current_type"] == "all"
    assert entry in list(response.context_data["entries"])


@pytest.mark.parametrize("page", [1, 3, 5])
@pytest.mark.parametrize("entry_type", ["log", "exception"])
def test_all_pagination_urls_preserve_filters(client, page, entry_type):
    query = "needle & + / ? < >"
    tag = 'team & + / ? " caf\u00e9'
    family = "family & + / ?"
    entries = [
        OrbitEntry.objects.create(
            type=entry_type,
            family_hash=family,
            tags=f",{tag},",
            payload={"message": query},
        )
        for _ in range(5)
    ]
    OrbitEntry.objects.create(type=entry_type, payload={"message": "unrelated"})
    filters = {"type": entry_type, "q": query, "tag": tag, "family": family}
    response = client.get(
        reverse("orbit:feed"), {**filters, "per_page": 1, "page": page}
    )
    assert response.context_data["total_count"] == 5
    links = pagination_links(response)
    assert links
    for url in links:
        params = parse_qs(urlsplit(url).query)
        assert params == {
            **{key: [value] for key, value in filters.items()},
            "per_page": ["1"],
            "page": params["page"],
        }
        following = client.get(url)
        assert following.context_data["total_count"] == 5
        assert list(following.context_data["entries"])[0] in entries


@pytest.mark.parametrize("page", [1, 3, 5])
def test_grouped_exception_pagination_preserves_state(client, page):
    for index in range(5):
        OrbitEntry.objects.create(
            type="exception", fingerprint=f"fp-{index}", payload={}
        )
    response = client.get(
        reverse("orbit:feed"), {"type": "exception", "per_page": 1, "page": page}
    )
    assert response.context_data["total_count"] == 5
    links = pagination_links(response)
    assert links
    for url in links:
        params = parse_qs(urlsplit(url).query)
        assert params["type"] == ["exception"]
        assert params["per_page"] == ["1"]
        following = client.get(url)
        assert following.context_data["total_count"] == 5
        assert len(following.context_data["groups"]) == 1


def test_tag_search_prefix_survives_pagination(client):
    for _ in range(3):
        OrbitEntry.objects.create(type="log", tags=",team & ops,", payload={})
    response = client.get(reverse("orbit:feed"), {"q": "tag:team & ops", "per_page": 1})
    links = pagination_links(response)
    assert links
    for url in links:
        assert parse_qs(urlsplit(url).query)["q"] == ["tag:team & ops"]
        assert client.get(url).context_data["total_count"] == 3
