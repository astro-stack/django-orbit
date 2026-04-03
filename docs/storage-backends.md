# Storage Backends

By default Django Orbit stores all telemetry in your project's `default` database. For production deployments you can redirect all Orbit writes to a dedicated database so observability data doesn't compete with your application traffic.

!!! tip "New in v0.8.0"
    Storage backends are available starting from `django-orbit>=0.8.0`.

## Available Backends

| Backend | Description |
|---------|-------------|
| `orbit.backends.database.DatabaseBackend` | **Default.** Uses Django's `default` database. Zero configuration. |
| `orbit.backends.django_db.DjangoDBBackend` | Dedicated Django database alias. Any engine supported. |

## Default Behaviour

If you don't set `STORAGE_BACKEND`, Orbit uses `DatabaseBackend` — identical behaviour to all versions before v0.8.0. No migration needed, no config change required.

## Dedicated Database (DjangoDBBackend)

Route Orbit writes to a separate database alias:

### 1. Add the database to `DATABASES`

```python
# settings.py
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "myapp",
        # ...
    },
    "orbit": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "orbit.sqlite3",
    },
}
```

Any Django-supported engine works: SQLite, PostgreSQL, MySQL. The alias name (`"orbit"`) is arbitrary — it just needs to match `STORAGE_DB_ALIAS`.

### 2. Configure Orbit

```python
ORBIT_CONFIG = {
    "STORAGE_BACKEND": "orbit.backends.django_db.DjangoDBBackend",
    "STORAGE_DB_ALIAS": "orbit",  # must match a key in DATABASES
}
```

### 3. Run migrations for the new database

```bash
python manage.py migrate orbit --database=orbit
```

Only Orbit's own migrations are run against this alias. Your app's migrations stay on `default`.

### 4. (Optional) Exclude from the default router

If you use `DATABASE_ROUTERS`, make sure your router doesn't try to migrate Orbit's tables to `default`. Add a simple allow-list router or use Django's `allow_migrate` hook:

```python
class OrbitRouter:
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == "orbit":
            return db == "orbit"
        if db == "orbit":
            return False
        return None
```

```python
DATABASE_ROUTERS = ["myapp.routers.OrbitRouter"]
```

## How It Works

`DjangoDBBackend.setup()` sets `OrbitEntry.objects._db = alias` once at Django startup. Django's ORM manager passes `_db` to every queryset, so all `.create()`, `.filter()`, and `.bulk_create()` calls are transparently routed to the configured alias — no changes to any call site.

## Public API

```python
from orbit.backends import get_backend, get_storage_db_alias

# Returns the configured backend singleton
backend = get_backend()

# Returns the database alias used for all Orbit writes
alias = get_storage_db_alias()  # e.g. "default" or "orbit"
```

## Building a Custom Backend

Subclass `BaseOrbitBackend`:

```python
# myapp/orbit_backend.py
from orbit.backends.base import BaseOrbitBackend

class MyCustomBackend(BaseOrbitBackend):
    def get_db_alias(self) -> str:
        return "my_alias"

    def setup(self) -> None:
        # Called once in AppConfig.ready() after watchers are installed
        from orbit.models import OrbitEntry
        OrbitEntry.objects._db = self.get_db_alias()
```

```python
ORBIT_CONFIG = {
    "STORAGE_BACKEND": "myapp.orbit_backend.MyCustomBackend",
}
```

## Next Steps

- [Configuration Reference](configuration.md)
- [MCP Server](mcp.md) — use AI assistants with your stored telemetry
