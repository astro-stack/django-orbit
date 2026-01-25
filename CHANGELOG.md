# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.6.3] - 2026-01-25

### Added

- **Plug-and-Play Module System**: Each watcher/module now operates independently
  - If one module fails to initialize, others continue working normally
  - Failed modules are logged but don't crash the application
  - Module status is tracked and available for diagnostics
  
- **Health Dashboard** (`/orbit/health/`): New diagnostics page showing module status
  - Visual indicators: Green (healthy), Red (failed), Yellow (disabled)
  - Expandable error details with full traceback
  - Summary cards for total/healthy/failed/disabled counts
  - Instructions for fixing failed modules
  
- **New API Functions**:
  - `orbit.get_watcher_status()` - Get status of all watchers
  - `orbit.get_installed_watchers()` - List of active watcher names  
  - `orbit.get_failed_watchers()` - Dict of failed watchers with error messages
  
- **Configuration**:
  - Added `WATCHER_FAIL_SILENTLY` setting (default: True)
    - When True, module failures are logged but app continues
    - When False, failures are re-raised for debugging

- **Dashboard Updates**:
  - New "Health" button in top navigation bar
  - Fixed missing icons for Transaction and Storage types in feed
  - Transactions now use `git-branch` icon (teal color)
  - Storage now uses `archive` icon (sky color)

### Fixed

- **Static files bug**: Removed `listdir` from storage watcher patching
  - This was causing `NotADirectoryError` when Django's staticfiles handler tried to list directory contents
- **Closure bug in storage watcher**: Fixed variable capture issue where `delete` and `exists` methods were incorrectly bound
  - Used factory function pattern to properly capture `method_name` and `original_method`
- **Test isolation**: Added `force=True` parameter to `install_storage_watcher()` for testing scenarios
- **Exists test**: Fixed query to use `-created_at` ordering since UUIDs don't preserve insertion order

### Technical

- New `orbit/health.py` module with `ModuleRegistry` class
- `_install_watcher_safely()` helper for isolated module initialization
- `create_patched_method()` factory to avoid Python closure bugs in loops

## [0.6.2] - 2026-01-23

### Fixed

- **Critical crash with `ATOMIC_REQUESTS=True`** (Issue #5)
  - Fixed `OrbitAtomicWrapper` compatibility with decorator usage
  - Added thread safety for nested atomic blocks

## [0.6.1] - 2026-01-22

### Fixed
- **Missing migration** for entry types added in v0.4.0-v0.6.0 (Issue #3)
  - Added migration 0004 with `mail`, `signal`, `redis`, `gate`, `transaction`, `storage` types
- **Command watcher breaking interactive commands** like `collectstatic` (Issue #4)
  - Removed stdout/stderr redirection that prevented user input
  - Commands now execute normally while still being recorded

## [0.6.0] - 2026-01-22

### Added
- **Transaction Watcher**: Track database transaction blocks
  - Intercepts `transaction.atomic()` context managers
  - Records commit/rollback status
  - Captures transaction duration in milliseconds
  - Logs exceptions that trigger rollbacks
- **Storage Watcher**: Monitor file storage operations
  - Tracks `save`, `open`, `delete`, `exists` operations
  - Works with `FileSystemStorage` (default)
  - Supports `S3Boto3Storage` (django-storages)
  - Records file path, backend name, and operation duration
- **Dashboard Updates**:
  - New "Transactions" filter with teal icon (layers)
  - New "Storage" filter with sky-blue icon (archive)
  - Summary formatting for transaction status (✓/✗ icons)

### Configuration
- Added `RECORD_TRANSACTIONS` setting (default: True)
- Added `RECORD_STORAGE` setting (default: True)

### Technical
- `OrbitAtomicWrapper` class for safe atomic block interception
- Storage patching via `create_patched_base()` factory to avoid closure issues
- Added `tests/test_transactions.py` and `tests/test_storage.py`

## [0.5.0] - 2025-12-19

### Added
- **Jobs Watcher**: Track background job executions
  - Celery integration via signals
  - Django-Q integration via signals
  - RQ (Redis Queue) integration via monkey-patching
  - APScheduler integration with event listeners
  - django-celery-beat integration for periodic tasks
- **Redis Watcher**: Capture Redis operations
  - Tracks GET, SET, DEL, HGET, HSET, LPUSH, RPUSH, etc.
  - Records key, operation type, duration, and result size
- **Gates/Permissions Watcher**: Monitor authorization checks
  - Tracks permission checks via Django's ModelBackend
  - Records user, permission, object, result (granted/denied)
- **Stats Dashboard**: New dedicated analytics page at `/orbit/stats/`
  - Real-time Apdex score calculation
  - Response time percentiles (P50, P75, P95, P99)
  - Throughput metrics (requests/min or /hr)
  - Error rate tracking with threshold visualization
  - Database performance analytics (slow queries, N+1 detection)
  - Cache hit rate monitoring with sparkline charts
  - Background job success rate and failure tracking
  - Permission check analytics with top denied permissions
  - Time range filters (1h, 6h, 24h, 7d)
  - ApexCharts for interactive visualizations
- **Duplicate Query Navigation**: Click on duplicate queries in entry details to navigate between related N+1 queries
- **Dashboard Improvements**:
  - Scrollable sidebar for many event types
  - Stats panel only visible for "All Events" filter
  - Loading spinner in detail panel
  - New event type icons for Jobs, Redis, Gates

### Configuration
- Added `RECORD_JOBS` setting (default: True)
- Added `RECORD_REDIS` setting (default: True)
- Added `RECORD_GATES` setting (default: True)

### Technical
- Added `tests/test_watchers_v050.py` with unit tests for new watchers
- Added `generate_historical_data()` to demo.py for stats visualization
- Retry logic for SQLite database lock issues

## [0.4.0] - 2025-12-18

### Added
- **Mail Watcher**: Capture all outgoing emails sent via `django.core.mail`
  - Records subject, from, to, cc, bcc, body, and attachments
  - Supports HTML email alternatives
- **Signals Watcher**: Track Django signal dispatches
  - Records signal name, sender, receivers count, and kwargs
  - Configurable `IGNORE_SIGNALS` to filter noisy signals (pre_init, post_init by default)
- **Dashboard Updates**:
  - New "Mail" filter with fuchsia icon
  - New "Signals" filter with yellow icon
  - Entry detail panel support for new types
- **Configuration**:
  - Added `RECORD_MAIL` setting (default: True)
  - Added `RECORD_SIGNALS` setting (default: True)
  - Added `IGNORE_SIGNALS` list for filtering

### Fixed
- Added missing `filter_sensitive_data` utility function
- Improved signal name detection for better developer context

## [0.3.0] - 2025-12-16

### Added
- **Dashboard Security**: Configurable `AUTH_CHECK` to restrict access
- **Data Management**: `orbit_prune` management command with age/importance filtering
- **Search & Filtering**: Full-text search, UUID lookup
- **Export**: "Export JSON" button and bulk export endpoint

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
