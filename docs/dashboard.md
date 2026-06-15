# Dashboard Guide

The Django Orbit dashboard is your mission control center, available at `/orbit/` (by default). It provides a real-time, unified view of your application's telemetry.

## Navigation & Filtering

### Sidebar

**All Events** sits at the top as a standalone item — a unified feed of everything. Below
it, entry types are organized into three **collapsible groups** so you're not faced with a
flat list of every type at once. The group containing the type you're viewing opens
automatically. The badge on each item shows its captured count; the **Exceptions** badge
turns red when non-zero.

#### Core

| Type | Description |
|------|-------------|
| **Requests** | HTTP requests (method, path, status, duration) |
| **Queries** | SQL queries with N+1 detection |
| **Exceptions** | Unhandled exceptions with tracebacks |
| **Logs** | Python logging messages |

#### Infrastructure

| Type | Description |
|------|-------------|
| **Cache** | Cache operations (hits, misses, sets) |
| **Redis** | Redis operations (GET, SET, DEL, HGET, etc.) |
| **HTTP Client** | Outgoing HTTP requests (httpx, requests) |
| **Mail** | Email sending operations |
| **Storage** | File storage operations — save, open, delete (local + S3) |

#### Application

| Type | Description |
|------|-------------|
| **Models** | ORM signals (post_save, post_delete) |
| **Jobs** | Background jobs (Celery, Django-Q, RQ, APScheduler) |
| **Commands** | Management command executions |
| **Signals** | Django signals |
| **Gates** | Permission/authorization checks |
| **Transactions** | Database `atomic()` blocks — commits and rollbacks with duration |
| **Dumps** | Custom debug dumps via `orbit.dump()` |

!!! tip "First-run tour"
    The first time you open the dashboard, a short onboarding overlay highlights the layout
    and shortcuts. Dismiss it with **Got it** — reopen any time from the **?** button in the
    top bar.

### Search

Use the search bar in the header to find specific entries:

- **By UUID**: Paste a specific Entry ID to jump to it
- **By Content**: Text search searches inside the JSON payload

### Metrics strip

When viewing **All Events**, a compact one-line metrics strip sits above the feed with
the numbers that matter for debugging: requests/hr, queries/hr, average response time, and
error-focused counts (**errors**, **slow** queries, **N+1** duplicates). For full
analytics, use the **Full analytics** link or the **Stats** button to open the
[Stats Dashboard](stats.md).

### Export

Open any entry and use the **download** link in the detail panel header to export it as
JSON — handy for sharing a specific request or exception.

## Detailed Views

Click on any row in the feed to open the **Detail Panel**.

### JSON Payload

The core of every entry is its JSON payload. Orbit renders this with syntax highlighting, making it easy to explore complex data structures.

### Related Entries

Orbit groups events by "Family". For example, if an HTTP Request triggers 5 SQL Queries and 1 Log message, they share the same `family_hash`.

When viewing the Request, you'll see the queries and logs listed in the "Related Entries" section.

### Mail HTML Preview

When an email is sent via `EmailMultiAlternatives` with an HTML alternative, the Mail detail panel shows two tabs:

- **Plain text** — the raw text body
- **HTML preview** — the HTML body rendered in a sandboxed `<iframe>`

The iframe uses the `sandbox` attribute, so external scripts and forms are blocked. This is useful for testing and visually reviewing HTML email templates without sending real emails.

Plain-text-only emails (sent via `EmailMessage`) display the body directly with no tab switcher.

!!! note
    HTML bodies are capped at **100 KB** during capture. Templates larger than this will be truncated.

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

With the detail panel open:

- **`j`** / **`↓`**: Next entry in the current feed
- **`k`** / **`↑`**: Previous entry
- **`Escape`**: Close the detail panel
- **Click outside**: Close the detail panel

The panel header also has prev/next buttons and a position indicator (e.g. `3/25`).

## Design system

The dashboard follows a documented design system — see
[`DESIGN.md`](https://github.com/astro-stack/django-orbit/blob/main/DESIGN.md) in the
repository for tokens, components and UI principles.

## Next Steps

- [Stats Dashboard](stats.md)
- [Configuration](configuration.md)
- [Security](security.md)
