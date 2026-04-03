"""
Tests for External Storage Backends (v0.8.0).

Covers:
- DatabaseBackend (default, no-op)
- DjangoDBBackend (dedicated alias)
- get_backend() / get_storage_db_alias() public API
"""

import pytest
import orbit.backends as backends_module
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_orbit_entries(request):
    """Override conftest fixture — only touch DB for tests that need it."""
    if request.node.get_closest_marker("django_db"):
        from orbit.models import OrbitEntry
        OrbitEntry.objects.all().delete()
    yield
    if request.node.get_closest_marker("django_db"):
        from orbit.models import OrbitEntry
        OrbitEntry.objects.all().delete()


@pytest.fixture(autouse=True)
def reset_backend_singleton():
    """Reset the cached backend singleton between tests."""
    old = backends_module._backend
    backends_module._backend = None
    yield
    backends_module._backend = old


@pytest.fixture()
def restore_manager_db():
    """Restore OrbitEntry.objects._db after tests that mutate it."""
    from orbit.models import OrbitEntry
    original = OrbitEntry.objects._db
    yield
    OrbitEntry.objects._db = original


# ---------------------------------------------------------------------------
# DatabaseBackend
# ---------------------------------------------------------------------------

class TestDatabaseBackend:
    def test_get_db_alias_returns_default(self):
        from orbit.backends.database import DatabaseBackend
        assert DatabaseBackend().get_db_alias() == "default"

    def test_setup_resets_manager_to_none(self, restore_manager_db):
        from orbit.backends.database import DatabaseBackend
        from orbit.models import OrbitEntry

        OrbitEntry.objects._db = "some_previous_value"
        DatabaseBackend().setup()
        assert OrbitEntry.objects._db is None

    def test_setup_is_idempotent(self, restore_manager_db):
        from orbit.backends.database import DatabaseBackend
        backend = DatabaseBackend()
        backend.setup()
        backend.setup()  # calling twice must not raise


# ---------------------------------------------------------------------------
# DjangoDBBackend
# ---------------------------------------------------------------------------

class TestDjangoDBBackend:
    def test_get_db_alias_reads_config(self):
        from orbit.backends.django_db import DjangoDBBackend

        with override_settings(ORBIT_CONFIG={"STORAGE_DB_ALIAS": "analytics"}):
            assert DjangoDBBackend().get_db_alias() == "analytics"

    def test_get_db_alias_default_is_orbit(self):
        from orbit.backends.django_db import DjangoDBBackend

        with override_settings(ORBIT_CONFIG={}):
            assert DjangoDBBackend().get_db_alias() == "orbit"

    def test_setup_raises_for_unknown_alias(self):
        from orbit.backends.django_db import DjangoDBBackend

        with override_settings(ORBIT_CONFIG={"STORAGE_DB_ALIAS": "nonexistent_db"}):
            with pytest.raises(ImproperlyConfigured, match="nonexistent_db"):
                DjangoDBBackend().setup()

    def test_setup_sets_manager_db_alias(self, restore_manager_db):
        from orbit.backends.django_db import DjangoDBBackend
        from orbit.models import OrbitEntry

        # 'default' is always in DATABASES in the test environment
        with override_settings(ORBIT_CONFIG={"STORAGE_DB_ALIAS": "default"}):
            DjangoDBBackend().setup()
            assert OrbitEntry.objects._db == "default"

    def test_error_message_lists_available_aliases(self):
        from orbit.backends.django_db import DjangoDBBackend

        with override_settings(ORBIT_CONFIG={"STORAGE_DB_ALIAS": "missing"}):
            with pytest.raises(ImproperlyConfigured, match="default"):
                DjangoDBBackend().setup()


# ---------------------------------------------------------------------------
# get_backend() public API
# ---------------------------------------------------------------------------

class TestGetBackend:
    def test_returns_database_backend_by_default(self):
        from orbit.backends.database import DatabaseBackend

        backend = backends_module.get_backend()
        assert isinstance(backend, DatabaseBackend)

    def test_caches_singleton(self):
        b1 = backends_module.get_backend()
        b2 = backends_module.get_backend()
        assert b1 is b2

    @override_settings(
        ORBIT_CONFIG={"STORAGE_BACKEND": "orbit.backends.django_db.DjangoDBBackend"}
    )
    def test_returns_configured_backend(self):
        from orbit.backends.django_db import DjangoDBBackend

        backend = backends_module.get_backend()
        assert isinstance(backend, DjangoDBBackend)

    def test_raises_for_invalid_import_path(self):
        with override_settings(
            ORBIT_CONFIG={"STORAGE_BACKEND": "nonexistent.module.Backend"}
        ):
            with pytest.raises(ImportError):
                backends_module.get_backend()


# ---------------------------------------------------------------------------
# get_storage_db_alias() public API
# ---------------------------------------------------------------------------

class TestGetStorageDbAlias:
    def test_default_alias_is_default(self):
        assert backends_module.get_storage_db_alias() == "default"

    @override_settings(
        ORBIT_CONFIG={
            "STORAGE_BACKEND": "orbit.backends.django_db.DjangoDBBackend",
            "STORAGE_DB_ALIAS": "default",
        }
    )
    def test_alias_from_django_db_backend(self):
        assert backends_module.get_storage_db_alias() == "default"


# ---------------------------------------------------------------------------
# _table_exists() uses the configured alias
# ---------------------------------------------------------------------------

def test_table_exists_uses_storage_alias(monkeypatch):
    """_table_exists() must introspect the backend's DB alias, not always 'default'."""
    import orbit.watchers as watchers
    from django.db import connections

    monkeypatch.setattr(watchers, "_orbit_table_ready", False)

    # Patch connections['default'].introspection.table_names to return the table
    with pytest.MonkeyPatch().context() as mp:
        # get_storage_db_alias() returns 'default' with the default backend
        from unittest.mock import patch

        with patch.object(
            connections["default"].introspection,
            "table_names",
            return_value=["orbit_orbitentry"],
        ):
            result = watchers._table_exists()

    assert result is True
