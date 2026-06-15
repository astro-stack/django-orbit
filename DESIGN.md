# Django Orbit — Design System

> The single source of truth for Orbit's dashboard UI. Read this before changing any
> template under `orbit/templates/`. Inspired by Linear's *ultra-minimal, precise*
> direction, grounded in Orbit's existing dark palette.

## Philosophy

Orbit is a **debugging tool used in short, focused bursts**. The UI must get out of the
way and surface signal fast. Three rules govern every decision:

1. **Hierarchy over decoration.** Color, weight, and spacing carry meaning. Decorative
   glows, gradients, and grid backgrounds are accents — never the default.
2. **Calm by default, loud on problems.** Normal rows are quiet. Errors, slow queries,
   and N+1 duplicates are the only things allowed to shout (rose / amber).
3. **Learnable in one session.** A developer should understand the layout, the entry
   types, and the keyboard shortcuts without reading docs.

## Color

Dark-only. Tokens are declared in `tailwind.config` inside
`orbit/templates/orbit/base.html` and referenced as `orbit-*` utility classes.

### Neutrals (surfaces & text)

| Token | Hex | Use |
|-------|-----|-----|
| `bg.primary` | `#020617` | App background (slate-950) |
| `bg.secondary` | `#0f172a` | Sidebar, panels (slate-900) |
| `bg.tertiary` | `#1e293b` | Cards, hover, inputs (slate-800) |
| `border` | `#334155` | Hairline borders (slate-700) |
| `text.primary` | `#f1f5f9` | Headings, key values (slate-100) |
| `text.secondary` | `#94a3b8` | Body, labels (slate-400) |
| `text.muted` | `#64748b` | Meta, timestamps (slate-500) |

### Accent & semantic

One **brand accent** (cyan) for interactive/active state. Everything else is **semantic**
— used only to convey state, never for decoration.

| Token | Hex | Meaning |
|-------|-----|---------|
| `accent.cyan` | `#22d3ee` | Active nav, focus, links, primary action |
| `accent.rose` | `#fb7185` | Error / failure / 5xx / exception |
| `accent.amber` | `#fbbf24` | Warning / slow / 4xx |
| `accent.emerald` | `#34d399` | Success / 2xx / cache hit |
| `accent.violet` | `#a78bfa` | Informational / duplicate / secondary metric |

Per-entry-type colors live in `OrbitEntry.TYPE_COLORS` (`orbit/models.py`) and drive the
type icons. Keep type colors **muted** (icon-only); they identify, they don't alarm.

## Typography

- **Sans:** Inter — UI text, labels, headings.
- **Mono:** JetBrains Mono — SQL, paths, payloads, IDs, durations, timestamps.

| Role | Size / weight |
|------|---------------|
| Page title | `text-lg` / 600 |
| Section heading | `text-sm` / 600, `text.secondary`, often uppercase tracking-wide |
| Body / row | `text-sm` / 400 |
| Meta / badge | `text-xs` / 500 |

Use mono for **anything a developer would copy** (IDs, SQL, file:line, ms).

## Spacing, radius, elevation, motion

- **Spacing:** 4px base. Cards pad `p-4`/`p-6`; rows `py-2.5 px-4`; group gaps `gap-3`.
- **Radius:** `rounded-lg` (8px) for cards/buttons, `rounded-full` for badges/dots,
  `rounded-xl` only for the brand mark.
- **Elevation:** prefer borders over shadows. Slide-over panel may use one soft shadow.
  `glow-*` utilities are reserved for the brand mark and at most one live-status dot —
  not cards.
- **Motion:** 150–200ms ease for hover/swap. Respect reduced-motion. No infinite glows
  except the single "recording" status dot.

## Components

- **Card:** `bg-orbit-bg-secondary border border-orbit-border rounded-lg`. Section title
  in `text.secondary` uppercase; metric value in `text.primary` large mono.
- **Badge:** `text-xs rounded-full px-2 py-0.5`. Neutral = `bg-orbit-bg-tertiary`.
  Semantic badges use `<color>-500/15` background + `<color>-400` text (e.g. SLOW = amber,
  DUP = violet, 5xx = rose).
- **Nav item:** quiet by default; active = cyan text + 2px left cyan border +
  `bg-orbit-bg-tertiary`. Count badge right-aligned; error types keep a rose count badge
  when non-zero.
- **Table row:** transparent left border; hover tints cyan; `is_error` tints rose,
  `is_warning` tints amber. Row is one click target.
- **Slide-over (detail):** right panel, `bg-orbit-bg-secondary`, one soft shadow, `Esc`
  to close, `j`/`k` to move between entries in the current feed.

## Layout

```
┌────────────┬─────────────────────────────────────────────┐
│  Sidebar   │  Top bar: title · live dot · search · actions │
│  (grouped  ├─────────────────────────────────────────────┤
│   nav)     │  Feed (table)            │  Detail slide-over │
└────────────┴─────────────────────────────────────────────┘
```

- **Sidebar** groups entry types into **Core / Infra / App** (collapsible). Core is open
  by default so newcomers see the essentials first.
- **Stats** and **Health** are full pages reachable from the nav, themed identically.

## Do / Don't

- ✅ Let whitespace and weight create hierarchy. ❌ Don't add a glow to make a card "pop".
- ✅ Reserve rose/amber for real problems. ❌ Don't color normal rows for variety.
- ✅ Drive nav/badges from config (`TYPE_*` maps). ❌ Don't hand-duplicate markup per type.
- ✅ Lazy-load heavy stats sections. ❌ Don't block first paint on every query.

## Accessibility

- Maintain WCAG AA contrast on `text.secondary`+ against `bg.primary`.
- Every interactive element is keyboard-reachable; visible cyan focus ring.
- Color is never the only signal — pair it with an icon or label (SLOW, DUP, status code).
