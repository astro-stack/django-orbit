# Planning — Track B (competitor features) & Track C (AI/agentic 2026)

> Working planning doc (not part of the published docs). Feeds the v0.9.0 release after the
> UX overhaul. Implement only what's approved.

## What Orbit already has (baseline)

15 watchers (request, query+N+1, log, exception, job, cache, model, http_client, dump,
mail+HTML preview, signal, redis, gate, transaction, storage), Stats (Apdex, percentiles,
trends, DB, cache, jobs, security), family/`family_hash` grouping, search, auth gate,
pruning (`STORAGE_LIMIT`), health page, per-entry JSON export, and an **MCP server with 7
tools** (`get_recent_requests`, `get_slow_queries`, `get_exceptions`, `get_n1_patterns`,
`search_entries`, `get_request_detail`, `get_stats_summary`).

---

## Track B — Competitor gap analysis

Sources: Laravel Telescope docs, django-silk (jazzband), Sentry docs/2026 reviews.

| Capability | Telescope | django-silk | Sentry | Orbit today | Gap? |
|---|---|---|---|---|---|
| Per-type watchers | ✅ | partial | n/a | ✅ (15) | — |
| Tagging + tag search | ✅ | — | ✅ | ❌ | **B1** |
| EXPLAIN / query plan on slow queries | — | ✅ (EXPLAIN ANALYZE) | ✅ | ❌ | **B2** |
| Exception grouping (fingerprint, count, first/last seen) | — | — | ✅ core | ❌ (rows repeat) | **B3** |
| Request waterfall/timeline (mini-trace) | — | partial | ✅ tracing | ❌ | **B4** |
| Sensitive-data masking (passwords, tokens, auth headers) | ✅ | ✅ | ✅ | ❌ | **B5** |
| Python profiler (cProfile + flamegraph) | — | ✅ | ✅ profiling | ❌ | B6 |
| Pin/keep entries from pruning ("monitored") | ✅ tags | — | — | ❌ | B7 |
| Request replay codegen (curl / pytest) | — | ✅ | — | ❌ | B8 |
| Alerts on new exception / error spike (webhook/Slack) | — | — | ✅ | ❌ | B9 |
| Template/view render watcher (+ context) | ✅ view | — | — | ❌ | B10 |
| Model hydration count per request | ✅ | — | — | ❌ | B11 |
| Mail `.eml` download | ✅ | — | — | ✅ preview only | B12 |
| Sampling / fractional recording (high load) | ✅ filter | ✅ | ✅ | ❌ | B13 |

### Recommended priority (value for a Django backend dev × simplicity)

**Tier 1 — high impact, strong fit**
- **B2 — Query EXPLAIN**: on a slow/duplicate query, show `EXPLAIN` (and opt-in `EXPLAIN ANALYZE`), tables, joins. Direct optimization value.
- **B3 — Exception grouping**: fingerprint exceptions (type+top frame), collapse duplicates into one row with count + first/last seen. Biggest signal-to-noise win.
- **B4 — Request waterfall**: a timeline of a request's queries/cache/HTTP spans (uses existing `family_hash`). Makes "why is this slow" obvious.
- **B5 — Sensitive-data masking**: redact configurable keys (password, token, authorization, secret) in payloads. Safety/trust.
- **B1 — Tagging + tag search**: custom tags via `orbit.tag(...)` + filter by tag.

**Tier 2 — valuable, larger or niche**
- B7 pin/keep entries · B8 replay codegen (curl/pytest) · B9 alerts (webhook/Slack) ·
  B6 cProfile profiler · B10 template watcher · B11 hydration count · B12 `.eml` · B13 sampling.

---

## Track C — AI / agentic 2026

Theme: Orbit becomes the **observability layer an AI agent (and the developer) reasons over**.
Privacy-first: AI is **opt-in**, bring-your-own key (Anthropic Claude default, latest model),
data sent to the LLM only on explicit action.

**C1 — "Explain & fix" on an entry** (Sentry Seer/Autofix analog)
Button on an exception / N+1 / slow query → Claude explains root cause and proposes a concrete
fix (e.g. the `select_related`/`prefetch_related` patch for N+1; the index for a slow query).

**C2 — Natural-language search**
"500s on /checkout in the last hour", "slowest queries today" → translated to Orbit filters.

**C3 — AI request/family summary**
One-paragraph summary of a request family: what ran, what was slow, what's suspicious.

**C4 — AI exception triage**
Auto severity + suggested grouping/labels for incoming exceptions (pairs with B3).

**C5 — Deepen the MCP server (the agentic core)**
Extend the existing `orbit/mcp_server.py` so coding agents (e.g. Claude Code) can use Orbit
live while fixing bugs: add tools like `explain_query` (EXPLAIN), `get_request_timeline`,
`propose_n1_fix`, `get_entry_source_context`, and MCP **resources** for entries. This makes
Orbit the "eyes" of an agent during a debugging loop — the strongest 2026 differentiator and
it builds on infrastructure Orbit already ships.

**Cross-cutting:** `ORBIT_CONFIG['AI'] = {provider, api_key, model, enabled}`; results cached on
the entry; never auto-call the LLM during recording (zero overhead by default).

---

## Decision (user)

Ship **all of B and C** — make Orbit a mature product (Sentry-class) and a **next-gen agentic
tool usable by any MCP client** (Claude Code, Codex, etc.). Prioritize by user value.

## Cross-cutting principles (apply to EVERY feature)

**1. Performance at scale (many events).** Orbit must stay fast for users with huge event
volumes. Non-negotiables:
- **Recording path stays ~zero-cost**: heavy work (EXPLAIN, AI, fingerprint hashing beyond a
  cheap hash) is on-demand or async — never inline during capture.
- **Aggregate in the DB, not Python**: grouping/counts/first-last-seen via `annotate`/`values`
  + indexes — never load-and-loop. No N+1 inside Orbit itself.
- **Add indexes for every new query path** (e.g. fingerprint, tags, created_at+type) and keep
  payload writes small; mask/truncate at write time.
- **Bounded by default**: honor `STORAGE_LIMIT`/pruning; promote **sampling (B13)** so high-load
  apps record a fraction; paginate everything; cap list/aggregation result sizes.
- **AI/EXPLAIN are opt-in & cached on the entry** — computed once, never during recording.

**2. Reach more developers (diverse stacks).** Keep Orbit broadly useful by respecting how
different teams work — see **Track D** below. Detect-and-degrade gracefully (a watcher absent
on a given stack is fine), stay framework-idiomatic, and prefer config over assumptions.

## Sequenced roadmap (value × dependencies × effort)

Ordered so each milestone unlocks the next. Recommended **phased releases** (one big PR would
be unreviewable): v0.9.0 = foundation, then v0.10.0 / v0.11.0.

### Milestone 1 — Signal & safety foundation  → v0.9.0
- **B3 Exception grouping** — fingerprint (type + normalized top frame), collapse duplicates
  into one row with count + first/last seen. Flagship "mature" feature. Feeds C4.
- **B5 Sensitive-data masking** — redact configurable keys in payloads. **Prerequisite for
  any AI** (never send secrets to an LLM). Do before Track C.
- **B1 Tagging + tag search** — `orbit.tag()` + filter by tag.

### Milestone 2 — Query & request intelligence  → v0.9.0/0.10.0
- **B2 Query EXPLAIN** — plan/tables/joins on slow & duplicate queries (opt-in EXPLAIN ANALYZE).
- **B4 Request waterfall** — span timeline over `family_hash`.
These directly back the agentic tools in M3.

### Milestone 3 — Agentic core (universal MCP)  → v0.10.0
- **C5** extend `orbit/mcp_server.py` (tool-agnostic; works with any MCP client):
  `explain_query` (B2), `get_request_timeline` (B4), `get_exception_groups` (B3),
  `propose_n1_fix`, `get_entry_source_context`, tag search (B1), + MCP **resources** for entries.
- Document connecting from Claude Code, Codex, and generic MCP clients.

### Milestone 4 — AI assist layer  → v0.10.0/0.11.0
- LLM provider abstraction (`ORBIT_CONFIG['AI']`, Anthropic Claude default, opt-in, BYO key,
  masking-aware, cached on entry, never called during recording).
- **C1 Explain & fix** UI on exceptions / N+1 / slow queries.

### Milestone 5 — AI UX  → v0.11.0
- **C2** natural-language search · **C3** request/family summary · **C4** exception triage
  (severity/labels, pairs with B3).

### Milestone 6 — Maturity polish (Tier-2 B)  → v0.11.0+
- B7 pin/keep · B8 replay codegen (curl/pytest) · B9 alerts (webhook/Slack) · B6 cProfile
  profiler · B10 template watcher · B11 hydration count · B12 `.eml` download · B13 sampling.

### Track D — Ecosystem & reach (ongoing, woven across milestones)
Broaden the stacks Orbit serves so it reaches more developers. Candidates, prioritized later
with the user:
- **DRF-aware insights** (serializer/viewset/permission context) — large Django audience.
- **ASGI / async** request + query capture; **Channels / WebSockets** events.
- **GraphQL** (Strawberry/Graphene) resolver + query capture.
- **DB dialect coverage** for EXPLAIN (PostgreSQL / MySQL / SQLite) with graceful fallback.
- More **queue/cache backends** beyond current (e.g. Dramatiq, Huey; Memcached specifics).
- **Framework-agnostic core** where feasible so non-Django Python apps can adopt later.
Each addition follows the performance principles (detect-and-degrade, no recording overhead).

**Start point:** Milestone 1, leading with **B3** (highest visible value) then **B5** (safety
gate before Track C). Every feature ships with: DB-level aggregation + indexes, a scale note,
tests + docs, and a live-preview checkpoint. Phased releases (v0.9.0 → v0.10.0 → v0.11.0).
