"""
Backend tests for duplicate query statistics feature.

Tests the logic in orbit.views.OrbitDetailPartial.get() that computes
duplicate query statistics for REQUEST entries.
"""

import pytest
from django.test import RequestFactory
from orbit.models import OrbitEntry
from orbit.views import OrbitDetailPartial


@pytest.mark.django_db
class TestDuplicateQueryStatsBackend:
    """Test backend computation of duplicate query statistics."""

    def test_duplicate_stats_with_duplicates(self):
        """Test correct calculation when duplicate queries exist."""
        # Create a REQUEST entry with duplicate queries
        family = "test_family_001"
        request_entry = OrbitEntry.objects.create(
            type=OrbitEntry.TYPE_REQUEST,
            family_hash=family,
            payload={
                "method": "GET",
                "path": "/test/",
                "status_code": 200,
                "query_count": 5,
            },
            duration_ms=100.0,
        )

        # Create duplicate queries (same SQL executed 3 times)
        duplicate_sql = "SELECT * FROM auth_user WHERE id = %s"
        for i in range(3):
            OrbitEntry.objects.create(
                type=OrbitEntry.TYPE_QUERY,
                family_hash=family,
                payload={
                    "sql": duplicate_sql,
                    "params": [1],
                    "is_duplicate": i > 0,
                    "duplicate_count": i + 1,
                    "database": "default",
                },
                duration_ms=2.0,
            )

        # Create unique queries
        for i in range(2):
            OrbitEntry.objects.create(
                type=OrbitEntry.TYPE_QUERY,
                family_hash=family,
                payload={
                    "sql": f"SELECT * FROM table_{i}",
                    "params": [],
                    "is_duplicate": False,
                    "duplicate_count": 1,
                    "database": "default",
                },
                duration_ms=1.0,
            )

        # Get the view response
        factory = RequestFactory()
        request = factory.get(f"/orbit/detail/{request_entry.id}/")
        view = OrbitDetailPartial()
        view.request = request
        response = view.get(request, entry_id=str(request_entry.id))

        # Verify stats in context
        duplicate_query_stats = response.context_data["duplicate_query_stats"]
        assert duplicate_query_stats is not None
        assert duplicate_query_stats["total_duplicates"] == 2  # 2nd and 3rd execution
        assert duplicate_query_stats["unique_duplicate_queries"] == 1
        assert duplicate_query_stats["most_duplicated_sql"] == duplicate_sql
        assert duplicate_query_stats["most_duplicated_count"] == 3
        assert duplicate_query_stats["most_duplicated_query_id"] is not None

    def test_duplicate_stats_no_duplicates(self):
        """Test stats when no duplicate queries exist."""
        family = "test_family_002"
        request_entry = OrbitEntry.objects.create(
            type=OrbitEntry.TYPE_REQUEST,
            family_hash=family,
            payload={
                "method": "GET",
                "path": "/test/",
                "status_code": 200,
                "query_count": 3,
            },
            duration_ms=50.0,
        )

        # Create only unique queries
        for i in range(3):
            OrbitEntry.objects.create(
                type=OrbitEntry.TYPE_QUERY,
                family_hash=family,
                payload={
                    "sql": f"SELECT * FROM table_{i}",
                    "params": [],
                    "is_duplicate": False,
                    "duplicate_count": 1,
                    "database": "default",
                },
                duration_ms=1.0,
            )

        # Get the view response
        factory = RequestFactory()
        request = factory.get(f"/orbit/detail/{request_entry.id}/")
        view = OrbitDetailPartial()
        view.request = request
        response = view.get(request, entry_id=str(request_entry.id))

        # Verify stats
        duplicate_query_stats = response.context_data["duplicate_query_stats"]
        assert duplicate_query_stats is not None
        assert duplicate_query_stats["total_duplicates"] == 0
        assert duplicate_query_stats["unique_duplicate_queries"] == 0
        assert duplicate_query_stats["most_duplicated_sql"] is None
        assert duplicate_query_stats["most_duplicated_count"] == 0
        assert duplicate_query_stats["most_duplicated_query_id"] is None

    def test_duplicate_stats_no_queries(self):
        """Test handling when request has no queries."""
        family = "test_family_003"
        request_entry = OrbitEntry.objects.create(
            type=OrbitEntry.TYPE_REQUEST,
            family_hash=family,
            payload={
                "method": "GET",
                "path": "/test/",
                "status_code": 200,
                "query_count": 0,
            },
            duration_ms=10.0,
        )

        # No query entries created

        # Get the view response
        factory = RequestFactory()
        request = factory.get(f"/orbit/detail/{request_entry.id}/")
        view = OrbitDetailPartial()
        view.request = request
        response = view.get(request, entry_id=str(request_entry.id))

        # Verify stats
        duplicate_query_stats = response.context_data["duplicate_query_stats"]
        assert duplicate_query_stats is not None
        assert duplicate_query_stats["total_duplicates"] == 0
        assert duplicate_query_stats["unique_duplicate_queries"] == 0

    def test_duplicate_stats_multiple_duplicate_groups(self):
        """Test correct 'most duplicated' selection with multiple duplicate groups."""
        family = "test_family_004"
        request_entry = OrbitEntry.objects.create(
            type=OrbitEntry.TYPE_REQUEST,
            family_hash=family,
            payload={
                "method": "GET",
                "path": "/test/",
                "status_code": 200,
                "query_count": 8,
            },
            duration_ms=100.0,
        )

        # Group 1: SQL executed 3 times
        sql_1 = "SELECT * FROM auth_user WHERE id = %s"
        for i in range(3):
            OrbitEntry.objects.create(
                type=OrbitEntry.TYPE_QUERY,
                family_hash=family,
                payload={
                    "sql": sql_1,
                    "params": [1],
                    "is_duplicate": i > 0,
                    "duplicate_count": i + 1,
                    "database": "default",
                },
                duration_ms=2.0,
            )

        # Group 2: SQL executed 5 times (should be "most duplicated")
        sql_2 = "SELECT * FROM demo_book ORDER BY id"
        most_duplicated_query_id = None
        for i in range(5):
            entry = OrbitEntry.objects.create(
                type=OrbitEntry.TYPE_QUERY,
                family_hash=family,
                payload={
                    "sql": sql_2,
                    "params": [],
                    "is_duplicate": i > 0,
                    "duplicate_count": i + 1,
                    "database": "default",
                },
                duration_ms=3.0,
            )
            if i == 4:  # Last one has highest duplicate_count
                most_duplicated_query_id = entry.id

        # Get the view response
        factory = RequestFactory()
        request = factory.get(f"/orbit/detail/{request_entry.id}/")
        view = OrbitDetailPartial()
        view.request = request
        response = view.get(request, entry_id=str(request_entry.id))

        # Verify stats
        duplicate_query_stats = response.context_data["duplicate_query_stats"]
        assert duplicate_query_stats is not None
        assert duplicate_query_stats["total_duplicates"] == 6  # 2 from group1 + 4 from group2
        assert duplicate_query_stats["unique_duplicate_queries"] == 2
        assert duplicate_query_stats["most_duplicated_sql"] == sql_2
        assert duplicate_query_stats["most_duplicated_count"] == 5
        assert duplicate_query_stats["most_duplicated_query_id"] == most_duplicated_query_id

    def test_duplicate_stats_non_request_entry(self):
        """Test that stats are None for non-REQUEST entries."""
        # Create a QUERY entry (not a REQUEST)
        query_entry = OrbitEntry.objects.create(
            type=OrbitEntry.TYPE_QUERY,
            payload={
                "sql": "SELECT * FROM auth_user",
                "params": [],
                "database": "default",
            },
            duration_ms=2.0,
        )

        # Get the view response
        factory = RequestFactory()
        request = factory.get(f"/orbit/detail/{query_entry.id}/")
        view = OrbitDetailPartial()
        view.request = request
        response = view.get(request, entry_id=str(query_entry.id))

        # Verify stats are None for non-REQUEST entries
        duplicate_query_stats = response.context_data["duplicate_query_stats"]
        assert duplicate_query_stats is None

    def test_duplicate_stats_request_without_family_hash(self):
        """Test that stats are None when REQUEST has no family_hash."""
        request_entry = OrbitEntry.objects.create(
            type=OrbitEntry.TYPE_REQUEST,
            family_hash=None,  # No family hash
            payload={
                "method": "GET",
                "path": "/test/",
                "status_code": 200,
            },
            duration_ms=10.0,
        )

        # Get the view response
        factory = RequestFactory()
        request = factory.get(f"/orbit/detail/{request_entry.id}/")
        view = OrbitDetailPartial()
        view.request = request
        response = view.get(request, entry_id=str(request_entry.id))

        # Verify stats are None when no family_hash
        duplicate_query_stats = response.context_data["duplicate_query_stats"]
        assert duplicate_query_stats is None

    def test_duplicate_stats_sql_truncation(self):
        """Test that long SQL queries are truncated in the display."""
        family = "test_family_005"
        request_entry = OrbitEntry.objects.create(
            type=OrbitEntry.TYPE_REQUEST,
            family_hash=family,
            payload={
                "method": "GET",
                "path": "/test/",
                "status_code": 200,
                "query_count": 2,
            },
            duration_ms=50.0,
        )

        # Create a very long SQL query (> 120 chars)
        long_sql = "SELECT " + ", ".join([f"field_{i}" for i in range(50)]) + " FROM very_long_table_name WHERE id = %s"
        assert len(long_sql) > 120

        for i in range(2):
            OrbitEntry.objects.create(
                type=OrbitEntry.TYPE_QUERY,
                family_hash=family,
                payload={
                    "sql": long_sql,
                    "params": [1],
                    "is_duplicate": i > 0,
                    "duplicate_count": i + 1,
                    "database": "default",
                },
                duration_ms=2.0,
            )

        # Get the view response
        factory = RequestFactory()
        request = factory.get(f"/orbit/detail/{request_entry.id}/")
        view = OrbitDetailPartial()
        view.request = request
        response = view.get(request, entry_id=str(request_entry.id))

        # Verify SQL is truncated with ellipsis
        duplicate_query_stats = response.context_data["duplicate_query_stats"]
        assert duplicate_query_stats is not None
        assert duplicate_query_stats["most_duplicated_sql"].endswith("...")
        # Should be original + "..." = 120 + 3 = 123 chars
        assert len(duplicate_query_stats["most_duplicated_sql"]) == 123

    def test_duplicate_stats_context_contains_all_fields(self):
        """Test that duplicate_query_stats dict contains all expected fields."""
        family = "test_family_006"
        request_entry = OrbitEntry.objects.create(
            type=OrbitEntry.TYPE_REQUEST,
            family_hash=family,
            payload={
                "method": "GET",
                "path": "/test/",
                "status_code": 200,
                "query_count": 2,
            },
            duration_ms=50.0,
        )

        sql = "SELECT * FROM test_table"
        for i in range(2):
            OrbitEntry.objects.create(
                type=OrbitEntry.TYPE_QUERY,
                family_hash=family,
                payload={
                    "sql": sql,
                    "params": [],
                    "is_duplicate": i > 0,
                    "duplicate_count": i + 1,
                    "database": "default",
                },
                duration_ms=1.0,
            )

        # Get the view response
        factory = RequestFactory()
        request = factory.get(f"/orbit/detail/{request_entry.id}/")
        view = OrbitDetailPartial()
        view.request = request
        response = view.get(request, entry_id=str(request_entry.id))

        # Verify all expected fields exist in stats dict
        duplicate_query_stats = response.context_data["duplicate_query_stats"]
        assert duplicate_query_stats is not None
        
        required_fields = [
            "total_duplicates",
            "unique_duplicate_queries",
            "most_duplicated_sql",
            "most_duplicated_count",
            "most_duplicated_query_id",
        ]
        
        for field in required_fields:
            assert field in duplicate_query_stats, f"Missing field: {field}"
