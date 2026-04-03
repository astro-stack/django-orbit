"""
DjangoDBBackend — redirects all Orbit writes to a dedicated database alias.
"""

from django.core.exceptions import ImproperlyConfigured

from orbit.backends.base import BaseOrbitBackend


class DjangoDBBackend(BaseOrbitBackend):
    """
    Stores OrbitEntry records in a separate Django database alias.

    Configure in settings::

        DATABASES = {
            "default": { ... },
            "orbit": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": BASE_DIR / "orbit.sqlite3",
            },
        }

        ORBIT_CONFIG = {
            "STORAGE_BACKEND": "orbit.backends.django_db.DjangoDBBackend",
            "STORAGE_DB_ALIAS": "orbit",   # must match a key in DATABASES
        }

    After ``setup()`` is called every ``OrbitEntry.objects.*`` call is
    transparently routed to the configured alias — no changes to individual
    call sites required.
    """

    def get_db_alias(self) -> str:
        from orbit.conf import get_config

        return get_config().get("STORAGE_DB_ALIAS", "orbit")

    def setup(self) -> None:
        from django.conf import settings

        from orbit.models import OrbitEntry

        alias = self.get_db_alias()
        if alias not in settings.DATABASES:
            raise ImproperlyConfigured(
                f"Django Orbit: STORAGE_DB_ALIAS '{alias}' is not defined in "
                f"DATABASES. Available aliases: {list(settings.DATABASES.keys())}. "
                "Add an entry for this alias or change STORAGE_DB_ALIAS."
            )
        # Redirect ALL ORM calls on OrbitEntry.objects to the target alias.
        # Django's Manager.get_queryset() passes self._db to QuerySet(using=…),
        # so every .create(), .filter(), .bulk_create(), etc. uses this alias.
        OrbitEntry.objects._db = alias
