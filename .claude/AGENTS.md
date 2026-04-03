# Django Orbit — Multi-Agent Workflow

Five specialized agents collaborate to ship features with production quality.
All agents read from and write to `.claude/workspace/` as handoff artifacts.

---

## Agents

| Agent | Invocation | Input | Output |
|-------|-----------|-------|--------|
| Product Owner | `po` | Feature idea (from you) | `.claude/workspace/spec.md` |
| Architect | `architect` | `spec.md` | `.claude/workspace/design.md` |
| Backend Dev | `backend-dev` | `design.md` + codebase | Code changes |
| Frontend Dev | `frontend-dev` | `design.md` + templates | Template changes |
| QA Engineer | `qa` | `spec.md` + `design.md` + new code | Tests + report |

---

## Standard workflow

```
You: "I want to add [feature]"
  ↓
PO → writes spec.md → you review
  ↓
Architect → writes design.md → you review
  ↓
Backend Dev + Frontend Dev (parallel if both needed)
  ↓
QA → tests + report → you review
```

### Step 1 — Spec (PO)

Tell the PO agent the idea. It will read PLANNING.md, CHANGELOG.md, README.md and write a structured spec to `.claude/workspace/spec.md`. Review and approve before continuing.

### Step 2 — Design (Architect)

The Architect reads `spec.md` and the relevant codebase, then writes `design.md`. It lists exactly which files to create/modify, config keys to add, payload schemas, algorithms. Review and approve before handing off to devs.

### Step 3 — Implementation

**Backend Dev**: Reads `design.md`, implements Python/Django code following all project conventions (`_table_exists()` guard, `cachalot_disabled()`, `WATCHER_FAIL_SILENTLY`, etc.).

**Frontend Dev**: Reads `design.md`, implements templates, HTMX interactions, Tailwind CSS following the dark-mode design system.

Run them in parallel if the design clearly separates backend and frontend work.

### Step 4 — QA

The QA agent reads `spec.md` (acceptance criteria), `design.md`, and the new code. It writes a comprehensive test file, runs the full suite, and produces a QA report mapping each acceptance criterion to test results.

---

## Quick invocations

```
# New feature
Agent tool → subagent_type: "po"     → "We want to add real-time alerting for exceptions"

# After PO finishes
Agent tool → subagent_type: "architect"  → "Design the implementation for spec.md"

# After Architect finishes  
Agent tool → subagent_type: "backend-dev"  → "Implement design.md"
Agent tool → subagent_type: "frontend-dev" → "Implement the UI from design.md"

# After implementation
Agent tool → subagent_type: "qa"  → "Validate the implementation against spec.md"
```

---

## Workspace files

`.claude/workspace/` is gitignored — these files are transient, one set per feature.

- `spec.md` — PO output, defines the "what" and acceptance criteria
- `design.md` — Architect output, defines the "how"

Overwrite freely when starting a new feature.

---

## Rules for all agents

1. Read before writing — never assume file contents
2. Respect role boundaries — Backend Dev doesn't design, QA doesn't fix bugs
3. Defer to existing patterns — if watchers.py already solves a similar problem, follow that pattern
4. Escalate to the user — if something is ambiguous or blocked, say so clearly rather than guessing
