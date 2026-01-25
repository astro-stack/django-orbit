"""
Django Orbit - Satellite Observability for Django

A modern debugging and observability tool that orbits your Django application
without touching it. Unlike Django Debug Toolbar, Orbit lives in its own
isolated URL with a completely separate, reactive interface.
"""

__version__ = "0.6.3"
__author__ = "Django Orbit Contributors"

default_app_config = "orbit.apps.OrbitConfig"

# User-facing helpers
from orbit.helpers import dump, log

# Watcher status functions (plug-and-play diagnostics)
from orbit.watchers import get_watcher_status, get_installed_watchers, get_failed_watchers

__all__ = ["dump", "log", "get_watcher_status", "get_installed_watchers", "get_failed_watchers"]
