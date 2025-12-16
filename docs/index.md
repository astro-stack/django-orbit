# Django Orbit Documentation

Welcome to the Django Orbit documentation. This guide covers installation, configuration, usage, and customization.

## Table of Contents

1. [Installation](installation.md)
2. [Quick Start](quickstart.md)
3. [Configuration](configuration.md)
4. [Running the Demo](running-demo.md)
5. [Dashboard Guide](dashboard.md)
6. [API Reference](api.md)
7. [Customization](customization.md)
8. [Security](security.md)
9. [Troubleshooting](troubleshooting.md)

## What is Django Orbit?

Django Orbit is a debugging and observability tool for Django applications. Unlike Django Debug Toolbar, which injects HTML into your templates, Orbit runs on its own isolated URL and provides a modern, reactive dashboard for monitoring your application.

### Key Concepts

- **OrbitEntry**: The central model that stores all telemetry data
- **Middleware**: Captures HTTP requests and coordinates recording
- **Recorders**: Specialized components for SQL, logging, etc.
- **Family Hash**: Links related events (e.g., all queries for one request)

### Why Orbit?

| Feature | Django Debug Toolbar | Django Orbit |
|---------|---------------------|--------------|
| DOM Injection | Yes | No |
| Works with APIs | Limited | Full |
| Works with SPAs | Limited | Full |
| Persistent Storage | No | Yes |
| Historical Data | No | Yes |
| Modern UI | Basic | Space-themed |

## Getting Help

- [GitHub Issues](https://github.com/your-org/django-orbit/issues)
- [GitHub Discussions](https://github.com/your-org/django-orbit/discussions)
- [Contributing Guide](../CONTRIBUTING.md)
