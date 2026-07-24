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

## Evidence API

For integrations, use the public metadata-first Evidence API instead of
depending on model payload internals:

```python
from orbit.evidence import read_family_evidence

evidence = read_family_evidence("request-family-hash", limit=250)
```

The response uses the versioned `orbit.evidence.v1` schema and contains
normalized plain dictionaries. Storage failures return a structured
`unavailable` state instead of raising into the host application. Callers must
check both `status` and `evidence_quality.status`. Raw payloads, summaries, SQL,
headers, bodies, messages, and tracebacks are not included.

See the [Evidence API guide](evidence-api.md) for the schema, safety boundary,
limits, and compatibility policy.

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
- [Evidence API](evidence-api.md)
- [Stats Dashboard](stats.md)
- [MCP Server](mcp.md)
