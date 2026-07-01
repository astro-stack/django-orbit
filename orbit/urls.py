"""
Django Orbit URL Configuration

All Orbit URLs are prefixed with /orbit/ in the main project.
"""

from django.urls import path

from orbit.views import (
    OrbitClearView,
    OrbitDashboardView,
    OrbitAgentPromptView,
    OrbitDetailPartial,
    OrbitExportView,
    OrbitFeedPartial,
    OrbitExplainView,
    OrbitHealthView,
    OrbitStatsSectionView,
    OrbitStatsView,
)

app_name = "orbit"

urlpatterns = [
    # Main dashboard
    path("", OrbitDashboardView.as_view(), name="dashboard"),
    # HTMX partials
    path("feed/", OrbitFeedPartial.as_view(), name="feed"),
    path("detail/<uuid:entry_id>/", OrbitDetailPartial.as_view(), name="detail"),
    path("agent-prompt/<uuid:entry_id>/", OrbitAgentPromptView.as_view(), name="agent_prompt"),
    path("explain/<uuid:entry_id>/", OrbitExplainView.as_view(), name="explain"),
    # Actions
    path("clear/", OrbitClearView.as_view(), name="clear"),
    path("export/", OrbitExportView.as_view(), name="export_all"),
    path("export/<uuid:entry_id>/", OrbitExportView.as_view(), name="export"),
    # Stats & Health
    path("stats/", OrbitStatsView.as_view(), name="stats"),
    path("stats/section/<str:section>/", OrbitStatsSectionView.as_view(), name="stats_section"),
    path("health/", OrbitHealthView.as_view(), name="health"),
]
