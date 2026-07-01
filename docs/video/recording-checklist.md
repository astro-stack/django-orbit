# Recording Checklist

Use this before every recording session.

## Local App State

- Pull or checkout the exact branch being recorded.
- Use a clean virtual environment.
- Run migrations.
- Seed demo data.
- Start the Django server.
- Confirm `/`, `/orbit/`, `/orbit/health/` and `/orbit/stats/` load.
- Clear old Orbit entries if the video needs a clean feed.
- Generate only the entries needed for the current scene.

## Browser State

- Use a clean browser profile or private window.
- Set zoom to 100%.
- Hide bookmarks bar unless the recorder frame needs it.
- Use a consistent viewport, preferably 1440x900 or 1920x1080.
- Disable browser extensions that inject UI.
- Keep the mouse movement deliberate and slow.

## Visual Framing

- Start each scene on a stable frame for 1-2 seconds.
- Pause after every click so automatic zoom tools can focus.
- Avoid scrolling while a zoom animation is happening.
- Keep terminal width wide enough for commands to fit.
- Use light or dark mode consistently across the full video set.

## Audio

- Record narration separately when possible.
- Keep screen recording silent if using subtitles/TTS later.
- Avoid live narration when running commands that may vary.

## Capture Settings

Recommended export:

- Resolution: 1920x1080
- Frame rate: 30 FPS
- Format: MP4/H.264
- Cursor: visible
- Click highlights: enabled
- Zoom on click: enabled when available
- Background: simple, no desktop clutter

## Orbit-Specific Checks

- Do not show real secrets, API keys, tokens, customer data or private project names.
- Prefer demo/stub data.
- For MCP scenes, show `audit_mcp_exposure()` before deeper tools.
- For AI/LLM scenes, show `LLM_CAPTURE_CONTENT: False`.
- For prompt-copy scenes, verify copied text contains safety constraints.

## Post-Recording Review

- Check text readability at mobile/social preview size.
- Confirm no sensitive values are visible.
- Trim dead time before/after commands.
- Add chapter labels only if they make the demo clearer.
- Export one master file and one compressed web/social file.

