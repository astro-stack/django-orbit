import pytest

from orbit.query_analysis import (
    analyze_query_patterns,
    build_query_evidence,
    normalize_query_shape,
)

pytestmark = pytest.mark.django_db


def _query(
    sql,
    params,
    *,
    caller="/app/shop/views.py:42:list_products",
    database="default",
    duration_ms=2.0,
):
    evidence = build_query_evidence(
        sql=sql,
        params=params,
        database=database,
        caller_key=caller,
    )
    return {
        "sql": sql,
        "params": params,
        "database": database,
        "duration_ms": duration_ms,
        "caller_key": caller,
        **evidence,
    }


def test_normalize_query_shape_removes_dynamic_values():
    first = normalize_query_shape(
        "SELECT * FROM products WHERE category_id = 10 AND name = 'Desk'"
    )
    second = normalize_query_shape(
        " select *  from products where category_id = 22 and name = 'Chair' "
    )

    assert first == second
    assert "10" not in first
    assert "Desk" not in first


def test_query_evidence_is_versioned_and_does_not_expose_parameter_values():
    evidence = build_query_evidence(
        sql="SELECT * FROM users WHERE email = %s",
        params=["person@example.com"],
        database="default",
        caller_key="/app/users/views.py:8:list_users",
    )

    assert evidence["query_signature_version"] == 1
    assert evidence["operation"] == "SELECT"
    assert evidence["parameter_shape"] == ["str"]
    assert evidence["parameter_fingerprint"]
    assert "person@example.com" not in str(evidence)


def test_classifies_varying_relation_lookups_as_n_plus_one_candidate():
    queries = [
        _query(
            "SELECT * FROM authors WHERE id = %s",
            [author_id],
            duration_ms=3.0,
        )
        for author_id in range(1, 7)
    ]

    findings = analyze_query_patterns(queries, min_occurrences=4)

    assert len(findings) == 1
    finding = findings[0]
    assert finding["kind"] == "n_plus_one_candidate"
    assert finding["confidence"] == "high"
    assert finding["occurrences"] == 6
    assert finding["unique_parameter_sets"] == 6
    assert "varying_parameters" in finding["evidence"]
    assert "same_callsite" in finding["evidence"]


def test_classifies_per_row_aggregate_separately():
    queries = [
        _query(
            "SELECT COUNT(*) FROM order_items WHERE order_id = %s",
            [order_id],
        )
        for order_id in range(1, 5)
    ]

    findings = analyze_query_patterns(queries, min_occurrences=4)

    assert findings[0]["kind"] == "per_row_aggregate_candidate"
    assert findings[0]["aggregate"] == "COUNT"


def test_exact_repeats_are_not_called_n_plus_one():
    queries = [
        _query("SELECT * FROM settings WHERE name = %s", ["site_name"])
        for _ in range(5)
    ]

    findings = analyze_query_patterns(queries, min_occurrences=4)

    assert findings[0]["kind"] == "exact_duplicate"
    assert findings[0]["confidence"] == "medium"
    assert "identical_parameters" in findings[0]["counter_evidence"]


def test_repeated_writes_are_classified_as_write_loop():
    queries = [
        _query("UPDATE products SET viewed = %s WHERE id = %s", [True, item_id])
        for item_id in range(1, 5)
    ]

    findings = analyze_query_patterns(queries, min_occurrences=4)

    assert findings[0]["kind"] == "write_loop"
    assert findings[0]["confidence"] == "high"
    assert "write_operation" in findings[0]["counter_evidence"]


def test_same_shape_from_different_callsites_is_not_merged():
    queries = [
        _query(
            "SELECT * FROM users WHERE id = %s",
            [1],
            caller="/app/a.py:10:first",
        ),
        _query(
            "SELECT * FROM users WHERE id = %s",
            [2],
            caller="/app/a.py:10:first",
        ),
        _query(
            "SELECT * FROM users WHERE id = %s",
            [3],
            caller="/app/b.py:20:second",
        ),
        _query(
            "SELECT * FROM users WHERE id = %s",
            [4],
            caller="/app/b.py:20:second",
        ),
    ]

    assert analyze_query_patterns(queries, min_occurrences=4) == []


def test_analysis_is_bounded_and_reports_truncation():
    queries = [
        _query("SELECT * FROM products WHERE id = %s", [item_id])
        for item_id in range(1, 10)
    ]

    findings = analyze_query_patterns(
        queries,
        min_occurrences=4,
        max_queries=5,
    )

    assert findings[0]["occurrences"] == 5
    assert findings[0]["capture_limits"] == ["query_analysis_truncated"]
