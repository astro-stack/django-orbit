# Tool Options

This page compares practical tools for recording Orbit demos.

## Best Open-Source Path

### Recordly

Best fit when you want a Screen Studio-like result with less manual editing.

Use for:

- product demo recordings;
- camera zooms;
- polished cursor movement;
- short marketing clips.

Tradeoff: newer ecosystem, so verify stability before relying on it for a release video.

### Screenity

Best fit when the whole demo happens in the browser.

Use for:

- Orbit dashboard walkthroughs;
- click highlights;
- browser-only captures;
- quick clips with simple editing.

Tradeoff: browser extension/workflow may be less predictable for terminal + browser split videos.

### OBS Studio

Best fit for reliable capture.

Use for:

- long recordings;
- terminal + browser layouts;
- stable local capture;
- repeatable settings.

Tradeoff: OBS records well but does not automatically create polished zooms/click focus. Pair it with Kdenlive or another editor.

### Kdenlive

Best fit for open-source editing.

Use for:

- zoom/pan keyframes;
- cuts;
- captions;
- audio cleanup;
- exporting final MP4 files.

Tradeoff: more manual work than Screen Studio-like tools.

## Paid Tools Worth Considering

### Screen Studio

Best overall result for software demos if macOS is available.

Use for:

- automatic zooms;
- cursor smoothing;
- clean backgrounds;
- polished SaaS-style videos.

Tradeoff: paid and macOS-focused.

### Tella, Descript, Camtasia

Useful for narration-heavy product walkthroughs and faster edits.

Tradeoff: less reproducible than a Playwright-driven recording flow unless you keep a strict script.

## Recommended Orbit Setup

For the first v0.12 videos:

1. Use Playwright/manual checklist to make the browser path repeatable.
2. Record browser-only scenes with Screenity or Recordly.
3. Record terminal-heavy scenes with OBS.
4. Edit only the final cuts in Kdenlive if needed.

## Decision Matrix

| Need | Best choice |
|------|-------------|
| Fast polished browser demo | Recordly or Screenity |
| Maximum reliability | OBS |
| Fully open-source capture + edit | OBS + Kdenlive |
| Most polished with least effort | Screen Studio |
| Repeatable browser actions | Playwright plus any recorder |

