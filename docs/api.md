# API Reference

!!! info "Coming Soon"
    This page is under construction. We're working hard to bring you comprehensive documentation!

## Available Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/orbit/` | GET | Dashboard interface |
| `/orbit/api/entries/` | GET | List all entries (JSON) |
| `/orbit/api/counts/` | GET | Entry counts by type |

## Models

### OrbitEntry

The main model for storing captured events.

```python
from orbit.models import OrbitEntry

# Get all requests
requests = OrbitEntry.objects.requests()

# Get all queries
queries = OrbitEntry.objects.queries()

# Get exceptions only
exceptions = OrbitEntry.objects.exceptions()
```

---

*Full API documentation coming soon!*
