# Dashboard Guide

The Django Orbit dashboard is your mission control center, available at `/orbit/` (by default). It provides a real-time, unified view of your application's telemetry.

## Navigation & Filtering

### Sidebar
The sidebar groups events by type. The number in the badge indicates the total count of captured events for that type.

- **All Events**: A unified feed of everything happening in your app.
- **Requests**: HTTP requests (method, path, status, duration).
- **Queries**: SQL queries (SQL, params, duration, N+1 detection).
- **Logs**: Python logging messages (INFO, WARNING, ERROR, etc.).
- **Exceptions**: Unhandled exceptions with full tracebacks.
- **Commands**: Management command executions (`manage.py`).
- **Cache**: Cache operations (hits, misses, sets, deletes).
- **Models**: ORM Signals (post_save, post_delete).
- **HTTP Client**: Outgoing HTTP requests (httpx, requests).
- **Dumps**: Custom debug dumps using `orbit.dump()`.

### Search
Use the search bar in the header to find specific entries:
- **By UUID**: Paste a specific Entry ID to jump to it.
- **By Content**: Text search searches inside the JSON payload of entries.

### Export
You can export data for offline analysis:
- **Export Filtered**: Click the "Download" icon in the sidebar to stream all currently filtered entries as a JSON array.
- **Single Entry**: Open any entry and click "Export JSON" in the detail panel header.

## Detailed Views

Click on any row in the feed to open the **Detail Panel**.

### JSON Payload
The core of every entry is its JSON payload. Orbit renders this with syntax highlighting and collapsible sections, making it easy to explore complex data structures.

### Related Entries
Orbit groups events by "Family". For example, if an HTTP Request triggers 5 SQL Queries and 1 Log message, they will all share the same `family_hash`.
When viewing the Request, you will see the queries and logs listed in the "Related Entries" section, allowing you to trace the full lifecycle of an operation.

## Actions

- **Pause/Resume**: Stop the live feed to inspect specific entries without rows shifting.
- **Clear All**: Purge all recorded data from the database.
- **Refresh**: Manually reload the current view.
