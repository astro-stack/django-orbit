# Django Orbit Documentation

Welcome to the Django Orbit documentation. This guide covers installation, configuration, usage, and customization.

[![Star on GitHub](https://img.shields.io/github/stars/astro-stack/django-orbit?style=social)](https://github.com/astro-stack/django-orbit)

## Table of Contents

1. [Installation](installation.md)
2. [Quick Start](quickstart.md)
3. [Configuration](configuration.md)
4. [Running the Demo](running-demo.md)
5. [Dashboard Guide](dashboard.md)
6. [Stats Dashboard](stats.md)
7. [MCP Server](mcp.md) ✨ **New in v0.7.0**
8. [Storage Backends](storage-backends.md) ✨ **New in v0.8.0**
9. [API Reference](api.md)
10. [Customization](customization.md)
11. [Security](security.md)
12. [Troubleshooting](troubleshooting.md)

## What is Django Orbit?

Django Orbit is a debugging and observability tool for Django applications. Unlike Django Debug Toolbar, which injects HTML into your templates, Orbit runs on its own isolated URL and provides a modern, reactive dashboard for monitoring your application.

### Key Concepts

- **OrbitEntry**: The central model that stores all telemetry data
- **Middleware**: Captures HTTP requests and coordinates recording
- **Watchers**: Specialized components for SQL, logging, jobs, Redis, permissions, etc.
- **Family Hash**: Links related events (e.g., all queries for one request)

### Why Orbit?

| Feature | Django Debug Toolbar | Django Orbit |
|---------|---------------------|--------------|
| DOM Injection | Yes | No |
| Works with APIs | Limited | Full |
| Works with SPAs | Limited | Full |
| Persistent Storage | No | Yes |
| Historical Data | No | Yes |
| Stats & Analytics | No | Yes |
| Modern UI | Basic | Space-themed |

### What's New in v0.8.0

- **External Storage Backends**: Route all Orbit writes to a dedicated Django database alias — keep telemetry out of your app's main database. See [Storage Backends](storage-backends.md).

### What's New in v0.7.0

- **MCP Server**: Connect Claude, Cursor, Windsurf, or any MCP-compatible AI assistant to your live Django telemetry. Ask questions like *"Why is this endpoint slow?"* directly against real data. See [MCP Server](mcp.md).

### What's New in v0.6.0

- **Transaction Watcher**: Track database transactions (commits/rollbacks)
- **Storage Watcher**: Monitor file operations (save, open, delete, exists)
- **Improved Summaries**: More informative entry summaries with duration and sizes
- **Enhanced Analytics**: Transaction and storage metrics in Stats Dashboard

### What's New in v0.5.0

- **Jobs Watcher**: Track Celery, Django-Q, RQ, APScheduler tasks
- **Redis Watcher**: Monitor Redis operations
- **Gates Watcher**: Audit permission checks
- **Stats Dashboard**: Apdex, percentiles, interactive charts
- **N+1 Navigation**: Click through duplicate queries

## Getting Help

- [GitHub Issues](https://github.com/astro-stack/django-orbit/issues)
- [GitHub Discussions](https://github.com/astro-stack/django-orbit/discussions)
- [Contributing Guide](contributing.md)
