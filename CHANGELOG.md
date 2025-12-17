# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Unreleased (v0.3.0) - Reliability & Security
- **Dashboard Security**: Added configurable `AUTH_CHECK` to restrict access.
- **Data Management**: Added `orbit_prune` management command with age/importance filtering.
- **Search & Filtering**:
    - Added search bar to Dashboard.
    - Implemented full-text search for entry payloads.
    - Added direct UUID lookup.
- **Export**:
    - Added "Export JSON" button to entry details.
    - Implemented `/orbit/export/<uuid>/` endpoint. old data.

## [0.2.0] - 2025-12-16

### Added
- **New Watchers**:
  - `Commands`: Track management commands execution
  - `Cache`: Monitor cache operations (get, set, delete)
  - `Models`: Track model signals (save, delete) and lifecycle
  - `HTTP Client`: Capture outgoing HTTP requests (httpx, requests)
- **Helpers**:
  - `dump()`: Helper for manual variable inspection (Laravel Telescope style)
  - `log()`: Helper for direct logging to Orbit
- **Dashboard**:
  - Complete pagination system (25 entries/page)
  - New entry types support with distinct icons and colors
  - "Dumps" section in sidebar
- **Configuration**:
  - Added `RECORD_*` settings for new watchers
  - Added `RECORD_DUMPS`

### Fixed
- Fixed HTMX processing for dynamic content loading
- Fixed pagination state persistence during auto-refresh
- Sidebar ordering (alphabetical)
- "Load More" button issues on long lists
- Accurate cache hit/miss detection using sentinel object

## [0.1.0] - 2024-12-01

### Added
- Initial release of Django Orbit
- `OrbitEntry` model for storing telemetry data
- `OrbitMiddleware` for capturing HTTP requests/responses
- SQL query recording with duplicate and slow query detection
- `OrbitLogHandler` for Python logging integration
- Exception tracking with full traceback capture
- Modern dashboard UI with space theme
- HTMX-powered live feed with 3-second polling
- Alpine.js reactive slide-over detail panel
- Entry grouping via `family_hash`
- Configurable ignore paths
- Sensitive data sanitization
- Automatic cleanup of old entries

### Technical
- Django 4.0+ support
- Python 3.9+ support
- Tailwind CSS via CDN (no build step required)
- HTMX for partial page updates
- Alpine.js for reactive UI components
- Lucide icons
