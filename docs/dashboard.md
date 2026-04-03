# Dashboard Guide

The Django Orbit dashboard is your mission control center, available at `/orbit/` (by default). It provides a real-time, unified view of your application's telemetry.

## Navigation & Filtering

### Sidebar

The sidebar groups events by type. The number in the badge indicates the total count of captured events for that type. The sidebar is scrollable when you have many event types.

#### Core Events

| Type | Icon | Description |
|------|------|-------------|
| **All Events** | 📋 | Unified feed of everything |
| **Requests** | 🌐 | HTTP requests (method, path, status, duration) |
| **Queries** | 🗄️ | SQL queries with N+1 detection |
| **Logs** | 📝 | Python logging messages |
| **Exceptions** | ⚠️ | Unhandled exceptions with tracebacks |

#### Extended Events

| Type | Icon | Description |
|------|------|-------------|
| **Cache** | 🟠 | Cache operations (hits, misses, sets) |
| **Commands** | 🟣 | Management command executions |
| **Models** | 🔵 | ORM signals (post_save, post_delete) |
| **HTTP Client** | 🩷 | Outgoing HTTP requests (httpx, requests) |
| **Dumps** | 🟢 | Custom debug dumps via `orbit.dump()` |
| **Mail** | 💜 | Email sending operations |
| **Signals** | ⚡ | Django signals |

#### Phase 3 Events (v0.5.0+)

| Type | Icon | Description |
|------|------|-------------|
| **Jobs** | ⏰ | Background jobs (Celery, Django-Q, RQ, APScheduler) |
| **Redis** | 🔴 | Redis operations (GET, SET, DEL, HGET, etc.) |
| **Gates** | 🛡️ | Permission/authorization checks |

#### Phase 4 Events (v0.6.0+)

| Type | Icon | Description |
|------|------|-------------|
| **Transactions** | 🔷 | Database `atomic()` blocks — commits and rollbacks with duration |
| **Storage** | 📦 | File storage operations — save, open, delete (local + S3) |

### Search

Use the search bar in the header to find specific entries:

- **By UUID**: Paste a specific Entry ID to jump to it
- **By Content**: Text search searches inside the JSON payload

### Stats Panel

When viewing **All Events**, a collapsible stats panel shows key metrics:

- Request count
- Error rate
- Slow queries percentage
- Mini charts

For detailed analytics, click the **Stats** button to open the [Stats Dashboard](stats.md).

### Export

Export data for offline analysis:

- **Export All**: Download button streams all entries as JSON
- **Single Entry**: Open any entry and use the header link

## Detailed Views

Click on any row in the feed to open the **Detail Panel**.

### JSON Payload

The core of every entry is its JSON payload. Orbit renders this with syntax highlighting, making it easy to explore complex data structures.

### Related Entries

Orbit groups events by "Family". For example, if an HTTP Request triggers 5 SQL Queries and 1 Log message, they share the same `family_hash`.

When viewing the Request, you'll see the queries and logs listed in the "Related Entries" section.

### Duplicate Queries (N+1 Detection)

When viewing a query marked as duplicate, a special section appears showing all queries with the same SQL. This helps debug N+1 query issues:

- Click any duplicate to view its details
- Tips for optimization (`select_related()`, `prefetch_related()`) are shown

## Actions

| Action | Description |
|--------|-------------|
| **Pause/Resume** | Stop live feed to inspect entries |
| **Clear All** | Purge all recorded data |
| **Refresh** | Manually reload current view |
| **Stats** | Open the Stats Dashboard |

## Keyboard Shortcuts

- **Escape**: Close detail panel
- **Click outside**: Close detail panel

## Next Steps

- [Stats Dashboard](stats.md)
- [Configuration](configuration.md)
- [Security](security.md)
