# Storyboard

This storyboard is optimized for short software demos: 45-90 seconds each, one clear outcome per video, no broad feature tour.

## Video 1: Install Orbit and Open the Dashboard

Goal: show that Orbit can be added quickly and runs outside the app UI.

| Time | Shot | Action | Visual Focus |
|------|------|--------|--------------|
| 0-5s | Title | "AI agent-native observability for Django" | Browser or terminal clean frame |
| 5-15s | Install | Run install/setup commands | Terminal, command output |
| 15-25s | Configure | Show `INSTALLED_APPS`, middleware and URLs | Editor or docs snippet |
| 25-40s | Run | Start Django and open app | Browser address bar |
| 40-65s | Orbit | Open `/orbit/` and scan dashboard | Sidebar, live feed, stats strip |
| 65-75s | Close | "Runtime context for humans and agents" | Dashboard full frame |

Primary zooms:

- `orbit` app in settings;
- `/orbit/` URL;
- dashboard sidebar and entry feed.

## Video 2: Debug a 500 with Orbit and an AI Agent

Goal: show the ticket/error to evidence to prompt handoff.

| Time | Shot | Action | Visual Focus |
|------|------|--------|--------------|
| 0-5s | Symptom | Open failing endpoint | Browser 500/error page |
| 5-20s | Evidence | Open Orbit, filter exceptions | Exception row |
| 20-40s | Detail | Open detail panel | traceback, family hash, related entries |
| 40-55s | Prompt | Click copy agent prompt | Clipboard/check icon |
| 55-75s | Agent | Paste prompt into Codex/Claude/Cursor | Prompt content, not secrets |
| 75-90s | Close | "From runtime evidence to testable hypothesis" | Orbit + agent side by side |

Primary zooms:

- exception row;
- copy agent prompt button;
- "Safety constraints" in copied prompt.

## Video 3: Find Slow Queries and N+1 Candidates

Goal: show Orbit's value for Django performance work.

| Time | Shot | Action | Visual Focus |
|------|------|--------|--------------|
| 0-10s | Generate | Hit slow and duplicate-query endpoints | Browser tabs or terminal |
| 10-25s | Dashboard | Open queries/request family | slow/N+1 visual markers |
| 25-45s | Timeline | Open request detail | query timeline and related queries |
| 45-65s | MCP | Show `find_n_plus_one_candidates(hours=24)` output | ranked candidates |
| 65-75s | Close | "Evidence before ORM changes" | query detail |

Primary zooms:

- duplicate query badge;
- query timeline;
- suggested next tool/output.

## Video 4: Verify What an Agent Can See

Goal: explain safety posture without hand-waving.

| Time | Shot | Action | Visual Focus |
|------|------|--------|--------------|
| 0-10s | Setup | Open MCP docs/config | `MCP_ENABLED`, `MCP_INCLUDE_PAYLOADS` |
| 10-25s | Audit | Run `audit_mcp_exposure()` | safety policy |
| 25-40s | Fields | Run `list_agent_safe_fields("request")` | allowed fields |
| 40-55s | Preview | Run `preview_masked_entry("<entry-id>")` | masked values |
| 55-70s | Health | Open `/orbit/health/` | Agent & MCP Safety panel |

Primary zooms:

- `metadata only`;
- masked payload values;
- health safety panel.

## Video 5: Inspect AI/LLM Call Metadata

Goal: show the v0.12 feature without implying prompt capture.

| Time | Shot | Action | Visual Focus |
|------|------|--------|--------------|
| 0-10s | Config | Show `RECORD_LLM` and capture flags | settings snippet |
| 10-25s | Trigger | Run a local OpenAI/Anthropic call or stub endpoint | app action |
| 25-45s | Orbit | Filter AI/LLM entries | `AI/LLM` sidebar item |
| 45-65s | Detail | Open LLM entry | provider, model, usage, tool-call names |
| 65-80s | Safety | Show no prompt/completion content | metadata-only flag |

Primary zooms:

- `LLM_CAPTURE_CONTENT: False`;
- token usage;
- tool-call names without arguments.

## Video 6: Release Readiness Workflow

Goal: position Orbit as part of a serious OSS release process.

| Time | Shot | Action | Visual Focus |
|------|------|--------|--------------|
| 0-10s | Context | Show PR/release branch | GitHub PR |
| 10-30s | Preflight | Run `python scripts/verify_release.py` | tests/docs/build/twine |
| 30-45s | Orbit Risk | Show `generate_release_risk_brief(hours=24)` | blocker/caution output |
| 45-60s | PR Context | Show `generate_pr_context(...)` | release notes/test plan |
| 60-75s | Close | "Ship with runtime context and repeatable checks" | PR checks |

Primary zooms:

- release preflight success;
- PR checks;
- release risk recommendation.

