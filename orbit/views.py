"""
Django Orbit Views

Dashboard views for the Orbit interface.
"""

import json
from typing import Optional

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
    "OrbitExportView",
]

from orbit.models import OrbitEntry
from orbit.mixins import OrbitProtectedView


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

        from django.urls import reverse

        context["orbit_urls"] = {
            "feed": reverse("orbit:feed"),
            "detail_base": reverse("orbit:dashboard")
            + "detail/",  # Base path for details
            "clear": reverse("orbit:clear"),
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

        # Filter by search query "q"
        query = request.GET.get("q")
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

        # Get entries for current page
        offset = (page - 1) * per_page
        entries = queryset.order_by("-created_at")[offset : offset + per_page]

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
        related_entries = []
        if entry.family_hash:
            related_entries = (
                OrbitEntry.objects.filter(family_hash=entry.family_hash)
                .exclude(id=entry.id)
                .order_by("created_at")[:50]
            )

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
            },
        )


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


class OrbitStatsView(OrbitProtectedView, View):
    """
    View that returns stats/metrics as JSON.
    """

    def get(self, request: HttpRequest) -> JsonResponse:
        from datetime import timedelta

        from django.db.models import Avg, Count, Max, Min, Sum
        from django.utils import timezone

        # Time range (last hour)
        since = timezone.now() - timedelta(hours=1)

        # Get aggregated stats
        request_stats = (
            OrbitEntry.objects.requests()
            .filter(created_at__gte=since)
            .aggregate(
                count=Count("id"),
                avg_duration=Avg("duration_ms"),
                max_duration=Max("duration_ms"),
                error_count=Count("id", filter=models.Q(payload__status_code__gte=400)),
            )
        )

        query_stats = (
            OrbitEntry.objects.queries()
            .filter(created_at__gte=since)
            .aggregate(
                count=Count("id"),
                avg_duration=Avg("duration_ms"),
                slow_count=Count("id", filter=models.Q(payload__is_slow=True)),
            )
        )

        return JsonResponse(
            {
                "requests": request_stats,
                "queries": query_stats,
                "time_range": "1h",
            }
        )


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
