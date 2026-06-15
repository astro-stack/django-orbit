"""
Django Orbit Views

Dashboard views for the Orbit interface.
"""

import json

from django.db.models import Window, F, Case, When, BooleanField
from django.db.models.functions import RowNumber
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.views import View
from django.views.generic import TemplateView

__all__ = [
    "OrbitDashboardView",
    "OrbitFeedPartial",
    "OrbitDetailPartial",
    "OrbitClearView",
    "OrbitStatsView",
    "OrbitStatsSectionView",
    "OrbitExplainView",
    "OrbitExportView",
    "OrbitHealthView",
]

from orbit import __version__ as ORBIT_VERSION
from orbit.models import OrbitEntry
from orbit.mixins import OrbitProtectedView


# Sidebar navigation, grouped for progressive disclosure (see DESIGN.md › Layout).
# Each item: (type_key, label). Icons/colors come from OrbitEntry.TYPE_ICONS/TYPE_COLORS.
# "all" is a pseudo-type that matches every entry.
NAV_GROUPS = [
    {
        "key": "core",
        "label": "Core",
        "open": True,
        "items": [
            # "All Events" is rendered as a standalone item above the groups (it's a
            # meta-filter, not an entry type).
            (OrbitEntry.TYPE_REQUEST, "Requests"),
            (OrbitEntry.TYPE_QUERY, "Queries"),
            (OrbitEntry.TYPE_EXCEPTION, "Exceptions"),
            (OrbitEntry.TYPE_LOG, "Logs"),
        ],
    },
    {
        "key": "infra",
        "label": "Infrastructure",
        "open": False,
        "items": [
            (OrbitEntry.TYPE_CACHE, "Cache"),
            (OrbitEntry.TYPE_REDIS, "Redis"),
            (OrbitEntry.TYPE_HTTP_CLIENT, "HTTP Client"),
            (OrbitEntry.TYPE_MAIL, "Mail"),
            (OrbitEntry.TYPE_STORAGE, "Storage"),
        ],
    },
    {
        "key": "app",
        "label": "Application",
        "open": False,
        "items": [
            (OrbitEntry.TYPE_MODEL, "Models"),
            (OrbitEntry.TYPE_JOB, "Jobs"),
            (OrbitEntry.TYPE_COMMAND, "Commands"),
            (OrbitEntry.TYPE_SIGNAL, "Signals"),
            (OrbitEntry.TYPE_GATE, "Gates"),
            (OrbitEntry.TYPE_TRANSACTION, "Transactions"),
            (OrbitEntry.TYPE_DUMP, "Dumps"),
        ],
    },
]

# Entry types whose count badge should turn rose when non-zero (problem signals).
ALERT_TYPES = {OrbitEntry.TYPE_EXCEPTION}


def build_nav_groups(counts, current_type="all"):
    """Render NAV_GROUPS into template-ready dicts with counts, icons and colors.

    A group starts expanded if configured open, or if it contains the active type
    so the current selection is always visible on load.
    """
    groups = []
    for group in NAV_GROUPS:
        items = []
        for type_key, label in group["items"]:
            icon = "layers" if type_key == "all" else OrbitEntry.TYPE_ICONS.get(type_key, "circle")
            color = "cyan" if type_key == "all" else OrbitEntry.TYPE_COLORS.get(type_key, "slate")
            items.append(
                {
                    "type": type_key,
                    "label": label,
                    "icon": icon,
                    "color": color,
                    "count": counts.get(type_key, 0),
                    "is_alert": type_key in ALERT_TYPES,
                }
            )
        contains_active = any(item["type"] == current_type for item in items)
        groups.append(
            {
                "key": group["key"],
                "label": group["label"],
                "open": group["open"] or contains_active,
                "items": items,
            }
        )
    return groups


class OrbitDashboardView(OrbitProtectedView, TemplateView):
    """
    Main dashboard view that renders the shell interface.

    The shell contains the sidebar navigation and main content area
    where partials are loaded via HTMX.
    """

    template_name = "orbit/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get entry type from query params (for filtering)
        entry_type = self.request.GET.get("type", "all")

        # Get counts for sidebar badges
        context["counts"] = {
            "all": OrbitEntry.objects.count(),
            "request": OrbitEntry.objects.requests().count(),
            "query": OrbitEntry.objects.queries().count(),
            "log": OrbitEntry.objects.logs().count(),
            "exception": OrbitEntry.objects.exceptions().count(),
            "job": OrbitEntry.objects.jobs().count(),
            # Phase 1 types
            "command": OrbitEntry.objects.commands().count(),
            "cache": OrbitEntry.objects.cache_ops().count(),
            "model": OrbitEntry.objects.models().count(),
            "http_client": OrbitEntry.objects.http_client().count(),
            "dump": OrbitEntry.objects.dumps().count(),
            # Phase 2 types (v0.4.0)
            "mail": OrbitEntry.objects.mails().count(),
            "signal": OrbitEntry.objects.signals().count(),
            # Phase 3 types (v0.5.0)
            "redis": OrbitEntry.objects.redis_ops().count(),
            "gate": OrbitEntry.objects.gates().count(),
            # Phase 4 types (v0.6.0)
            "transaction": OrbitEntry.objects.filter(type=OrbitEntry.TYPE_TRANSACTION).count(),
            "storage": OrbitEntry.objects.filter(type=OrbitEntry.TYPE_STORAGE).count(),
        }

        # Get error and warning counts for alerts
        context["error_count"] = (
            OrbitEntry.objects.filter(type=OrbitEntry.TYPE_EXCEPTION).count()
            + OrbitEntry.objects.filter(
                type=OrbitEntry.TYPE_REQUEST, payload__status_code__gte=400
            ).count()
        )

        context["slow_query_count"] = OrbitEntry.objects.filter(
            type=OrbitEntry.TYPE_QUERY, payload__is_slow=True
        ).count()

        context["current_type"] = entry_type

        # Grouped sidebar navigation + package version (single source of truth)
        context["nav_groups"] = build_nav_groups(context["counts"], entry_type)
        context["orbit_version"] = ORBIT_VERSION

        # Calculate statistics for dashboard
        from django.db.models import Avg
        from datetime import timedelta
        from django.utils import timezone

        now = timezone.now()
        last_hour = now - timedelta(hours=1)
        last_24h = now - timedelta(hours=24)

        # Performance stats
        requests_last_hour = OrbitEntry.objects.filter(
            type=OrbitEntry.TYPE_REQUEST,
            created_at__gte=last_hour
        )
        
        queries_last_hour = OrbitEntry.objects.filter(
            type=OrbitEntry.TYPE_QUERY,
            created_at__gte=last_hour
        )

        context["stats"] = {
            # Request metrics
            "requests_per_hour": requests_last_hour.count(),
            "avg_response_time": requests_last_hour.aggregate(
                avg=Avg("duration_ms")
            )["avg"] or 0,
            
            # Query metrics
            "queries_per_hour": queries_last_hour.count(),
            "avg_query_time": queries_last_hour.aggregate(
                avg=Avg("duration_ms")
            )["avg"] or 0,
            "slow_queries_pct": (
                (context["slow_query_count"] / context["counts"]["query"] * 100)
                if context["counts"]["query"] > 0 else 0
            ),
            "duplicate_queries": OrbitEntry.objects.filter(
                type=OrbitEntry.TYPE_QUERY,
                payload__is_duplicate=True
            ).count(),
            
            # Error metrics
            "error_rate": (
                (context["error_count"] / context["counts"]["request"] * 100)
                if context["counts"]["request"] > 0 else 0
            ),
            "exceptions_24h": OrbitEntry.objects.filter(
                type=OrbitEntry.TYPE_EXCEPTION,
                created_at__gte=last_24h
            ).count(),
            
            # Cache metrics
            "cache_hits": OrbitEntry.objects.filter(
                type=OrbitEntry.TYPE_CACHE,
                payload__hit=True
            ).count(),
            "cache_misses": OrbitEntry.objects.filter(
                type=OrbitEntry.TYPE_CACHE,
                payload__hit=False
            ).count(),
            
            # Permission metrics
            "permission_denied": OrbitEntry.objects.filter(
                type=OrbitEntry.TYPE_GATE,
                payload__result="denied"
            ).count(),
            "permission_granted": OrbitEntry.objects.filter(
                type=OrbitEntry.TYPE_GATE,
                payload__result="granted"
            ).count(),
            
            # Job metrics
            "jobs_failed": OrbitEntry.objects.filter(
                type=OrbitEntry.TYPE_JOB,
                payload__status="failed"
            ).count(),
            "jobs_success": OrbitEntry.objects.filter(
                type=OrbitEntry.TYPE_JOB,
                payload__status="success"
            ).count(),
        }
        
        # Calculate cache hit rate
        total_cache = context["stats"]["cache_hits"] + context["stats"]["cache_misses"]
        context["stats"]["cache_hit_rate"] = (
            (context["stats"]["cache_hits"] / total_cache * 100)
            if total_cache > 0 else 0
        )

        from django.urls import reverse

        context["orbit_urls"] = {
            "feed": reverse("orbit:feed"),
            "detail_base": reverse("orbit:dashboard")
            + "detail/",  # Base path for details
            "clear": reverse("orbit:clear"),
            "export_all": reverse("orbit:export_all"),
        }

        return context


class OrbitFeedPartial(OrbitProtectedView, View):
    """
    Partial view that returns the feed table content.

    This is called by HTMX for polling updates (every 3 seconds)
    and when filtering by entry type.
    """

    def get(self, request: HttpRequest) -> HttpResponse:
        # Get filter parameters
        entry_type = request.GET.get("type", "all")
        per_page = int(request.GET.get("per_page", 25))
        page = int(request.GET.get("page", 1))
        family_hash = request.GET.get("family")

        # Build queryset
        queryset = OrbitEntry.objects.all()

        # Filter by type
        if entry_type and entry_type != "all":
            queryset = queryset.filter(type=entry_type)

        # Filter by family
        if family_hash:
            queryset = queryset.filter(family_hash=family_hash)

        query = request.GET.get("q")

        # Tag filter (B1): explicit ?tag=foo, or a "tag:foo" prefix typed in the search box.
        tag = request.GET.get("tag")
        if not tag and query and query.lower().startswith("tag:"):
            tag = query[4:].strip()
            query = None
        if tag:
            queryset = queryset.filter(tags__contains="," + tag + ",")

        # Exception grouping (B3): on the plain Exceptions view, collapse identical
        # exceptions into one row with a count + first/last seen. Skipped when searching
        # or drilling into a family so those flows still show individual occurrences.
        if entry_type == OrbitEntry.TYPE_EXCEPTION and not family_hash and not query and not tag:
            return self._exception_groups_response(request, per_page, page)

        # Filter by search query "q"
        if query:
            import uuid
            try:
                # Try explicit UUID search
                uuid_obj = uuid.UUID(query)
                queryset = queryset.filter(id=uuid_obj)
            except ValueError:
                # Text search on payload using generic "contains"
                # For SQLite/Postgres JSONField, we can use __icontains
                # Ideally we cast to text for better compatibility if needed, 
                # but let's try direct first as it handles some string casting implicitly in Django 4.2+
                from django.db.models import TextField
                from django.db.models.functions import Cast
                
                # Cast payload to text to search inside keys and values
                queryset = queryset.annotate(
                    payload_text=Cast("payload", TextField())
                ).filter(payload_text__icontains=query)

        # Calculate pagination
        total_count = queryset.count()
        total_pages = (total_count + per_page - 1) // per_page  # Ceiling division
        page = max(1, min(page, total_pages)) if total_pages > 0 else 1

        # Get entries for current page - only load necessary fields for performance
        offset = (page - 1) * per_page
        entries = queryset.only(
            'id', 'type', 'payload', 'duration_ms', 'created_at'
        ).order_by("-created_at")[offset : offset + per_page]

        # Render partial
        return TemplateResponse(
            request,
            "orbit/partials/feed.html",
            {
                "entries": entries,
                "current_type": entry_type,
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages,
                "total_count": total_count,
                "has_prev": page > 1,
                "has_next": page < total_pages,
            },
        )

    def _exception_groups_response(self, request, per_page, page):
        """Render the grouped Exceptions feed (B3). Aggregation happens in the DB."""
        groups_qs = OrbitEntry.objects.exception_groups()

        total_count = groups_qs.count()  # number of distinct errors
        total_pages = (total_count + per_page - 1) // per_page
        page = max(1, min(page, total_pages)) if total_pages > 0 else 1
        offset = (page - 1) * per_page

        page_groups = list(groups_qs[offset : offset + per_page])
        group_keys = [g["group_key"] for g in page_groups]
        latest = OrbitEntry.objects.latest_for_groups(group_keys)

        groups = []
        for g in page_groups:
            rep = latest.get(g["group_key"])
            if rep is None:
                continue
            groups.append(
                {
                    "entry": rep,
                    "count": g["count"],
                    "first_seen": g["first_seen"],
                    "last_seen": g["last_seen"],
                }
            )

        return TemplateResponse(
            request,
            "orbit/partials/feed_exception_groups.html",
            {
                "groups": groups,
                "current_type": OrbitEntry.TYPE_EXCEPTION,
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages,
                "total_count": total_count,
                "has_prev": page > 1,
                "has_next": page < total_pages,
            },
        )


class OrbitDetailPartial(OrbitProtectedView, View):
    """
    Partial view that returns the detail panel for a specific entry.

    Shows the full JSON payload with syntax highlighting and
    related entries (same family_hash).
    """

    def get(self, request: HttpRequest, entry_id: str) -> HttpResponse:
        # Get the entry
        entry = get_object_or_404(OrbitEntry, id=entry_id)

        # Get related entries (same family)
        # Annotate top 3 slowest by duration
        related_entries = []
        if entry.family_hash:
            related_entries = (
                OrbitEntry.objects.filter(family_hash=entry.family_hash)
                .exclude(id=entry.id)
                .annotate(
                    slow_rank=Window(
                        expression=RowNumber(),
                        partition_by=F("type"),
                        order_by=F("duration_ms").desc(nulls_last=True),
                    )
                )
                .annotate(
                    is_top_slowest=Case(
                        When(type=OrbitEntry.TYPE_QUERY, slow_rank__lte=3, then=True),
                        default=False,
                        output_field=BooleanField(),
                    )
                )
                .order_by("created_at")[:100]
            )

        # Get duplicate queries (same SQL) for query entries
        duplicate_entries = []
        if entry.type == OrbitEntry.TYPE_QUERY:
            sql = entry.payload.get("sql", "")
            if sql and entry.payload.get("is_duplicate"):
                duplicate_entries = (
                    OrbitEntry.objects.filter(
                        type=OrbitEntry.TYPE_QUERY,
                        payload__sql=sql,
                    )
                    .exclude(id=entry.id)
                    .order_by("-created_at")[:20]
                )

        # Compute duplicate query stats for REQUEST entries
        duplicate_query_stats = None
        if entry.type == OrbitEntry.TYPE_REQUEST and entry.family_hash:
            precomputed_total = entry.payload.get("duplicate_query_count")

            # Optimization: If we already know there are zero duplicates, skip expensive processing
            if precomputed_total == 0:
                duplicate_query_stats = {
                    "total_duplicates": 0,
                    "unique_duplicate_queries": 0,
                    "most_duplicated_sql": None,
                    "most_duplicated_count": 0,
                    "most_duplicated_query_id": None,
                }
            else:
                query_entries = OrbitEntry.objects.filter(
                    family_hash=entry.family_hash, type=OrbitEntry.TYPE_QUERY
                ).only("payload")

                total_duplicates = 0
                query_groups = {}
                query_ids = {}

                for query in query_entries:
                    sql = query.payload.get("sql")
                    if not sql:
                        continue
                    
                    duplicate_count = query.payload.get("duplicate_count", 1)
                    is_duplicate = query.payload.get("is_duplicate", False)

                    # Count total redundant executions
                    if is_duplicate:
                        total_duplicates += 1

                    # Track unique duplicated queries (those executed more than once)
                    if duplicate_count > 1:
                        # Keep track of the highest execution count and a representative ID
                        if sql not in query_groups or duplicate_count > query_groups[sql]:
                            query_groups[sql] = duplicate_count
                            query_ids[sql] = query.id

                # Use precomputed total if available (fallback to calculated for old data)
                final_total = precomputed_total if precomputed_total is not None else total_duplicates

                # Find the most duplicated query
                most_duplicated_sql = None
                most_duplicated_count = 0
                most_duplicated_query_id = None

                if query_groups:
                    most_duplicated_sql = max(query_groups, key=query_groups.get)
                    most_duplicated_count = query_groups[most_duplicated_sql]
                    most_duplicated_query_id = query_ids.get(most_duplicated_sql)

                    # Truncate SQL for display to keep it readable in the UI
                    if len(most_duplicated_sql) > 120:
                        most_duplicated_sql = most_duplicated_sql[:120] + "..."

                duplicate_query_stats = {
                    "total_duplicates": final_total,
                    "unique_duplicate_queries": len(query_groups),
                    "most_duplicated_sql": most_duplicated_sql,
                    "most_duplicated_count": most_duplicated_count,
                    "most_duplicated_query_id": most_duplicated_query_id,
                }

        # Request waterfall (B4): position child query spans on the request timeline.
        waterfall = self._build_waterfall(entry, related_entries)

        # Format payload as pretty JSON
        payload_json = json.dumps(
            entry.payload, indent=2, ensure_ascii=False, default=str
        )

        return TemplateResponse(
            request,
            "orbit/partials/detail.html",
            {
                "entry": entry,
                "payload_json": payload_json,
                "related_entries": related_entries,
                "duplicate_entries": duplicate_entries,
                "duplicate_query_stats": duplicate_query_stats,
                "waterfall": waterfall,
            },
        )

    @staticmethod
    def _build_waterfall(entry, related_entries):
        """
        Build span bars (left%/width%) for a request's child queries.

        Uses each query's recorded start_offset_ms (accurate, captured at execution) over
        the request's total duration. Pure arithmetic on already-fetched rows — no extra
        queries. Returns None when there's nothing meaningful to show.
        """
        if entry.type != OrbitEntry.TYPE_REQUEST or not entry.duration_ms:
            return None

        total = entry.duration_ms
        spans = []
        for rel in related_entries:
            if rel.type != OrbitEntry.TYPE_QUERY:
                continue
            payload = rel.payload or {}
            offset = payload.get("start_offset_ms")
            dur = rel.duration_ms
            if offset is None or dur is None:
                continue
            left = max(0.0, min(100.0, (offset / total) * 100))
            width = max(0.6, min(100.0 - left, (dur / total) * 100))
            spans.append(
                {
                    "id": rel.id,
                    "left": round(left, 2),
                    "width": round(width, 2),
                    "duration_ms": dur,
                    "is_slow": payload.get("is_slow", False),
                    "is_duplicate": payload.get("is_duplicate", False),
                    "sql": (payload.get("sql", "") or "")[:80],
                }
            )

        if not spans:
            return None
        return {"total_ms": round(total, 1), "spans": spans, "count": len(spans)}


class OrbitClearView(OrbitProtectedView, View):
    """
    View to clear all Orbit entries.
    """

    def post(self, request: HttpRequest) -> HttpResponse:
        # Clear all entries
        count = OrbitEntry.objects.count()
        OrbitEntry.objects.all().delete()

        # Return success response for HTMX
        return HttpResponse(
            f'<div class="text-emerald-400">Cleared {count} entries</div>',
            content_type="text/html",
        )


# Stats time ranges accepted by the dashboard and section endpoints.
STATS_TIME_RANGES = ["1h", "6h", "24h", "7d"]


def normalize_stats_range(value):
    """Clamp a requested time range to a known value (default 24h)."""
    return value if value in STATS_TIME_RANGES else "24h"


class OrbitStatsView(OrbitProtectedView, TemplateView):
    """
    Full-page Stats Dashboard.

    Only the lightweight headline (summary + percentiles) is computed here so the
    page paints fast. Heavier sections (trends, database, cache, jobs, security)
    are loaded lazily via OrbitStatsSectionView, which keeps each DB hit small and
    avoids the SQLite lock that the old "compute everything at once" path caused.
    """
    template_name = "orbit/stats.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        from orbit import stats

        time_range = normalize_stats_range(self.request.GET.get("range", "24h"))
        context["time_range"] = time_range
        context["time_ranges"] = STATS_TIME_RANGES

        # Headline only — cheap aggregates, rendered immediately.
        try:
            context["summary"] = stats.get_summary_stats(time_range)
            context["percentiles"] = stats.get_percentiles(time_range)
        except Exception as e:
            context["error"] = str(e)

        # Add URLs
        from django.urls import reverse
        context['dashboard_url'] = reverse('orbit:dashboard')
        context['orbit_version'] = ORBIT_VERSION

        return context


class OrbitStatsSectionView(OrbitProtectedView, View):
    """
    Returns a single Stats section as an HTML fragment for lazy (HTMX) loading.

    Each section computes only its own metrics, so one slow/failed section never
    blocks the rest of the page and the DB is touched in small independent reads.
    """

    # section name -> (template fragment, builder returning a context dict)
    SECTIONS = {
        "trends": "orbit/partials/stats_trends.html",
        "database": "orbit/partials/stats_database.html",
        "cache": "orbit/partials/stats_cache.html",
        "jobs": "orbit/partials/stats_jobs.html",
        "security": "orbit/partials/stats_security.html",
    }

    def get(self, request: HttpRequest, section: str) -> HttpResponse:
        from django.http import Http404
        from orbit import stats

        template = self.SECTIONS.get(section)
        if template is None:
            raise Http404("Unknown stats section")

        time_range = normalize_stats_range(request.GET.get("range", "24h"))
        ctx = {"time_range": time_range}

        try:
            if section == "trends":
                ctx["response_time_data"] = stats.get_response_time_trend(time_range)
                ctx["throughput_data"] = stats.get_throughput_data(time_range)
                ctx["error_trend_data"] = stats.get_error_rate_trend(time_range)
            elif section == "database":
                ctx["database"] = stats.get_database_metrics(time_range)
            elif section == "cache":
                ctx["cache"] = stats.get_cache_metrics(time_range)
            elif section == "jobs":
                ctx["jobs"] = stats.get_jobs_metrics(time_range)
            elif section == "security":
                ctx["security"] = stats.get_security_metrics(time_range)
        except Exception as e:
            ctx["error"] = str(e)

        return TemplateResponse(request, template, ctx)


class OrbitExplainView(OrbitProtectedView, View):
    """Run EXPLAIN for a captured query entry, on demand (B2)."""

    def get(self, request: HttpRequest, entry_id: str) -> HttpResponse:
        from orbit.conf import get_config
        from orbit.explain import explain_query

        config = get_config()
        ctx = {"entry_id": entry_id}

        if not config.get("ENABLE_EXPLAIN", True):
            ctx["error"] = "EXPLAIN is disabled (ENABLE_EXPLAIN=False)."
            return TemplateResponse(request, "orbit/partials/explain.html", ctx)

        entry = get_object_or_404(OrbitEntry, id=entry_id)
        payload = entry.payload or {}
        sql = payload.get("sql", "")
        if entry.type != OrbitEntry.TYPE_QUERY or not sql:
            ctx["error"] = "This entry has no SQL to explain."
            return TemplateResponse(request, "orbit/partials/explain.html", ctx)

        ctx["result"] = explain_query(
            sql,
            params=payload.get("params"),
            analyze=config.get("EXPLAIN_ANALYZE", False),
        )
        return TemplateResponse(request, "orbit/partials/explain.html", ctx)


class OrbitExportView(OrbitProtectedView, View):
    """
    View to export one or many entries as JSON.
    """

    def get(self, request: HttpRequest, entry_id: str = None) -> HttpResponse:
        # Single Entry Export
        if entry_id:
            entry = get_object_or_404(OrbitEntry, id=entry_id)
            
            data = {
                "entry": {
                    "id": str(entry.id),
                    "type": entry.type,
                    "created_at": entry.created_at.isoformat(),
                    "payload": entry.payload,
                    "duration_ms": entry.duration_ms,
                    "family_hash": entry.family_hash,
                },
                "related": [],
            }

            if entry.family_hash:
                related_qs = (
                    OrbitEntry.objects.filter(family_hash=entry.family_hash)
                    .exclude(id=entry.id)
                    .order_by("created_at")
                )
                
                for rel in related_qs:
                    data["related"].append({
                        "id": str(rel.id),
                        "type": rel.type,
                        "created_at": rel.created_at.isoformat(),
                        "payload": rel.payload,
                        "duration_ms": rel.duration_ms,
                    })
            
            response = JsonResponse(data, json_dumps_params={"indent": 2})
            response["Content-Disposition"] = f'attachment; filename="orbit_entry_{entry.id}.json"'
            return response

        # Bulk Export (Streaming)
        from django.http import StreamingHttpResponse
        
        # 1. Reuse filtering logic from OrbitFeedPartial
        queryset = OrbitEntry.objects.all().order_by("-created_at")
        
        entry_type = request.GET.get("type", "all")
        if entry_type and entry_type != "all":
            queryset = queryset.filter(type=entry_type)

        family_hash = request.GET.get("family")
        if family_hash:
            queryset = queryset.filter(family_hash=family_hash)

        query = request.GET.get("q")
        if query:
            import uuid
            try:
                uuid_obj = uuid.UUID(query)
                queryset = queryset.filter(id=uuid_obj)
            except ValueError:
                from django.db.models import TextField
                from django.db.models.functions import Cast
                queryset = queryset.annotate(
                    payload_text=Cast("payload", TextField())
                ).filter(payload_text__icontains=query)

        # 2. Generator function
        def stream_generator():
            yield "[\n"
            first = True
            for entry in queryset.iterator(chunk_size=500):
                if not first:
                    yield ",\n"
                first = False
                
                # Manual JSON serialization for speed/simplicity in generator
                # using json.dumps for the dict is safest
                yield json.dumps({
                    "id": str(entry.id),
                    "type": entry.type,
                    "created_at": entry.created_at.isoformat(),
                    "payload": entry.payload,
                    "duration_ms": entry.duration_ms,
                    "family_hash": entry.family_hash,
                }, default=str)
            yield "\n]"

        response = StreamingHttpResponse(
            stream_generator(), 
            content_type="application/json"
        )
        response["Content-Disposition"] = 'attachment; filename="orbit_export_all.json"'
        return response


class OrbitHealthView(OrbitProtectedView, TemplateView):
    """
    Health Dashboard view showing the status of all Orbit modules.
    
    This is the plug-and-play diagnostics page that shows:
    - Which modules are installed and working (green)
    - Which modules failed and why (red)
    - Which modules are disabled via configuration
    """
    template_name = "orbit/health.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get health status from the health module
        try:
            from orbit.health import get_health_status, is_orbit_healthy
            health = get_health_status()
            context['health'] = health
            context['is_healthy'] = is_orbit_healthy()
        except Exception as e:
            context['health'] = {
                'error': str(e),
                'total': 0,
                'healthy_count': 0,
                'failed_count': 0,
                'modules': [],
            }
            context['is_healthy'] = False
        
        # Also get watcher status from the watchers module
        try:
            from orbit.watchers import get_watcher_status, get_installed_watchers, get_failed_watchers
            watcher_status = get_watcher_status()
            
            # Convert watcher status to module format for unified display
            watcher_modules = []
            for name, status in watcher_status.items():
                watcher_modules.append({
                    'name': name,
                    'description': f'Watcher: {name}',
                    'category': 'watcher',
                    'status': 'healthy' if status.get('installed') else ('disabled' if status.get('disabled') else 'failed'),
                    'is_healthy': status.get('installed', False),
                    'is_failed': not status.get('installed') and not status.get('disabled') and status.get('error'),
                    'is_disabled': status.get('disabled', False),
                    'error': status.get('error'),
                    'error_traceback': None,
                })
            
            context['watchers'] = {
                'modules': watcher_modules,
                'installed': get_installed_watchers(),
                'failed': get_failed_watchers(),
                'total': len(watcher_status),
                'installed_count': len(get_installed_watchers()),
                'failed_count': len(get_failed_watchers()),
            }
        except Exception as e:
            context['watchers'] = {
                'error': str(e),
                'modules': [],
                'installed': [],
                'failed': {},
                'total': 0,
                'installed_count': 0,
                'failed_count': 0,
            }
        
        # Add URLs
        from django.urls import reverse
        context['dashboard_url'] = reverse('orbit:dashboard')
        context['stats_url'] = reverse('orbit:stats')
        context['orbit_version'] = ORBIT_VERSION

        return context
