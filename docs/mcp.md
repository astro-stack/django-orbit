# MCP Server — AI Assistant Integration

Django Orbit exposes your app's telemetry as an [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server. Connect Claude, Cursor, Windsurf, or any MCP-compatible AI assistant and ask questions directly against your app's live observability data.

!!! tip "New in v0.11.0"
    Orbit now includes endpoint investigation, daily health briefs and release risk briefs on top of the v0.10 request/exception/ticket workflows.

## Installation

```bash
pip install django-orbit[mcp]
```

The `[mcp]` extra installs the official `mcp` Python SDK (`mcp>=1.0,<3.0`). The core `django-orbit` package has no dependency on it.

### Supported SDK versions

Orbit works with both major versions of the MCP Python SDK and picks the right server class at runtime:

| SDK | Server class used |
| --- | --- |
| `mcp` 1.x | `mcp.server.fastmcp.FastMCP` |
| `mcp` 2.x | `mcp.server.mcpserver.MCPServer` (renamed from `FastMCP`) |

CI runs the full test suite, including in-process protocol tests (`initialize`, `tools/list`, `tools/call`), against both. Pin `mcp<2` or `mcp<3` yourself if you need to hold a version.

### Tool annotations

Every Orbit tool only reads telemetry, so each one is advertised with MCP tool annotations `readOnlyHint=true`, `destructiveHint=false`, `idempotentHint=true` and `openWorldHint=false`. Clients can use these hints to skip confirmation prompts. Annotations are only sent when the installed SDK provides `ToolAnnotations`.

## Setup

Add the MCP server configuration to your AI assistant:

=== "Claude Desktop"

    Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

    ```json
    {
      "mcpServers": {
        "django-orbit": {
          "command": "python",
          "args": ["manage.py", "orbit_mcp"],
          "cwd": "/path/to/your/django/project"
        }
      }
    }
    ```

=== "Cursor"

    Edit `.cursor/mcp.json` in your project:

    ```json
    {
      "mcpServers": {
        "django-orbit": {
          "command": "python",
          "args": ["manage.py", "orbit_mcp"],
          "cwd": "/path/to/your/django/project"
        }
      }
    }
    ```

=== "Windsurf"

    Edit `~/.windsurfrc`:

    ```json
    {
      "mcpServers": {
        "django-orbit": {
          "command": "python",
          "args": ["manage.py", "orbit_mcp"],
          "cwd": "/path/to/your/django/project"
        }
      }
    }
    ```

The MCP server launches on-demand using stdio transport — no extra process to keep running.

## Available Tools

The MCP server exposes raw telemetry tools plus higher-level agentic investigation tools to your AI assistant:

| Tool | What it returns |
|------|----------------|
| `get_recent_requests` | Last N HTTP requests with status, path, duration |
| `get_slow_queries` | SQL queries above threshold, sorted by duration |
| `get_exceptions` | Exceptions in a time window with full traceback |
| `get_n1_patterns` | Requests where N+1 duplicate queries were detected |
| `get_request_detail` | Versioned, metadata-only evidence for one request via `family_hash`, capped by `MCP_MAX_LIMIT` |
| `summarize_request_family` | Compact, metadata-only counts and observed signals for one `family_hash`; never returns payloads |
| `get_capture_health` | Metadata-only capture readiness, safe flags and watcher state through Evidence API |
| `search_entries` | Keyword search across all event types |
| `get_stats_summary` | Error rate, avg response time, cache hit rate |
| `audit_mcp_exposure` | Effective MCP safety policy: payload inclusion, masking and limits |
| `preview_masked_entry` | One entry as an agent will see it, with masked payload and detected risk paths |
| `find_sensitive_payload_risks` | Recent entries whose payload keys look sensitive, without raw values |
| `list_agent_safe_fields` | Allowlisted common fields and payload policy for one entry type |
| `investigate_request` | Diagnosis for one `family_hash`: timeline, signals, queries, hypotheses and next actions |
| `investigate_exception_group` | Blast-radius summary for one exception fingerprint |
| `create_incident_bundle` | On-demand JSON, Markdown or prompt handoff bundle from a request, fingerprint or ticket text |
| `build_debug_brief` | Match natural-language ticket/error text to recent Orbit evidence |
| `investigate_endpoint` | Endpoint health summary with error rate, slowest requests, query analysis and exception groups |
| `compare_endpoint_windows` | Current-vs-baseline endpoint comparison for regression, stable, improving or insufficient-data calls |
| `find_n_plus_one_candidates` | Ranked recent requests with duplicate-query/N+1 evidence |
| `summarize_exception_groups` | Recent exception fingerprints with counts, affected paths and representatives |
| `daily_health_brief` | Local daily triage of exceptions, failed jobs, slow queries, N+1 candidates and warning logs |
| `generate_release_risk_brief` | Pre-release blocker/caution summary from recent runtime evidence |
| `generate_pr_context` | PR-ready title, evidence, hypotheses, test plan and release-risk notes |
| `propose_fix_hypotheses` | Ranked fix directions from captured evidence; does not edit code |
| `propose_test_plan` | Suggested regression/performance tests for the observed issue |


## Compact Request Context

`summarize_request_family(family_hash, limit=None)` summarizes only metadata from `orbit.evidence.read_family_evidence`. It always omits raw payloads, messages, SQL, tags and entry summaries, even with `MCP_INCLUDE_PAYLOADS=True`. It returns no hypotheses or absence-of-error verdicts.

The response reuses `schema_version="orbit.evidence.v1"` and the Evidence envelope fields `status`, `reason`, `family_hash`, `count`, `truncated` and `evidence_quality`, with `resource="request_family_summary"`. Evidence quality status and warnings are preserved. Recovery actions respect the effective MCP cap: retries never exceed it; once reached, `review_mcp_limit` asks for a configuration review, or `review_family_scope` indicates the Evidence contract maximum has been reached. For `unavailable`, `invalid` or `not_found` responses, `summary` is `None`. Otherwise, `summary` contains:

- `counts_scope="returned_events"`;
- `request`: `{id, method, path, status_code, duration_ms, query_count, duplicate_query_count, had_exception}`, or `None` when no request event is returned;
- `event_counts` and `observed_signals`, which includes only positive counts for `exceptions`, `http_server_errors`, `http_client_errors`, `slow_queries` and `duplicate_queries`;
- `first_seen` and `last_seen` for the returned events.

Counts describe only the returned subset, not all retained traffic. Missing signals are not proof that no errors occurred. `limit` must be a positive integer; invalid values are rejected before reading evidence. The default is the configured maximum, capped by both `MCP_MAX_LIMIT` and Evidence's `MAX_FAMILY_LIMIT`; explicit limits are capped by those same bounds.

Start compact, then request the ordered metadata timeline or richer investigation evidence:

```text
summarize_request_family("<family_hash>", limit=100)
get_request_detail("<family_hash>")
investigate_request("<family_hash>")
```

`get_request_detail` already provides an ordered metadata timeline. The richer investigation tools use a different policy: they can include masked payload-derived evidence and hypotheses, subject to their MCP safety settings. The summary's unconditional metadata-only guarantee does not extend to those tools.

## Agentic Debugging Workflow

Use the high-level tools when you want the assistant to move from symptom to evidence instead of browsing raw rows.

```text
audit_mcp_exposure()
find_sensitive_payload_risks(limit=20)
build_debug_brief("checkout returns 500 payment token rejected")
create_incident_bundle("fingerprint", "<fingerprint-from-brief>", format="markdown")
create_incident_bundle("fingerprint", "<fingerprint-from-brief>", format="prompt")
propose_fix_hypotheses("fingerprint", "<fingerprint-from-brief>")
propose_test_plan("family_hash", "<family_hash>")
generate_pr_context("fingerprint", "<fingerprint-from-brief>")
investigate_endpoint("/checkout/", method="POST")
compare_endpoint_windows("/checkout/", method="POST")
find_n_plus_one_candidates(hours=24)
summarize_exception_groups(hours=24)
generate_release_risk_brief(hours=24)
investigate_exception_group("<fingerprint>")
investigate_request("<family_hash>")
```

Incident bundles are generated on demand from current `OrbitEntry` data. They are not persisted. Each bundle includes primary evidence, a safety report, recommended next actions, likely code surfaces, a suggested coding-agent prompt and a next-tool sequence for deeper investigation. Use `create_incident_bundle(..., format="prompt")` when MCP is unavailable and you need a safe copy/paste prompt. Use `generate_pr_context` when you need a paste-ready PR section after the fix path is understood.

## Agent Safety

Payload-bearing MCP entry output goes through Orbit's agent-safe serializer. It masks sensitive keys using `MASK_KEYS`, can omit payloads entirely, and replaces oversized payloads with deterministic truncation metadata. Evidence-backed tools such as `summarize_request_family` and `get_request_detail` instead return metadata-only Evidence responses regardless of `MCP_INCLUDE_PAYLOADS`. Use `audit_mcp_exposure`, `preview_masked_entry`, `find_sensitive_payload_risks` and `list_agent_safe_fields` to verify the effective policy before sharing an MCP session with an assistant.

Residual risk: MCP gives a local assistant read access to Orbit telemetry. Masking and truncation reduce raw secret exposure, but telemetry can still reveal sensitive operational context such as endpoint names, SQL shape, exception messages, user identifiers or business events. In shared, staging or sensitive environments, prefer `MCP_ENABLED: False`; if agents only need metadata, set `MCP_INCLUDE_PAYLOADS: False`.

### What an Agent Can See

With default MCP settings, payload-bearing entry tools can expose common fields such as type, timestamps, duration, family hash, tags and masked payload data. The compact summary and Evidence-backed request detail do not expose tags or payloads. For LLM entries returned by payload-bearing tools, the default payload contains provider/model/token metadata and tool-call names, not prompts or completions.

An agent does not get direct database access, shell access or code-editing permission through Orbit MCP. It only receives the data returned by Orbit's read-only tools. If `MCP_INCLUDE_PAYLOADS` is `False`, entry payloads, derived free-text summaries, tags and query-analysis SQL previews are omitted. Entry serializers retain empty `summary` and `tags` fields for compatibility and report `derived_fields_omitted`. A per-call payload request cannot override the disabled configuration.

Incident-bundle safety reports describe policy coverage rather than certify that
no sensitive values exist. `raw_sensitive_values_exposed` is `null` and
`residual_risk` is `unknown`: key-based masking is not universal free-text
redaction. When payloads are enabled, messages, SQL literals and tags can still
contain private text. Identifiers, paths and other operational metadata can
remain sensitive in either mode. Review exports before sharing them.

Use this sequence before sharing a sensitive session:

```text
audit_mcp_exposure()
find_sensitive_payload_risks(limit=20)
list_agent_safe_fields("request")
list_agent_safe_fields("llm")
preview_masked_entry("<entry-id>")
```

## Example Prompts

Once connected, ask your AI assistant questions like:

- *"Why is `/api/orders/` slow? Check the recent requests."*
- *"What exceptions occurred in the last hour?"*
- *"Find all N+1 query patterns in the app"*
- *"Show me everything that happened during request abc123"*
- *"What's the current error rate and avg response time?"*

The assistant will call the appropriate Orbit tools and reason over the live data from your running Django app.

## Configuration

```python
ORBIT_CONFIG = {
    'MCP_ENABLED': True,  # default
}
```

Setting `MCP_ENABLED: False` does not disable the server itself (it's a management command), but disables data exposure if you want to prevent access programmatically.

For metadata-only access, keep MCP enabled and omit payload bodies:

```python
ORBIT_CONFIG = {
    'MCP_ENABLED': True,
    'MCP_INCLUDE_PAYLOADS': False,
}
```

## Running Manually

You can also run the MCP server directly for debugging:

```bash
python manage.py orbit_mcp
```

This starts the server in stdio mode. It reads JSON-RPC messages from stdin and writes responses to stdout — the standard MCP transport.

## How It Works

The `orbit_mcp` management command calls `create_mcp_server()` from `orbit/mcp_server.py`, which builds a `FastMCP` (mcp 1.x) or `MCPServer` (mcp 2.x) instance with the raw telemetry and agentic investigation tools. Payload-based tools query `OrbitEntry`; Evidence-backed tools read through `orbit.evidence`, with `summarize_request_family` consuming only family evidence metadata.

The server is stateless and read-only — it never modifies your data.

## Next Steps

- [Configuration Reference](configuration.md)
- [Storage Backends](storage-backends.md) — persist data across restarts for richer AI context
