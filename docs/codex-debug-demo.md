# Debug Django With Codex And Claude Using Orbit Context

This workflow shows how to move from a ticket, error report or failing endpoint to a useful Codex, Claude or Cursor investigation using Orbit MCP context.

## 1. Run Orbit Locally

Install Orbit with MCP support and run your Django app normally:

```bash
pip install "django-orbit[mcp]"
python manage.py migrate
python manage.py runserver
```

Configure the MCP server in your coding assistant. Claude Desktop, Cursor and most MCP-compatible clients use the same server shape:

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

For Claude Desktop specifically, place the same block inside `claude_desktop_config.json`:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

For Claude Code or Codex CLI, configure the equivalent local MCP server entry for the project, pointing `command` to `python`, `args` to `["manage.py", "orbit_mcp"]`, and `cwd` to the Django project root.

Keep the MCP exposure explicit in Django settings:

```python
ORBIT_CONFIG = {
    "MCP_ENABLED": True,
    "MCP_INCLUDE_PAYLOADS": True,
    "MCP_MAX_LIMIT": 100,
    "MCP_MAX_PAYLOAD_CHARS": 12000,
}
```

## 2. Verify Agent Safety

Before asking Codex, Claude or Cursor to inspect runtime context, ask it to verify the exposure policy:

```text
audit_mcp_exposure()
find_sensitive_payload_risks(limit=20)
list_agent_safe_fields("request")
```

If a specific entry is relevant, preview exactly what the agent can see:

```text
preview_masked_entry("<entry-id>")
```

Orbit masks sensitive keys before output and reports payload truncation when evidence is too large.

## 3. Start From The Ticket Or Error

Give the coding agent the human symptom first. This prompt works in Codex, Claude or Cursor:

```text
Use Django Orbit context to investigate: checkout returns 500 after payment token rejection.
Start by finding matching runtime evidence. Do not edit code until you have a regression-test plan.
```

The assistant should call:

```text
build_debug_brief("checkout returns 500 after payment token rejection")
summarize_exception_groups(hours=24)
investigate_endpoint("/checkout/", method="POST", hours=24)
compare_endpoint_windows("/checkout/", method="POST")
```

For performance tickets, add:

```text
find_n_plus_one_candidates(hours=24)
```

## 4. Create An Incident Bundle

Once Orbit identifies a `family_hash` or exception `fingerprint`, create a bundle:

```text
create_incident_bundle("fingerprint", "<fingerprint>", format="markdown")
```

The bundle is designed for Codex, Claude and Cursor. It includes:

- source metadata and severity;
- primary runtime evidence;
- likely code surfaces from tracebacks and query callers;
- a suggested coding-agent prompt;
- a next-tool sequence;
- safety metadata confirming payload masking.

Use prompt format when MCP is not connected and you want to paste safe Orbit context into Claude, Codex or Cursor:

```text
create_incident_bundle("fingerprint", "<fingerprint>", format="prompt")
```

Use JSON when automation needs structure:

```text
create_incident_bundle("family_hash", "<family_hash>", format="json")
```

## 5. Move From Evidence To Fix Hypothesis

Ask the assistant to turn the bundle into a plan:

```text
Using the Orbit incident bundle, inspect the likely code surfaces, write a failing regression test first, and propose the smallest code fix that explains the captured signals.
```

Then ask Orbit for structured support:

```text
propose_fix_hypotheses("fingerprint", "<fingerprint>")
propose_test_plan("family_hash", "<family_hash>")
generate_pr_context("fingerprint", "<fingerprint>")
```

A good coding-agent handoff should produce:

- the exact runtime symptom being fixed;
- a failing test target;
- the code surface to inspect first;
- a minimal fix hypothesis;
- follow-up Orbit checks after the patch;
- a PR-ready Orbit Evidence section from `generate_pr_context`.

## 6. Verify Before Release

After the code change and tests pass, use Orbit again:

```text
investigate_endpoint("/checkout/", method="POST", hours=24)
compare_endpoint_windows("/checkout/", method="POST")
compare_endpoint_windows("/checkout/", method="POST")
generate_release_risk_brief(hours=24)
```

If blocker signals remain, keep the release closed. If the window is clean or the remaining signals are accepted, include the Orbit bundle or summary in the PR/release notes.
