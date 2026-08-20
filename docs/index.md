# Django Orbit Documentation

Current maintenance release: **v0.12.1**.

Welcome to the Django Orbit documentation. This guide covers installation, configuration, usage, and customization.

[![Star on GitHub](https://img.shields.io/github/stars/astro-stack/django-orbit?style=social)](https://github.com/astro-stack/django-orbit)

Looking for the product overview and visual landing page? Visit the [Django Orbit product site](https://labs.wearehik.com/django-orbit/).

## Table of Contents

1. [Installation](installation.md)
2. [Quick Start](quickstart.md)
3. [Configuration](configuration.md)
4. [Running the Demo](running-demo.md)
5. [Dashboard Guide](dashboard.md)
6. [Stats Dashboard](stats.md)
7. [AI/LLM Watcher](llm-watcher.md) - New in v0.12.0
8. [MCP Server](mcp.md)
9. [Storage Backends](storage-backends.md)
10. [Agent-Native Roadmap](roadmap.md)
11. [API Reference](api.md)
12. [Customization](customization.md)
13. [Security](security.md)
14. [Troubleshooting](troubleshooting.md)

## What is Django Orbit?

Django Orbit is an AI agent-native observability and debugging tool for Django applications. Unlike Django Debug Toolbar, which injects HTML into your templates, Orbit runs on its own isolated URL and exposes structured runtime evidence through both a human dashboard and MCP tools for AI assistants.

!!! info "Orbit Pro founder waitlist"
    Django Orbit remains MIT-licensed. [Orbit Pro](https://labs.wearehik.com/django-orbit/pro/)
    is the planned self-hosted verification layer for release comparison, saved
    investigations and evidence-backed validation of agent-assisted changes.

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
| Modern UI | Basic | Focused dashboard |
| Agent-native MCP tools | No | Yes |
| Ticket-to-fix handoff bundles | No | Yes |

### What's New in v0.13.0

- **Honest query semantics**: duplicate SQL is evidence, not automatic proof of
  an N+1 issue.
- **Deterministic N+1 analysis**: versioned signatures, parameter variation,
  callsite correlation, confidence and explicit limitations.
- **Agent-ready findings**: MCP responses distinguish classified candidates
  from duplicate-only historical entries.
- **Storage guards**: request, exception and bulk-query paths check that Orbit
  storage exists before writing.
- **Configuration Center**: inspect effective settings and generate a safe,
  validated `ORBIT_CONFIG` block without runtime mutation.
- **Honest database stats and demo corpus**: duplicate-only requests, N+1
  requests and findings are separate, with reproducible examples for each.

### What's New in v0.12.0

- **AI/LLM watcher**: Orbit records provider, model, operation, latency, status, token usage and tool-call names for supported OpenAI and Anthropic SDK calls.
- **Metadata-first defaults**: prompts, completions and tool-call arguments are not captured unless explicitly enabled.
- **Release safeguards**: local release verification checks version consistency, changelog, package build, Twine metadata and strict docs.
- **Production safety guidance**: docs now spell out conservative MCP and LLM capture settings for shared environments.

### What's New in v0.11.0

- **Endpoint investigation**: `investigate_endpoint` summarizes endpoint health across recent requests, errors, slow requests, query signals and exception groups.
- **Regression comparison**: `compare_endpoint_windows` compares current endpoint behavior against a baseline window to detect regressions.
- **Agent safety tools**: `preview_masked_entry`, `find_sensitive_payload_risks` and `list_agent_safe_fields` make MCP exposure auditable before sharing runtime context.
- **Higher-level triage**: `find_n_plus_one_candidates` and `summarize_exception_groups` help agents move from noisy telemetry to ranked daily debugging targets.
- **Daily developer triage**: `daily_health_brief` creates a local morning brief of top exceptions, failed jobs, slow queries, N+1 candidates and warning logs.
- **Release risk brief**: `generate_release_risk_brief` flags blocker/caution signals before deploys.
- **PR context generation**: `generate_pr_context` turns Orbit evidence into PR-ready summaries, test plans and release-risk notes.
- **Copy/paste agent prompts**: `create_incident_bundle(..., format="prompt")` produces safe prompts for Claude, Codex and Cursor when MCP is unavailable.
- **MCP workflow expansion**: all new tools are available through MCP and honor the existing `MCP_ENABLED` safety gate.
- **Codex and Claude debugging demo**: the docs now include a practical ticket-to-test-to-fix workflow using Orbit context.

### Agent-Native Debugging Workflow

Orbit is most useful when it turns a vague symptom into a focused handoff:

```text
ticket or runtime error
  -> build_debug_brief(...)
  -> create_incident_bundle(...)
  -> propose_fix_hypotheses(...)
  -> propose_test_plan(...)
  -> developer or coding-agent fix
```

The local dashboard remains the first surface for humans. MCP is the optional agent surface: read-only tools that query captured runtime evidence, apply masking and limits, and return compact context that can be used by Codex, Claude, Cursor, Windsurf or another MCP-compatible assistant.

### What's New in v0.10.0

- **Agent-native debugging base**: Orbit now exposes high-level MCP tools that help AI assistants move from ticket or runtime error to evidence, fix hypotheses, test plans and incident bundles.
- **Safe MCP serialization**: agent-facing output masks sensitive keys, can omit payloads, bounds result sizes and truncates oversized payloads deterministically.
- **Request and exception investigation**: `investigate_request` and `investigate_exception_group` summarize timelines, related signals, likely causes and next actions.
- **Ticket-to-evidence workflow**: `build_debug_brief`, `create_incident_bundle`, `propose_fix_hypotheses` and `propose_test_plan` support daily developer and coding-agent workflows.
- **MCP kill switch**: `MCP_ENABLED: False` now blocks all MCP tools with a stable disabled response.

Telemetry opt-in is intentionally not included in v0.10.0. It is planned for a separate future release.

### What's New in v0.9.1

- **MCP server runtime fix**: `orbit_mcp` now works correctly with FastMCP's async loop by allowing Django's synchronous ORM in this local stdio server context.
- **Exception grouping fix**: exceptions without a fingerprint are no longer hidden from the grouped Exceptions view.

### What's New in v0.9.0

- **Sensitive-data masking**: recursive, case-insensitive masking for tokens, passwords, API keys, cookies and related values.
- **Query EXPLAIN**: inspect query plans from the query detail panel.
- **Request waterfall**: see request query timing as a timeline.
- **Tags and tag search**: attach and filter entries by operational tags.
- **Exception grouping**: group identical exceptions by fingerprint.
- **Dashboard redesign**: grouped sidebar, All Events, compact KPI strip, keyboard navigation and onboarding.
- **Faster Stats page**: heavy sections now lazy-load.

### What's New in v0.8.1

- **HTML Email Preview**: Emails sent with `EmailMultiAlternatives` now show a **Plain text / HTML preview** tab switcher in the dashboard. The HTML body renders in a sandboxed iframe - great for testing email templates. See [Email Preview](dashboard.md#mail-html-preview).
- **MySQL `max_allowed_packet` fix**: New `BULK_CREATE_BATCH_SIZE` config key prevents `OperationalError (2006, 'Server has gone away')` on requests that trigger thousands of SQL queries. See [`BULK_CREATE_BATCH_SIZE`](configuration.md#bulk_create_batch_size).

### What's New in v0.8.0

- **External Storage Backends**: Route all Orbit writes to a dedicated Django database alias - keep telemetry out of your app's main database. See [Storage Backends](storage-backends.md).

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
