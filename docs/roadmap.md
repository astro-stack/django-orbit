# Roadmap: Agent-Native Debugging

Django Orbit should evolve from a Django debugging dashboard into an agent-native observability layer: a local, privacy-conscious system that gives humans and AI agents enough structured context to move from ticket or error to root-cause hypothesis and proposed fix.

## Direction

The future debugging workflow is likely to be hybrid:

- humans use the dashboard for inspection, trust-building and quick triage;
- agents use MCP tools, incident bundles and structured traces for investigation;
- coding agents consume the same context to propose patches, tests and pull requests;
- OpenTelemetry compatibility keeps Orbit interoperable with the wider observability ecosystem.

Orbit's differentiator should be Django-native context: request lifecycle, ORM behavior, middleware, templates, cache, storage, mail, auth/gates, jobs, signals and settings-aware safety boundaries.

## Track A: High-Level MCP Tools

Current MCP tools expose useful raw slices. The next generation should expose investigation primitives that answer developer and agent questions directly.

### Request and Endpoint Investigation

| Tool | Purpose |
|------|---------|
| `investigate_request(family_hash)` | Return a complete diagnosis for one request: request summary, child events, slow spans, duplicate queries, exceptions, logs and likely causes. |
| `investigate_endpoint(path, method=None, hours=24)` | Summarize health for an endpoint across recent traffic: latency, error rate, slow queries, top exception groups and regressions. |
| `compare_endpoint_windows(path, baseline_hours=24, current_hours=1)` | Compare current endpoint behavior against a prior window to detect regressions. |
| `find_slowest_endpoints(hours=24, limit=10)` | Rank endpoints by p95 or average duration with query and exception context. |
| `find_erroring_endpoints(hours=24, limit=10)` | Rank endpoints by error rate and show representative requests. |
| `summarize_request_family(family_hash)` | Compact, agent-friendly summary of one family without full payload noise. |
| `get_request_timeline(family_hash)` | Return ordered spans/events suitable for RCA and timeline rendering. |
| `find_related_requests(family_hash, limit=10)` | Find similar requests by path, exception fingerprint, tags or duplicate-query signature. |
| `explain_status_code_spike(status_code, hours=24)` | Identify paths and fingerprints driving a spike in 4xx/5xx responses. |

### Exception and Error Intelligence

| Tool | Purpose |
|------|---------|
| `investigate_exception_group(fingerprint)` | Return representative traceback, frequency, affected paths, first/last seen and likely owner surface. |
| `summarize_exception_groups(hours=24)` | Group exceptions by fingerprint and rank by recency, frequency and blast radius. |
| `find_new_exception_groups(hours=24, baseline_hours=168)` | Detect exceptions not seen in the baseline period. |
| `find_regressed_exception_groups(hours=24, baseline_hours=168)` | Detect exception groups whose frequency increased materially. |
| `get_exception_repro_context(entry_id)` | Return request method/path, payload shape, user/auth hints, related logs and DB/cache events needed to reproduce. |
| `trace_exception_to_request(entry_id)` | Walk from exception to parent request and adjacent logs/queries/jobs. |
| `classify_exception(entry_id)` | Classify likely category: validation, auth, database, migration, external service, timeout, template, settings, code bug. |
| `suggest_exception_fix(entry_id)` | Produce a bounded hypothesis and candidate code areas, not an automatic patch. |

### Database and ORM Analysis

| Tool | Purpose |
|------|---------|
| `investigate_slow_query(entry_id)` | Explain one slow query with request context, duplicates, stack caller and optional EXPLAIN summary. |
| `find_n_plus_one_candidates(hours=24)` | Rank endpoints/requests with duplicate-query evidence. |
| `explain_n_plus_one(family_hash)` | Identify repeated SQL shapes, likely model relation and suggested `select_related` / `prefetch_related`. |
| `find_duplicate_query_signatures(hours=24)` | Group repeated SQL fingerprints globally. |
| `find_query_regressions(hours=24, baseline_hours=168)` | Detect query count or duration increases by endpoint. |
| `find_missing_indexes_candidates(hours=24)` | Use slow query patterns and EXPLAIN output to identify likely missing indexes. |
| `summarize_db_load(hours=24)` | Return query count, slow count, duplicate count, top tables if inferable and worst endpoints. |
| `get_query_callsite(entry_id)` | Return captured Python stack/caller context for the query. |

### Logs, Cache, Storage, Mail and Jobs

| Tool | Purpose |
|------|---------|
| `investigate_log(entry_id)` | Tie a warning/error log to request/job context and nearby events. |
| `find_warning_clusters(hours=24)` | Group warnings by logger/message shape and affected paths. |
| `analyze_cache_efficiency(hours=24)` | Cache hit/miss ratios by operation/key prefix if safe. |
| `find_cache_miss_spikes(hours=24)` | Identify endpoints or code paths with elevated misses. |
| `investigate_job_failure(entry_id)` | Summarize failed job, exception/log context and related DB/cache/external calls. |
| `summarize_jobs(hours=24)` | Job success/failure counts, slow jobs and top failure fingerprints. |
| `investigate_storage_error(entry_id)` | Explain storage failures with backend, operation and safe path metadata. |
| `investigate_mail_failure(entry_id)` | Summarize mail send failures, backend and safe recipient metadata. |
| `find_external_service_failures(hours=24)` | Group HTTP client failures/timeouts by host and endpoint. |

### Security and Privacy-Aware Debugging

| Tool | Purpose |
|------|---------|
| `find_authz_denials(hours=24)` | Summarize gate/permission denials by permission, user class and endpoint. |
| `investigate_permission_denial(entry_id)` | Tie a denial to request context and related logs. |
| `audit_mcp_exposure()` | Report MCP config, masking config and which tools can expose what classes of data. |
| `preview_masked_entry(entry_id)` | Show exactly what an agent would receive after masking. |
| `find_sensitive_payload_risks(limit=20)` | Identify entries whose keys look sensitive and confirm masking behavior. |
| `list_agent_safe_fields(entry_type)` | Return the allowlisted fields exported to MCP/incident bundles. |

### Ticket-to-Diagnosis Tools

| Tool | Purpose |
|------|---------|
| `investigate_ticket(text, hours=72)` | Parse a ticket/error report and search Orbit for matching paths, messages, fingerprints and tags. |
| `match_error_text(text, hours=72)` | Match pasted stack traces or user reports to exception groups and logs. |
| `build_debug_brief(query, hours=72)` | Generate a concise brief for a human or coding agent from a natural-language problem. |
| `find_recent_changes_context(path=None)` | Return Orbit-side evidence useful to compare against recent code changes, without reading git. |
| `propose_reproduction_steps(entry_id)` | Convert request/error context into likely repro steps and test targets. |
| `propose_test_plan(entry_id)` | Suggest unit/integration/E2E tests that would cover the failure. |
| `propose_fix_hypotheses(entry_id)` | Produce ranked hypotheses with confidence, evidence and files/surfaces likely involved. |
| `create_agent_handoff_bundle(entry_id_or_query)` | Produce a compact JSON/Markdown bundle for Codex/Cursor/Claude. |

### Daily Developer Workflows

| Tool | Purpose |
|------|---------|
| `daily_health_brief(hours=24)` | Morning digest: error groups, slow endpoints, N+1s, job failures, new warnings. |
| `what_changed_in_orbit(hours=24)` | Human-friendly summary of notable runtime behavior changes. |
| `triage_top_issues(hours=24, limit=10)` | Rank issues by severity, recency, frequency and blast radius. |
| `find_flaky_failures(days=7)` | Detect intermittent exception/job/log patterns. |
| `list_open_debug_threads(hours=24)` | Return unresolved-looking issue clusters with latest evidence. |
| `suggest_next_debug_action(issue_id_or_entry_id)` | Recommend the next investigation step based on missing evidence. |
| `generate_pr_context(entry_id_or_group)` | Create PR-ready context: problem, evidence, suspected cause, test plan. |
| `generate_release_risk_brief(hours=24)` | Before release: current errors, slow paths, new exception groups and safety warnings. |

## Track B: Incident Bundles

Incident Bundles are portable evidence packages generated from a request, exception group, endpoint, ticket text or natural-language query. They should be small enough for agents, structured enough for automation and readable enough for humans.

### Bundle Sources

- `family_hash` for a single request lifecycle;
- exception `fingerprint` for grouped errors;
- endpoint path/method for route-level behavior;
- raw ticket text or pasted traceback;
- tag, query or time window.

### Bundle Contents

Each bundle should include:

- metadata: bundle id, generated at, Orbit version, time window, source type;
- primary evidence: request summary, exception summary, endpoint stats or matched ticket terms;
- timeline: ordered events with relative offsets;
- query analysis: slow queries, duplicate signatures, callsites and EXPLAIN summaries when available;
- logs: warning/error logs near the event, grouped by logger/message shape;
- related systems: cache, jobs, mail, storage, Redis, HTTP client, gates;
- safety report: masking status, omitted fields, payload truncation and MCP exposure policy;
- hypotheses: ranked causes with supporting evidence and confidence;
- suggested next actions: reproduce, inspect file/surface, add test, check config, add index, etc.;
- agent handoff: compact JSON plus Markdown brief.

### Bundle Formats

- `incident_bundle.json` for agents and automation;
- `incident_bundle.md` for tickets, PRs and humans;
- optional zipped export for sharing with maintainers;
- future: OTLP trace export for OpenTelemetry-compatible backends.

### MCP Tools for Bundles

- `create_incident_bundle(source_type, source_id_or_text, hours=72)`
- `get_incident_bundle(bundle_id)`
- `list_recent_incident_bundles(limit=20)`
- `export_incident_bundle(bundle_id, format="json|markdown")`
- `redact_incident_bundle(bundle_id, policy="agent_safe")`

### Storage Model

Start without a new table: generate bundles on demand from `OrbitEntry` and return them directly. Add persisted bundles later only if users need sharing, comments or issue tracking.

## Track C: OpenTelemetry Bridge

Add OpenTelemetry as an interoperability lane, not as a replacement for Orbit's Django-native storage.

Possible milestones:

1. `orbit.exporters.opentelemetry` module that converts `OrbitEntry` objects into OTEL-like spans/events.
2. Config keys: `OTEL_EXPORT_ENABLED`, `OTEL_EXPORT_ENDPOINT`, `OTEL_SERVICE_NAME`, `OTEL_HEADERS`, `OTEL_SAMPLE_RATE`.
3. Map `family_hash` to `trace_id` and child entries to spans/events.
4. Map SQL/cache/http_client/job/mail/storage events to semantic attributes where stable.
5. Add GenAI/LLM attributes when the AI watcher ships.
6. Provide `python manage.py orbit_export_otel --since ...` for batch export.
7. Optional live export hook with strict fail-silent behavior.

## Track D: AI and LLM Watcher

Capture AI application behavior for Django apps that call LLM providers or agent frameworks.

Initial surfaces:

- OpenAI Python SDK;
- Anthropic Python SDK;
- LangChain / LangGraph callbacks;
- LiteLLM if present;
- HTTP fallback for known provider hosts.

Events should capture only safe metadata by default:

- provider, model, operation, status;
- latency, retries, timeout/error type;
- token counts and estimated cost when available;
- tool call names, not raw arguments by default;
- prompt/completion capture disabled by default and guarded by explicit config;
- request family correlation so LLM calls appear inside the Django request timeline.

Possible config:

```python
ORBIT_CONFIG = {
    "RECORD_AI": True,
    "AI_CAPTURE_PROMPTS": False,
    "AI_CAPTURE_COMPLETIONS": False,
    "AI_CAPTURE_TOOL_ARGS": False,
    "AI_MASK_KEYS": ["password", "token", "secret"],
}
```

## Track E: Agent Safety Layer

Before Orbit becomes deeply agentic, it needs explicit data boundaries.

Milestones:

1. Central `agent_safe_serialize_entry(entry)` used by MCP and bundles.
2. Default field allowlists by entry type.
3. Payload size caps and deterministic truncation metadata.
4. MCP-level config: `MCP_ENABLED`, `MCP_ALLOWED_TOOLS`, `MCP_DENIED_TOOLS`, `MCP_MAX_LIMIT`, `MCP_INCLUDE_PAYLOADS`.
5. `audit_mcp_exposure()` tool.
6. Masking preview in dashboard and MCP.
7. Optional per-environment profiles: `local`, `staging`, `production`.

## Track F: From Error to Fix Hypothesis

Orbit should not directly edit code. It should produce evidence-rich handoffs that coding agents can use.

Workflow:

1. Developer pastes a ticket, traceback or endpoint complaint.
2. Orbit matches it to entries, exception groups, endpoints or related logs.
3. Orbit creates an Incident Bundle.
4. Orbit ranks hypotheses and suggests repro/test plan.
5. A coding agent consumes the bundle, inspects the repo, writes tests, proposes a fix and references the evidence.
6. Orbit can later verify whether the runtime symptom disappeared.

MCP sequence example:

```text
investigate_ticket("Users get 500 on checkout")
create_incident_bundle("ticket", "Users get 500 on checkout")
propose_fix_hypotheses(bundle_id)
propose_test_plan(bundle_id)
generate_pr_context(bundle_id)
```

## Track G: Orbit Agent Packs

Orbit should eventually ship reusable agent roles, not only raw tools. These agents would be small, versioned workflows that tell Codex, Claude, Cursor or another MCP-capable assistant how to use Orbit evidence for a specific job. They should be explainable, inspectable and easy to improve over time.

The goal is not to create autonomous agents that freely modify applications. The goal is to provide high-quality role prompts, tool sequences, checklists and output schemas that make daily debugging and review workflows repeatable.

### Initial Agent Roles

| Agent | Purpose | Primary Orbit context | Expected output |
|-------|---------|-----------------------|-----------------|
| QA Agent | Turn runtime evidence into regression tests and repro steps. | Incident bundles, request families, exception groups, endpoint summaries. | Repro steps, failing test candidates, edge cases, acceptance checks. |
| Architecture Reviewer | Check whether a fix direction fits the app's Django boundaries. | Related entries, query callsites, middleware/settings context, endpoint behavior. | Architecture risks, coupling concerns, safer design options. |
| Performance Reviewer | Investigate slow endpoints, N+1s and query regressions. | Slow queries, waterfall, duplicate signatures, endpoint comparisons. | Bottleneck summary, likely ORM/index fixes, measurement plan. |
| Security and Privacy Reviewer | Verify that debugging context is safe to share with an assistant. | `audit_mcp_exposure`, masked previews, sensitive payload risks, gate events. | Exposure report, risky fields, safer sharing policy. |
| Release Reviewer | Decide whether a branch or release is safe enough to ship. | Release risk brief, daily health brief, new exception groups, endpoint regressions. | Blockers, cautions, release note context, follow-up checks. |
| Incident Commander | Coordinate a ticket/error investigation from symptom to handoff. | `build_debug_brief`, incident bundle, hypotheses, test plan, PR context. | Investigation timeline, next tool sequence, owner-ready summary. |

### Agent Pack Contents

Each agent pack should be a portable artifact, not hidden product magic:

- role prompt: what the agent is responsible for and what it must not do;
- required Orbit tools: minimum MCP calls and when to use them;
- input contract: ticket text, endpoint, entry id, family hash, fingerprint or bundle;
- output schema: Markdown sections and JSON fields when automation needs structure;
- safety policy: whether payloads are allowed, masked-only, or metadata-only;
- verification loop: tests, checks or Orbit queries required before a recommendation is trusted;
- examples: good prompts and expected outputs for real Django incidents.

### Product Surface

Near-term, this can stay open source and local:

1. `docs/agents/qa.md`, `architecture-reviewer.md`, `performance-reviewer.md`, etc.
2. MCP prompts/resources, if supported by the active MCP server implementation.
3. `orbit agents list` to show available roles and required tools.
4. `orbit agents print qa --source family_hash:...` to print a ready-to-paste prompt.
5. Dashboard action: `Copy QA agent prompt` or `Copy release reviewer prompt` from a detail panel or bundle.

Later, the cloud version can monetize collaboration around these agents:

- team-maintained agent policies;
- shared prompt versions and approvals;
- scheduled agent runs against daily/release briefs;
- comments, ownership and issue-tracker handoff;
- organization-level safety policies and audit logs.

### Improvement Loop

Agent packs should be designed to improve from usage without requiring Orbit to collect private telemetry by default:

- developers can edit local agent specs in-repo;
- teams can pin agent pack versions per project;
- outputs can be evaluated against checklists: did it cite evidence, avoid raw secrets, propose tests, avoid unsupported fixes;
- future cloud workflows can compare prompt versions and track which role produced useful handoffs.

## Near-Term Priority

The v0.11.0 release ships endpoint investigation, daily health briefs and release risk briefs from the roadmap. The next pragmatic PR sequence:

1. Add `agent_safe_serialize_entry()` and make existing MCP tools use it.
2. Add `investigate_request(family_hash)`.
3. Add `investigate_exception_group(fingerprint)`.
4. Add `create_incident_bundle(...)` as on-demand JSON.
5. Add `build_debug_brief(query, hours=72)`.
6. Add OpenTelemetry export design doc and config stub.
7. Add AI watcher behind conservative defaults.
