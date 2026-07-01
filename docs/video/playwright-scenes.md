# Playwright Scenes

Playwright should drive repeatable browser behavior; the recorder captures the browser. This avoids redoing manual clicks when the UI changes.

These are scene specs, not a committed test suite. Convert them into scripts when the video target is fixed.

## Shared Setup

Assumptions:

- Django runs at `http://127.0.0.1:8000`.
- Orbit is mounted at `/orbit/`.
- The demo has endpoints for normal traffic, slow requests, duplicate queries and errors.
- Browser viewport is `1440x900` or `1920x1080`.

Suggested script structure:

```text
scripts/video/
  scene_install_smoke.py
  scene_debug_500.py
  scene_n_plus_one.py
  scene_llm_metadata.py
  scene_release_readiness.py
```

## Scene: Dashboard Smoke

Steps:

1. Open `/`.
2. Pause 1 second.
3. Open `/orbit/`.
4. Pause on dashboard.
5. Click **Requests**.
6. Click the latest request.
7. Pause on detail panel.

Recording notes:

- Zoom into the sidebar.
- Zoom into the entry feed.
- End on the detail panel.

## Scene: Debug 500

Steps:

1. Open `/error/` or the demo error endpoint.
2. Return to `/orbit/`.
3. Click **Exceptions**.
4. Open the latest exception.
5. Click **Copy agent prompt**.
6. Pause on success check icon.

Recording notes:

- Keep the copied prompt private if it includes local paths.
- For the public video, paste into a clean scratch editor or agent chat only if the content is safe.

## Scene: Slow Query and N+1

Steps:

1. Open the duplicate-query demo endpoint.
2. Open the slow endpoint.
3. Open `/orbit/`.
4. Click **Requests**.
5. Open the most recent request with duplicate query evidence.
6. Scroll to query timeline.
7. Open the related slow or duplicate query.

Recording notes:

- Pause on duplicate badges.
- Pause on query timeline bars before clicking.

## Scene: MCP Safety

This scene is better recorded in an assistant UI or terminal, not only the browser.

Steps:

1. Show settings with:

```python
ORBIT_CONFIG = {
    "MCP_ENABLED": True,
    "MCP_INCLUDE_PAYLOADS": False,
}
```

2. Run or show:

```text
audit_mcp_exposure()
find_sensitive_payload_risks(limit=20)
list_agent_safe_fields("request")
preview_masked_entry("<entry-id>")
```

3. Open `/orbit/health/`.
4. Pause on **Agent & MCP Safety**.

Recording notes:

- Avoid showing real project telemetry.
- Prefer metadata-only mode.

## Scene: AI/LLM Metadata

Steps:

1. Show config:

```python
ORBIT_CONFIG = {
    "RECORD_LLM": True,
    "LLM_CAPTURE_CONTENT": False,
    "LLM_CAPTURE_TOOL_CALL_ARGUMENTS": False,
}
```

2. Trigger a stubbed or local provider call.
3. Open `/orbit/`.
4. Click **AI/LLM**.
5. Open the latest LLM entry.
6. Pause on provider/model/tokens/tool-call names.

Recording notes:

- The video should explicitly show `metadata_only: true`.
- Do not use real prompts in a public recording.

## Scene: Release Readiness

Steps:

1. Open terminal.
2. Run:

```bash
python scripts/verify_release.py
```

3. Open the PR checks page.
4. Show release metadata/docs/package checks.

Recording notes:

- This is a credibility video, not a debugging video.
- Trim the long test output unless the goal is to show the whole command.

