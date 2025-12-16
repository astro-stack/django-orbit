# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2024-XX-XX

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
