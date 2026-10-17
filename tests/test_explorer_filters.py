import uuid
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.db import connection
from django.db.models import F
from django.urls import reverse
from django.utils import timezone

import pytest

from orbit.explorer import ExplorerFilters, _JSONPathIsString
from orbit.models import OrbitEntry

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "params, expected",
    [
        ({}, {"type": "all", "range": "all", "min_duration_ms": ""}),
        (
            {"method": "post", "min_duration_ms": "0"},
            {"method": "POST", "min_duration_ms": "0"},
        ),
        ({"type": "not-a-type"}, {"type": "all"}),
        ({"range": ""}, {"range": "all"}),
        ({"method": " post "}, {"method": "POST"}),
        ({"q": ["first", "last"]}, {"q": "last"}),
    ],
)
def test_filters_normalize_canonical_values(params, expected):
    filters, errors = ExplorerFilters.parse(params)
    assert not errors
    for key, value in expected.items():
        assert filters.canonical[key] == value


@pytest.mark.parametrize(
    "params, field",
    [
        ({"range": "nonsense"}, "range"),
        ({"method": "BREW"}, "method"),
        ({"status_class": "200"}, "status_class"),
        ({"min_duration_ms": "1e2"}, "min_duration_ms"),
        ({"min_duration_ms": "9" * 100}, "min_duration_ms"),
        ({"range": ["15m", "1h"]}, "range"),
        ({"path": ["one", "two"]}, "path"),
        ({"status_class": ["4xx", "5xx"]}, "status_class"),
        ({"min_duration_ms": ["1", "2"]}, "min_duration_ms"),
    ],
)
def test_invalid_and_repeated_filters_are_fielded(params, field):
    _, errors = ExplorerFilters.parse(params)
    assert field in errors
    assert "invalid_filters" not in str(errors)


def test_filters_apply_as_and_scope_with_request_exception_path_fields(client):
    matching = OrbitEntry.objects.create(
        type="request",
        duration_ms=0,
        payload={"path": "/api/orders/", "method": "POST", "status_code": 201},
    )
    OrbitEntry.objects.create(
        type="request",
        duration_ms=None,
        payload={"path": "/api/orders/", "method": "POST", "status_code": 201},
    )
    error = OrbitEntry.objects.create(
        type="exception",
        payload={"request_path": "/api/orders/", "request_method": "POST"},
    )
    response = client.get(
        reverse("orbit:feed"),
        {
            "type": "all",
            "path": "orders",
            "method": "post",
            "status_class": "2xx",
            "min_duration_ms": "0",
            "per_page": "1",
        },
    )
    assert response.status_code == 200
    assert response.context_data["total_entries"] == 1
    assert list(response.context_data["entries"]) == [matching]
    assert error not in response.context_data["entries"]


def test_request_path_filter_matches_exceptions_without_family_expansion(client):
    exception = OrbitEntry.objects.create(
        type="exception", family_hash="same", payload={"request_path": "/private/"}
    )
    unrelated = OrbitEntry.objects.create(
        type="log", family_hash="same", payload={"message": "not a request path"}
    )
    response = client.get(reverse("orbit:feed"), {"path": "private"})
    assert list(response.context_data["entries"]) == [exception]
    assert unrelated not in response.context_data["entries"]


def test_grouping_uses_only_scoped_occurrences_and_latest_tiebreaker(client):
    OrbitEntry.objects.create(
        type="exception", fingerprint="group", payload={"message": "outside"}
    )
    first = OrbitEntry.objects.create(
        id=uuid.UUID(int=1),
        type="exception",
        fingerprint="group",
        payload={"request_path": "/target/", "message": "first"},
    )
    second = OrbitEntry.objects.create(
        id=uuid.UUID(int=2),
        type="exception",
        fingerprint="group",
        payload={"request_path": "/target/", "message": "second"},
    )
    response = client.get(
        reverse("orbit:feed"), {"type": "exception", "path": "target"}
    )
    assert response.context_data["groups"][0]["entry"] == second
    assert response.context_data["groups"][0]["count"] == 2
    assert first.id != second.id


def test_relative_range_includes_both_boundaries(client):
    now = timezone.now()
    start = now - timedelta(minutes=15)
    lower = OrbitEntry.objects.create(type="log", payload={})
    upper = OrbitEntry.objects.create(type="log", payload={})
    outside = OrbitEntry.objects.create(type="log", payload={})
    OrbitEntry.objects.filter(id=lower.id).update(created_at=start)
    OrbitEntry.objects.filter(id=upper.id).update(created_at=now)
    OrbitEntry.objects.filter(id=outside.id).update(
        created_at=start - timedelta(seconds=1)
    )
    with patch("orbit.views.timezone.now", return_value=now):
        response = client.get(reverse("orbit:feed"), {"range": "15m"})
    assert response.status_code == 200
    assert response.context_data["total_entries"] == 2


def test_status_filter_excludes_malformed_json_status_values(client):
    valid = OrbitEntry.objects.create(
        type="request", payload={"path": "/x/", "status_code": 500}
    )
    for malformed in ("500", True, None, {"value": 500}, [500]):
        OrbitEntry.objects.create(
            type="request", payload={"path": "/x/", "status_code": malformed}
        )
    response = client.get(reverse("orbit:feed"), {"status_class": "5xx"})
    assert response.status_code == 200
    assert list(response.context_data["entries"]) == [valid]


def test_group_page_limits_representative_lookups(client, django_assert_num_queries):
    for index in range(12):
        OrbitEntry.objects.create(
            type="exception", fingerprint=f"group-{index}", payload={}
        )
    with django_assert_num_queries(5):
        response = client.get(
            reverse("orbit:feed"), {"type": "exception", "per_page": 1}
        )
    assert response.status_code == 200
    assert response.context_data["total_count"] == 12
    assert len(response.context_data["groups"]) == 1


@pytest.mark.parametrize(
    "entry_type, path_key", [("request", "path"), ("exception", "request_path")]
)
def test_path_filter_only_matches_string_json_values(client, entry_type, path_key):
    matching = OrbitEntry.objects.create(
        type=entry_type, payload={path_key: "/needle/%_literal"}
    )
    for value in ({"nested": "needle"}, ["needle"], 123, True, None):
        OrbitEntry.objects.create(type=entry_type, payload={path_key: value})
    OrbitEntry.objects.create(type=entry_type, payload={})

    response = client.get(reverse("orbit:feed"), {"type": entry_type, "path": "needle"})
    if entry_type == "request":
        assert list(response.context_data["entries"]) == [matching]
    else:
        assert [group["entry"] for group in response.context_data["groups"]] == [
            matching
        ]
    unfiltered = client.get(reverse("orbit:feed"), {"type": entry_type})
    assert unfiltered.context_data["total_entries"] == 7


@pytest.mark.parametrize(
    "vendor, expected_sql, expected_key",
    [
        ("sqlite", "JSON_TYPE", "$.path"),
        ("postgresql", "jsonb_typeof", "path"),
        ("mysql", "JSON_TYPE", "$.path"),
    ],
)
def test_json_path_string_expression_compiles_for_supported_vendors(
    vendor, expected_sql, expected_key
):
    from django.db.models.sql.compiler import SQLCompiler

    query = OrbitEntry.objects.all().query
    expression = _JSONPathIsString(F("payload"), "path").resolve_expression(query)
    proxy = SimpleNamespace(vendor=vendor, ops=connection.ops, alias=connection.alias)
    sql, params = SQLCompiler(query, proxy, connection.alias).compile(expression)
    assert expected_sql in sql
    assert expected_key in params
    assert "path" not in sql


def test_json_path_string_expression_rejects_unapproved_keys():
    with pytest.raises(ValueError):
        _JSONPathIsString(F("payload"), "payload__path")


@pytest.mark.parametrize("vendor", ["sqlite", "postgresql", "mysql"])
@pytest.mark.parametrize("params", [[], ()])
def test_json_path_expression_accepts_list_and_tuple_compiler_params(vendor, params):
    compiler = SimpleNamespace(compile=lambda expression: ('"payload"', params))
    expression = _JSONPathIsString(F("payload"), "path")
    sql, bound = expression.as_sql(compiler, SimpleNamespace(vendor=vendor))
    assert "%s" in sql
    assert len(bound) == 1


def test_path_filter_treats_percent_and_underscore_as_literal(client):
    matching = OrbitEntry.objects.create(
        type="request", payload={"path": "/literal/%_segment/"}
    )
    OrbitEntry.objects.create(type="request", payload={"path": "/literal/xysegment/"})
    response = client.get(reverse("orbit:feed"), {"path": "%_"})
    assert list(response.context_data["entries"]) == [matching]


def test_json_path_string_expression_fails_closed_for_unknown_vendor():
    from django.db.models.sql.compiler import SQLCompiler

    query = OrbitEntry.objects.all().query
    expression = _JSONPathIsString(F("payload"), "path").resolve_expression(query)
    proxy = SimpleNamespace(
        vendor="unknown", ops=connection.ops, alias=connection.alias
    )
    sql, params = SQLCompiler(query, proxy, connection.alias).compile(expression)
    assert sql == "1=0"
    assert params == []
