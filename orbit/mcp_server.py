"""
Django Orbit MCP Server

Exposes OrbitEntry data as MCP (Model Context Protocol) tools so that
AI assistants like Claude, Cursor, and Copilot can query your application's
telemetry directly.

Usage:
    python manage.py orbit_mcp

Then configure your AI assistant (see README for claude_desktop_config.json
and .cursor/mcp.json examples).

Requires the optional 'mcp' dependency:
    pip install django-orbit[mcp]
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _serialize_entry(entry) -> dict:
    """Convert an OrbitEntry to a JSON-serializable dict."""
    return {
        "id": str(entry.id),
        "type": entry.type,
        "summary": entry.summary,
        "duration_ms": entry.duration_ms,
        "family_hash": entry.family_hash,
        "created_at": entry.created_at.isoformat(),
        "payload": entry.payload,
        "is_error": entry.is_error,
        "is_warning": entry.is_warning,
    }


def _format_output(data: Any) -> str:
    """Format data as pretty-printed JSON string for AI consumption."""
    return json.dumps(data, indent=2, default=str)


def create_mcp_server():
    """
    Build and return the FastMCP server instance.

    Called lazily so Django ORM is available when tools run.
    """
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        raise ImportError(
            "The 'mcp' package is required to run the Orbit MCP server.\n"
            "Install it with: pip install django-orbit[mcp]"
        )

    from orbit.conf import get_config
    from orbit.models import OrbitEntry

    config = get_config()
    slow_threshold = config.get("SLOW_QUERY_THRESHOLD_MS", 500)

    mcp = FastMCP(
        "Django Orbit",
        instructions=(
            "Django Orbit captures telemetry from a Django application: HTTP requests, "
            "SQL queries, exceptions, logs, cache operations, model events, background jobs, "
            "and more. Use these tools to debug performance issues, find errors, detect N+1 "
            "query patterns, and understand what your application is doing."
        ),
    )

    # -------------------------------------------------------------------------
    # Tool: get_recent_requests
    # -------------------------------------------------------------------------
    @mcp.tool()
    def get_recent_requests(limit: int = 20) -> str:
        """
        Get the most recent HTTP requests captured by Orbit.

        Returns method, path, status code, duration, and family_hash for
        each request. Use family_hash with get_request_detail() to see all
        events (queries, logs, exceptions) associated with a specific request.

        Args:
            limit: Number of requests to return (max 100, default 20)
        """
        limit = min(limit, 100)
        entries = OrbitEntry.objects.requests().order_by("-created_at")[:limit]
        result = [_serialize_entry(e) for e in entries]
        return _format_output({"count": len(result), "requests": result})

    # -------------------------------------------------------------------------
    # Tool: get_slow_queries
    # -------------------------------------------------------------------------
    @mcp.tool()
    def get_slow_queries(threshold_ms: float = None, limit: int = 20) -> str:
        """
        Get SQL queries that exceeded the slow query threshold.

        Use this to find performance bottlenecks. Each result includes the full
        SQL, execution time, and the family_hash of the request that triggered it.

        Args:
            threshold_ms: Minimum duration to consider slow (default: SLOW_QUERY_THRESHOLD_MS from config)
            limit: Number of results to return (max 100, default 20)
        """
        limit = min(limit, 100)
        threshold = threshold_ms if threshold_ms is not None else slow_threshold

        entries = (
            OrbitEntry.objects.queries()
            .filter(duration_ms__gte=threshold)
            .order_by("-duration_ms")[:limit]
        )
        result = [_serialize_entry(e) for e in entries]
        return _format_output({
            "threshold_ms": threshold,
            "count": len(result),
            "slow_queries": result,
        })

    # -------------------------------------------------------------------------
    # Tool: get_exceptions
    # -------------------------------------------------------------------------
    @mcp.tool()
    def get_exceptions(hours: int = 24, limit: int = 20) -> str:
        """
        Get exceptions captured by Orbit within the specified time window.

        Each result includes the exception type, message, full traceback,
        and the request path where it occurred.

        Args:
            hours: How many hours back to look (default 24)
            limit: Number of results to return (max 100, default 20)
        """
        from django.utils import timezone
        from datetime import timedelta

        limit = min(limit, 100)
        since = timezone.now() - timedelta(hours=hours)

        entries = (
            OrbitEntry.objects.exceptions()
            .filter(created_at__gte=since)
            .order_by("-created_at")[:limit]
        )
        result = [_serialize_entry(e) for e in entries]
        return _format_output({"hours": hours, "count": len(result), "exceptions": result})

    # -------------------------------------------------------------------------
    # Tool: get_n1_patterns
    # -------------------------------------------------------------------------
    @mcp.tool()
    def get_n1_patterns(limit: int = 20) -> str:
        """
        Find HTTP requests that triggered N+1 query patterns.

        Returns requests where duplicate SQL queries were detected — a strong
        signal of missing select_related() or prefetch_related() calls.
        Each result includes the most-duplicated query and its repetition count.

        Args:
            limit: Number of results to return (max 50, default 20)
        """
        limit = min(limit, 50)

        # Requests where Orbit detected duplicate queries
        entries = (
            OrbitEntry.objects.requests()
            .filter(payload__duplicate_query_count__gt=0)
            .order_by("-payload__duplicate_query_count")[:limit]
        )

        results = []
        for entry in entries:
            results.append({
                "id": str(entry.id),
                "path": entry.payload.get("path"),
                "method": entry.payload.get("method"),
                "duration_ms": entry.duration_ms,
                "duplicate_query_count": entry.payload.get("duplicate_query_count", 0),
                "family_hash": entry.family_hash,
                "created_at": entry.created_at.isoformat(),
            })

        return _format_output({"count": len(results), "n1_patterns": results})

    # -------------------------------------------------------------------------
    # Tool: search_entries
    # -------------------------------------------------------------------------
    @mcp.tool()
    def search_entries(query: str, entry_type: str = None, limit: int = 20) -> str:
        """
        Search Orbit entries by keyword across all payload fields.

        Useful for finding all events related to a specific model, endpoint,
        user, error message, or any other string in the telemetry data.

        Args:
            query: Search string to look for in entry payloads
            entry_type: Optional filter — one of: request, query, log, exception,
                        command, cache, model, http_client, mail, signal, redis,
                        gate, transaction, storage, job
            limit: Number of results to return (max 100, default 20)
        """
        limit = min(limit, 100)

        qs = OrbitEntry.objects.all()
        if entry_type:
            qs = qs.filter(type=entry_type)

        # Search in summary (computed) via payload JSON fields
        # Use icontains on the payload cast — works on SQLite and PostgreSQL
        from django.db.models import Q
        qs = qs.filter(
            Q(payload__icontains=query)
        ).order_by("-created_at")[:limit]

        result = [_serialize_entry(e) for e in qs]
        return _format_output({
            "query": query,
            "entry_type": entry_type,
            "count": len(result),
            "entries": result,
        })

    # -------------------------------------------------------------------------
    # Tool: get_request_detail
    # -------------------------------------------------------------------------
    @mcp.tool()
    def get_request_detail(family_hash: str) -> str:
        """
        Get all events associated with a specific HTTP request.

        Given a family_hash from any entry, returns the originating request
        plus all SQL queries, logs, exceptions, and other events that occurred
        during that request's lifecycle. Essential for root-cause analysis.

        Args:
            family_hash: The family_hash value from any OrbitEntry
        """
        entries = OrbitEntry.objects.for_family(family_hash)
        if not entries.exists():
            return _format_output({"error": f"No entries found for family_hash: {family_hash}"})

        result = [_serialize_entry(e) for e in entries]

        # Build a summary
        by_type: dict = {}
        for e in result:
            by_type.setdefault(e["type"], []).append(e)

        return _format_output({
            "family_hash": family_hash,
            "total_events": len(result),
            "event_types": {k: len(v) for k, v in by_type.items()},
            "events": result,
        })

    # -------------------------------------------------------------------------
    # Tool: get_stats_summary
    # -------------------------------------------------------------------------
    @mcp.tool()
    def get_stats_summary(hours: int = 24) -> str:
        """
        Get a high-level summary of application health over the given time window.

        Returns total requests, error rate, average response time, slow query
        count, exception count, cache hit rate, and top error paths.
        Useful for a quick overview before diving into specific issues.

        Args:
            hours: Time window in hours (default 24)
        """
        from django.utils import timezone
        from datetime import timedelta
        from django.db.models import Avg, Count

        since = timezone.now() - timedelta(hours=hours)
        base = OrbitEntry.objects.filter(created_at__gte=since)

        # Requests
        requests = base.filter(type=OrbitEntry.TYPE_REQUEST)
        total_requests = requests.count()
        error_requests = requests.filter(payload__status_code__gte=400).count()
        avg_duration = requests.filter(duration_ms__isnull=False).aggregate(
            avg=Avg("duration_ms")
        )["avg"]

        # Queries
        total_queries = base.filter(type=OrbitEntry.TYPE_QUERY).count()
        slow_queries = base.filter(
            type=OrbitEntry.TYPE_QUERY, duration_ms__gte=slow_threshold
        ).count()

        # Exceptions
        total_exceptions = base.filter(type=OrbitEntry.TYPE_EXCEPTION).count()

        # Cache
        cache_ops = base.filter(type=OrbitEntry.TYPE_CACHE)
        total_cache = cache_ops.count()
        cache_hits = cache_ops.filter(payload__hit=True).count()
        cache_hit_rate = round(cache_hits / total_cache * 100, 1) if total_cache else None

        # Top error paths
        top_errors = (
            requests.filter(payload__status_code__gte=400)
            .values("payload__path", "payload__status_code")
            .annotate(count=Count("id"))
            .order_by("-count")[:5]
        )

        return _format_output({
            "period_hours": hours,
            "requests": {
                "total": total_requests,
                "errors": error_requests,
                "error_rate_pct": round(error_requests / total_requests * 100, 1) if total_requests else 0,
                "avg_duration_ms": round(avg_duration, 1) if avg_duration else None,
            },
            "queries": {
                "total": total_queries,
                "slow": slow_queries,
                "slow_threshold_ms": slow_threshold,
            },
            "exceptions": {"total": total_exceptions},
            "cache": {
                "total_ops": total_cache,
                "hit_rate_pct": cache_hit_rate,
            },
            "top_error_paths": list(top_errors),
        })

    return mcp
