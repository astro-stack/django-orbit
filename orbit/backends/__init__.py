"""
Django Orbit storage backend registry.

Public API::

    from orbit.backends import get_backend, get_storage_db_alias
"""

_backend = None


def get_backend():
    """
    Return the configured storage backend singleton.

    Reads ``ORBIT_CONFIG["STORAGE_BACKEND"]`` (defaults to
    ``"orbit.backends.database.DatabaseBackend"``).  The instance is cached
    for the process lifetime.
    """
    global _backend
    if _backend is None:
        from django.utils.module_loading import import_string

        from orbit.conf import get_config

        config = get_config()
        path = config.get(
            "STORAGE_BACKEND", "orbit.backends.database.DatabaseBackend"
        )
        backend_class = import_string(path)
        _backend = backend_class()
    return _backend


def get_storage_db_alias() -> str:
    """Return the database alias that Orbit uses for all writes."""
    return get_backend().get_db_alias()
