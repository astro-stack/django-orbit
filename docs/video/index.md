# Video Production Kit

This folder defines repeatable product-video workflows for Django Orbit.

The goal is to make demos easy to re-record whenever the UI or agent workflow changes:

- one storyboard per video;
- deterministic browser steps;
- predictable demo data;
- a recording checklist;
- clear guidance on open-source and paid tooling.

## Recommended Workflow

Use a hybrid recording process:

1. Run the Django Orbit demo locally.
2. Use the storyboard to decide the scene order.
3. Use Playwright or a manual checklist to drive the browser consistently.
4. Record with Recordly, Screenity, OBS or another screen recorder.
5. Edit only if needed in Kdenlive, DaVinci Resolve or a similar editor.

This keeps the demo reproducible without forcing every video to be generated entirely by code.

## Folder Contents

| File | Purpose |
|------|---------|
| [Storyboard](storyboard.md) | Shot-by-shot plan for the first Orbit product videos. |
| [Recording Checklist](recording-checklist.md) | Local setup, browser state, audio/video checks and export settings. |
| [Tool Options](tool-options.md) | Open-source and paid options for recording, zooms and editing. |
| [Playwright Scenes](playwright-scenes.md) | Browser automation plan for repeatable demo flows. |

## First Videos to Record

1. **Install Orbit and open the dashboard**
2. **Debug a 500 with Orbit and an AI coding agent**
3. **Find slow queries and N+1 candidates**
4. **Verify what an agent can see through MCP**
5. **Inspect AI/LLM call metadata without capturing prompts**
6. **Run the release readiness workflow**

