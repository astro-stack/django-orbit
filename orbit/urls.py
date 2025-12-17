"""
Django Orbit URL Configuration

All Orbit URLs are prefixed with /orbit/ in the main project.
"""

from django.urls import path

from orbit.views import (
    OrbitClearView,
    OrbitDashboardView,
    OrbitDetailPartial,
    OrbitFeedPartial,
    OrbitStatsView,
)

app_name = "orbit"

urlpatterns = [
    # Main dashboard
    path("", OrbitDashboardView.as_view(), name="dashboard"),
    # HTMX partials
    path("feed/", OrbitFeedPartial.as_view(), name="feed"),
    path("detail/<uuid:entry_id>/", OrbitDetailPartial.as_view(), name="detail"),
    # Actions
    path("clear/", OrbitClearView.as_view(), name="clear"),
    # API/Stats
    path("stats/", OrbitStatsView.as_view(), name="stats"),
]
