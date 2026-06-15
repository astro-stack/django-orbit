# API Reference

Orbit ships a dashboard UI plus a small set of internal routes used by that interface.

## Dashboard Routes

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/orbit/` | GET | Main dashboard |
| `/orbit/feed/` | GET | HTMX feed partial used by the live list |
| `/orbit/detail/<uuid:entry_id>/` | GET | HTMX detail partial for a single entry |
| `/orbit/clear/` | POST | Clear all recorded entries |
| `/orbit/export/` | GET | Export all entries |
| `/orbit/export/<uuid:entry_id>/` | GET | Export a single entry |
| `/orbit/stats/` | GET | Stats dashboard |
| `/orbit/health/` | GET | Health and watcher status dashboard |

!!! note
    Orbit does not currently expose a public REST API for entries. The routes above are the dashboard and its internal UI endpoints.

## Models

### OrbitEntry

`OrbitEntry` is the central model used to store all telemetry.

```python
from orbit.models import OrbitEntry

# Get all requests
requests = OrbitEntry.objects.requests()

# Get all queries
queries = OrbitEntry.objects.queries()

# Get exceptions only
exceptions = OrbitEntry.objects.exceptions()
```

## Common Queries

```python
# Recent slow queries
slow_queries = OrbitEntry.objects.queries().filter(duration_ms__gte=500)

# Latest exceptions
latest_exceptions = OrbitEntry.objects.exceptions().order_by("-created_at")[:20]

# A single request family
family_entries = OrbitEntry.objects.filter(family_hash="...")
```

## Related References

- [Dashboard Guide](dashboard.md)
- [Stats Dashboard](stats.md)
- [MCP Server](mcp.md)
