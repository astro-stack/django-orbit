"""
Django Orbit App Configuration
"""

import logging

from django.apps import AppConfig


class OrbitConfig(AppConfig):
    """Configuration for Django Orbit application."""

    name = "orbit"
    verbose_name = "Django Orbit"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        """
        Called when Django starts. Sets up the Orbit logging handler
        and installs all watchers.
        """
        from orbit.conf import get_config
        from orbit.handlers import OrbitLogHandler

        config = get_config()

        if config.get("ENABLED", True):
            # Add OrbitLogHandler to root logger
            root_logger = logging.getLogger()

            # Check if handler already exists to avoid duplicates
            handler_exists = any(
                isinstance(h, OrbitLogHandler) for h in root_logger.handlers
            )

            if not handler_exists:
                orbit_handler = OrbitLogHandler()
                orbit_handler.setLevel(logging.DEBUG)
                root_logger.addHandler(orbit_handler)

            # Install Phase 1 watchers
            from orbit.watchers import install_all_watchers

            install_all_watchers()

            # Configure storage backend (v0.8.0+)
            from orbit.backends import get_backend

            try:
                get_backend().setup()
            except Exception as exc:
                logging.getLogger(__name__).error(
                    "Django Orbit: storage backend setup failed: %s", exc
                )
