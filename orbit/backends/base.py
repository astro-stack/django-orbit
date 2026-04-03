"""
Base class for Django Orbit storage backends.
"""


class BaseOrbitBackend:
    """
    Abstract base for Orbit storage backends.

    Subclass this to control where OrbitEntry records are stored.
    """

    def get_db_alias(self) -> str:
        """Return the Django database alias used for all Orbit writes."""
        return "default"

    def setup(self) -> None:
        """
        Called once in AppConfig.ready() after all watchers are installed.

        Override to configure the storage destination, e.g. set
        OrbitEntry.objects._db to redirect ORM calls to a dedicated database.
        """
        pass
