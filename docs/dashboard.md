# Dashboard Guide

The Django Orbit dashboard is your mission control center, available at `/orbit/` (by default). It provides a real-time, unified view of your application's telemetry.

!!! info "Works offline"
    The dashboard is fully self-contained. Scripts, styles, icons and fonts are
    bundled with the package and served from your own static files, so it needs
    no CDN or internet access (run `collectstatic` in production). It also works under a strict
    [Content Security Policy](security.md#content-security-policy).

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
| **AI/LLM** | Provider/model/token metadata, latency, errors and tool-call names |
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

The compact scope controls filter by time range (`all`, `15m`, `1h`, `24h`),
path substring on request and exception entries whose stored JSON path value is
a string (SQLite, PostgreSQL and MySQL are supported; other database vendors
fail closed), method on request and exception stored fields, request status
class, and minimum duration using each entry's own duration value across entry types.
Status applies only to requests. These filters do not expand through a request
family or apply request fields to related queries. Existing type, search, tag
and request-family filters remain available. Controls are drafts until **Apply**;
search applies immediately with the current controls. A successful response
updates the feed and scoped metrics together and writes canonical filters plus
the effective page to the URL. Back/forward restores a scope without adding a
history entry. Invalid filters or failed initial/history navigation preserve the
last successful feed and metrics and suspend polling until **Apply** or **Clear**
successfully establishes a scope.

Pagination preserves the selected type, search, tag, request family and
structured filters. The feed accepts `page` and `per_page` parameters:
malformed values fall back to page 1 and 25 rows; valid page sizes are clamped
to 1..100. Repeated structured-filter query keys are rejected rather than
silently collapsed.

**Pause feed** pauses browser polling, not server-side recording. Recording
remains controlled by Django's `ORBIT_CONFIG` and watcher setup. Manual refresh
works while polling is paused. Failed loads show a retry action; feed failures
keep the last loaded rows, and late responses cannot overwrite a newer selection.

### Scoped metrics

The compact metrics strip remains visible for every feed and uses the same
confirmed filter scope and time window as its rows. It distinguishes failed
requests from exceptions, displays a dash when no request duration is available,
and labels duplicate-query counts without claiming they prove an N+1 pattern.
The sidebar badges are recorded totals, not filtered counts. For full analytics,
use the **Full analytics** link or the **Stats** button to open the
[Stats Dashboard](stats.md).

### Export

Open any entry and use the **download** link in the detail panel header to export it as
JSON — handy for sharing a specific request or exception.
The detail panel includes an **Investigation guide** when the entry has enough
recorded fields to explain a next step. It identifies the request method/path/status,
query signal, or log level without claiming a root cause. Use the related entries,
query timeline, and Stats views to verify the signal before changing code.

Entries with a `family_hash` or exception fingerprint also show a **Copy fix handoff**
action. It combines the safe incident prompt with ranked fix hypotheses and a
regression-test plan, so you can paste a useful starting point into Codex, Claude,
Cursor or another coding agent even when MCP is not connected. It does not edit code
or claim a root cause; verify the evidence against the repository first.

## Detailed Views

Signal recording is disabled by default because framework lifecycle dispatches
can overwhelm the event feed. Enable `RECORD_SIGNALS` when useful; common ORM
lifecycle signals remain filtered by `IGNORE_SIGNALS`. The separate model
watcher continues recording model changes.

Click on any row in the feed to open the **Detail Panel**.

The **Copy fix handoff** action fetches the masked handoff from the server and
copies it using the browser clipboard API or a local fallback. **Preview
handoff** opens the exact text so you can inspect it before sharing it with an
agent. If both copy methods are blocked by the browser, open the preview and
select the text manually.

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
- **Click another event**: Replace the open detail with that event in one click
- **Click the selected event again**: Close the detail panel
- **Click outside the panel and event rows**: Close the detail panel

The panel header also has prev/next buttons and a position indicator (e.g. `3/25`).

## Design system

The dashboard follows a documented design system — see
[`DESIGN.md`](https://github.com/astro-stack/django-orbit/blob/main/DESIGN.md) in the
repository for tokens, components and UI principles.

## Next Steps

- [Stats Dashboard](stats.md)
- [Configuration](configuration.md)
- [Security](security.md)
