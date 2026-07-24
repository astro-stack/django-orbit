import pytest

from orbit.models import OrbitEntry

pytestmark = pytest.mark.django_db


def test_candidate_response_distinguishes_duplicate_only_request():
    from orbit.agentic import find_n_plus_one_candidates

    request = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        family_hash="fam-duplicate-only",
        duration_ms=20.0,
        payload={
            "method": "GET",
            "path": "/settings/",
            "query_count": 4,
            "duplicate_query_count": 3,
            "query_patterns": [
                {
                    "kind": "exact_duplicate",
                    "confidence": "medium",
                    "occurrences": 4,
                    "evidence": ["same_query_shape"],
                    "counter_evidence": ["identical_parameters"],
                }
            ],
            "n_plus_one_count": 0,
        },
    )
    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_QUERY,
        family_hash=request.family_hash,
        payload={
            "sql": "SELECT value FROM settings WHERE name = %s",
            "is_duplicate": True,
            "duplicate_count": 4,
        },
    )

    data = find_n_plus_one_candidates(hours=72)
    candidate = next(
        item
        for item in data["candidates"]
        if item["family_hash"] == request.family_hash
    )

    assert candidate["classification"] == "duplicate_only"
    assert candidate["n_plus_one_findings"] == []
