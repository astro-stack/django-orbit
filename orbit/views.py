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

from orbit.models import OrbitEntry


class OrbitDashboardView(TemplateView):
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
        }
        
        # Get error and warning counts for alerts
        context["error_count"] = OrbitEntry.objects.filter(
            type=OrbitEntry.TYPE_EXCEPTION
        ).count() + OrbitEntry.objects.filter(
            type=OrbitEntry.TYPE_REQUEST,
            payload__status_code__gte=400
        ).count()
        
        context["slow_query_count"] = OrbitEntry.objects.filter(
            type=OrbitEntry.TYPE_QUERY,
            payload__is_slow=True
        ).count()
        
        context["current_type"] = entry_type
        
        from django.urls import reverse
        context["orbit_urls"] = {
            "feed": reverse("orbit:feed"),
            "detail_base": reverse("orbit:dashboard") + "detail/",  # Base path for details
            "clear": reverse("orbit:clear"),
        }
        
        return context


class OrbitFeedPartial(View):
    """
    Partial view that returns the feed table content.
    
    This is called by HTMX for polling updates (every 3 seconds)
    and when filtering by entry type.
    """
    
    def get(self, request: HttpRequest) -> HttpResponse:
        # Get filter parameters
        entry_type = request.GET.get("type", "all")
        limit = int(request.GET.get("limit", 50))
        offset = int(request.GET.get("offset", 0))
        family_hash = request.GET.get("family")
        
        # Build queryset
        queryset = OrbitEntry.objects.all()
        
        # Filter by type
        if entry_type and entry_type != "all":
            queryset = queryset.filter(type=entry_type)
        
        # Filter by family
        if family_hash:
            queryset = queryset.filter(family_hash=family_hash)
        
        # Order and limit
        entries = queryset.order_by("-created_at")[offset:offset + limit]
        
        # Render partial
        return TemplateResponse(
            request,
            "orbit/partials/feed.html",
            {
                "entries": entries,
                "current_type": entry_type,
                "has_more": queryset.count() > offset + limit,
                "offset": offset,
                "limit": limit,
            }
        )


class OrbitDetailPartial(View):
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
            related_entries = OrbitEntry.objects.filter(
                family_hash=entry.family_hash
            ).exclude(
                id=entry.id
            ).order_by("created_at")[:50]
        
        # Format payload as pretty JSON
        payload_json = json.dumps(
            entry.payload,
            indent=2,
            ensure_ascii=False,
            default=str
        )
        
        return TemplateResponse(
            request,
            "orbit/partials/detail.html",
            {
                "entry": entry,
                "payload_json": payload_json,
                "related_entries": related_entries,
            }
        )


class OrbitClearView(View):
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
            content_type="text/html"
        )


class OrbitStatsView(View):
    """
    View that returns stats/metrics as JSON.
    """
    
    def get(self, request: HttpRequest) -> JsonResponse:
        from django.db.models import Avg, Count, Max, Min, Sum
        from django.utils import timezone
        from datetime import timedelta
        
        # Time range (last hour)
        since = timezone.now() - timedelta(hours=1)
        
        # Get aggregated stats
        request_stats = OrbitEntry.objects.requests().filter(
            created_at__gte=since
        ).aggregate(
            count=Count("id"),
            avg_duration=Avg("duration_ms"),
            max_duration=Max("duration_ms"),
            error_count=Count("id", filter=models.Q(payload__status_code__gte=400)),
        )
        
        query_stats = OrbitEntry.objects.queries().filter(
            created_at__gte=since
        ).aggregate(
            count=Count("id"),
            avg_duration=Avg("duration_ms"),
            slow_count=Count("id", filter=models.Q(payload__is_slow=True)),
        )
        
        return JsonResponse({
            "requests": request_stats,
            "queries": query_stats,
            "time_range": "1h",
        })
