"""
Default Orbit storage backend — stores events in Django's default database.
"""

from orbit.backends.base import BaseOrbitBackend


class DatabaseBackend(BaseOrbitBackend):
    """
    Default backend.  All OrbitEntry records are written to Django's
    ``default`` database with zero configuration required.

    This is a drop-in no-op: existing projects that have not set
    ``STORAGE_BACKEND`` continue to work exactly as before.
    """

    def get_db_alias(self) -> str:
        return "default"

    def setup(self) -> None:
        # Ensure the manager uses the default database (resets any previous
        # value that might have been set during testing).
        from orbit.models import OrbitEntry

        OrbitEntry.objects._db = None
