import pytest

from example_project.demo.models import Book, Review
from orbit.models import OrbitEntry


@pytest.fixture
def query_pattern_books(db):
    books = [
        Book.objects.create(
            title=f"Book {index}",
            author="Orbit",
            isbn=f"9780000000{index:03d}",
        )
        for index in range(6)
    ]
    for index, book in enumerate(books):
        Review.objects.create(
            book=book,
            reviewer_name=f"Reviewer {index}",
            rating=5,
            comment="Deterministic review",
        )
    return books


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("path", "expected_pattern"),
    [
        ("/query-patterns/exact-duplicate/", "exact_duplicate"),
        ("/query-patterns/n-plus-one/", "n_plus_one_candidate"),
        (
            "/query-patterns/per-row-aggregate/",
            "per_row_aggregate_candidate",
        ),
    ],
)
def test_demo_exposes_deterministic_query_pattern_scenarios(
    client, query_pattern_books, path, expected_pattern
):
    response = client.get(path)

    assert response.status_code == 200
    assert response.json()["orbit_demo"]["expected_pattern"] == expected_pattern
    assert response.json()["orbit_demo"]["minimum_occurrences"] >= 4

    captured = OrbitEntry.objects.filter(
        type=OrbitEntry.TYPE_REQUEST,
        payload__path=path,
    ).latest("created_at")
    kinds = {
        pattern["kind"]
        for pattern in captured.payload.get("query_patterns", [])
        if isinstance(pattern, dict)
    }
    assert expected_pattern in kinds


@pytest.mark.django_db
def test_legacy_duplicate_queries_url_remains_an_n_plus_one_alias(
    client, query_pattern_books
):
    response = client.get("/duplicate-queries/")

    assert response.status_code == 200
    assert response.json()["orbit_demo"]["expected_pattern"] == "n_plus_one_candidate"
