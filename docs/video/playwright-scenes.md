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
  record-orbit-scenes.cjs
  run-local-recording.ps1
```

Run one local scene:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/video/run-local-recording.ps1 -Scene dashboard-smoke
```

Run all browser scenes:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/video/run-local-recording.ps1 -Scene all
```

Raw Playwright videos are written to `output/video/raw/`. MP4 files are written to
`output/video/mp4/`. Both directories are ignored by Git.

The recorder generates setup traffic through Playwright request calls before opening Orbit. That traffic is intentionally invisible in the browser recording, so public videos do not start on raw JSON endpoints or demo error pages.

Available scripted scenes:

| Scene | Purpose |
|-------|---------|
| `dashboard-smoke` | Fast sanity check: Orbit opens, telemetry appears, request detail works. |
| `dashboard-tour` | Longer product tour: live feed, sidebar filters, stats and health/safety. |
| `debug-500` | Runtime error to exception detail to copyable agent prompt. |
| `n-plus-one` | Slow request and duplicate-query evidence in request detail. |
| `health-safety` | Watcher status plus Agent & MCP Safety posture. |
| `llm-metadata` | AI/LLM metadata-first entry without prompt/response capture. |

## Scene: Dashboard Smoke

This is intentionally short. It does not show every dashboard surface; use
`dashboard-tour` for the full product walkthrough.

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

## Scene: Dashboard Tour

Steps:

1. Generate demo traffic.
2. Open `/orbit/`.
3. Pause on the live event feed and metric strip.
4. Explain sidebar filtering.
5. Click **Exceptions**. The demo uses seeded exception data; dashboard-tour should not visually trigger `/error/`.
6. Open **Stats**.
7. Open `/orbit/health/`.
8. Pause on **Agent & MCP Safety**.

Recording notes:

- This is the best source for a broad product demo.
- Keep callouts readable; this scene should feel closer to 45-60 seconds than a smoke test.

## Scene: Debug 500

Steps:

1. Use seeded demo exception/500 data so the browser recording starts in Orbit, not on Django's error page.
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

1. Seed or trigger an LLM call. The local runner seeds a metadata-only demo entry.
2. Show config:

```python
ORBIT_CONFIG = {
    "RECORD_LLM": True,
    "LLM_CAPTURE_CONTENT": False,
    "LLM_CAPTURE_TOOL_CALL_ARGUMENTS": False,
}
```

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
