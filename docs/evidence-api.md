# Evidence API

Orbit provides a public, versioned read boundary for integrations that need
runtime evidence without depending on `OrbitEntry` internals:

```python
from orbit.evidence import read_family_evidence

evidence = read_family_evidence("request-family-hash")
```

The current schema identifier is `orbit.evidence.v1`.

## Why Use It

Direct ORM access exposes Orbit's complete payload schema and couples an
integration to internal model details. The Evidence API returns plain Python
dictionaries with a small, documented set of normalized fields.

Use it for local debugging extensions, CI helpers, incident tooling, or
agent-assisted workflows that need a stable, metadata-first input.

## Find a Family Hash

The MCP `get_recent_requests` tool returns the complete `family_hash`. A
local integration can also select a captured request from `python manage.py shell`
and pass its hash to the Evidence API:

```python
from orbit.evidence import read_family_evidence
from orbit.models import OrbitEntry

request = (
    OrbitEntry.objects.requests()
    .exclude(family_hash=None)
    .latest("created_at")
)
evidence = read_family_evidence(request.family_hash)
```

Use the full hash. A shortened value copied from a dashboard label may not
identify the family.

## Family Response

```json
{
  "schema_version": "orbit.evidence.v1",
  "status": "ok",
  "reason": null,
  "family_hash": "abc123",
  "count": 1,
  "truncated": false,
  "evidence_quality": {
    "status": "complete",
    "warnings": [],
    "missing_fields": [],
    "truncated_fields": [],
    "unsupported_entry_types": [],
    "next_actions": []
  },
  "entries": [
    {
      "id": "7fb37d9d-815b-43d5-8e5f-3faed295ef98",
      "type": "request",
      "family_hash": "abc123",
      "fingerprint": null,
      "created_at": "2026-07-23T12:00:00+00:00",
      "duration_ms": 123.4,
      "attributes": {
        "method": "GET",
        "path": "/checkout/",
        "status_code": 200,
        "query_count": 4,
        "duplicate_query_count": 0,
        "had_exception": false
      },
      "truncated_fields": []
    }
  ]
}
```

`status` reports whether the read operation succeeded. It does not say that
Orbit captured every event needed for a conclusion.

| Status | Reason | Meaning | Recommended response |
|--------|--------|---------|----------------------|
| `ok` | `null` | One or more normalized entries were read | Check `evidence_quality.status` before evaluating the result |
| `not_found` | `family_not_found` | No matching entries are currently stored | Verify the full hash, capture settings, pruning, and retention |
| `invalid` | `invalid_family_hash` | The hash is blank, padded, malformed, or too long | Supply a valid full family hash |
| `invalid` | `invalid_limit` | The limit is outside `1..5000` | Retry with a valid limit |
| `unavailable` | `storage_unavailable` | The Orbit table is not available | Verify migrations and the configured storage alias |
| `unavailable` | `read_failed` | Storage could not be read safely | Retry and inspect server logs |

Database exception text and storage details are never returned. A `not_found`
response is not proof that an event did not happen.

## Evidence Quality

`evidence_quality.status` is the completeness signal for automated consumers:

| Quality | Meaning |
|---------|---------|
| `complete` | All normalized v1 fields for supported entry types are present and the family did not exceed the requested limit |
| `partial` | The family was clipped, a field is missing or shortened, or the family contains an entry type not normalized by v1 |
| `unavailable` | The read could not provide evidence to evaluate |

The object includes machine-readable `warnings`, `missing_fields`,
`truncated_fields`, `unsupported_entry_types`, and structured `next_actions`.
Each action contains a stable `code` and concrete `parameters`. Any nonempty
warning list means a consumer must not conclude that a problem is absent.

```python
result = read_family_evidence("abc123")
quality = result["evidence_quality"]

for action in quality["next_actions"]:
    if action["code"] == "retry_with_higher_limit":
        result = read_family_evidence(
            result["family_hash"],
            limit=action["parameters"]["limit"],
        )

if result["status"] != "ok" or result["evidence_quality"]["status"] != "complete":
    # Report the warning and next action; do not emit a passing diagnosis.
    raise RuntimeError("Orbit evidence needs recovery before evaluation")
```

A `complete` result only describes normalized `request`, `query`, and
`exception` fields in the returned window. Ignore rules, disabled watchers, sampling, or retention may still mean historical events
were never captured or are no longer stored.

### Action Catalog

| Action code | Parameters | What the consumer should do |
|-------------|------------|-----------------------------|
| `provide_valid_family_hash` | `max_chars` | Obtain the full hash from `get_recent_requests` or a captured request |
| `use_valid_limit` | `minimum`, `maximum`, `default` | Retry inside the documented bounds |
| `verify_family_hash` | none | Confirm that the full, unshortened hash was supplied |
| `verify_capture_and_retention` | none | Check watcher settings, ignore rules, pruning, and retention |
| `verify_migrations_and_storage` | none | Run Orbit migrations for the configured storage alias |
| `retry_read` | none | Retry the same read after storage recovers |
| `inspect_server_logs` | none | Inspect the host application's logs for the internal read failure |
| `retry_with_higher_limit` | `limit` | Repeat `read_family_evidence` with the supplied limit |
| `call_mcp_tool` | `tool`, `arguments`, `reason` | Invoke the named MCP tool with the supplied complete argument object |
| `review_missing_fields` | `fields` | Treat the listed measurements as unknown and review capture configuration |
| `review_truncated_fields` | `fields` | Avoid decisions that require the clipped values |
| `do_not_conclude_absence` | none | Do not report a passing or absent diagnosis from this response |

### Evidence Quality Fragment

```json
{
  "status": "ok",
  "reason": null,
  "evidence_quality": {
    "status": "partial",
    "warnings": ["unsupported_entry_types"],
    "missing_fields": [],
    "truncated_fields": [],
    "unsupported_entry_types": ["log"],
    "next_actions": [
      {
        "code": "call_mcp_tool",
        "parameters": {
          "tool": "create_incident_bundle",
          "arguments": {
            "source_type": "family_hash",
            "source_value": "abc123",
            "format": "json"
          },
          "reason": "unsupported_entry_types"
        }
      },
      {"code": "do_not_conclude_absence", "parameters": {}}
    ]
  }
}
```

For `not_found`, `invalid`, and `unavailable`, the same quality object uses
`status: "unavailable"` and returns the recovery actions listed above. Surface
the reason to the developer; never translate it into "no problem found".

## Entry Schema

Normalized attributes by entry type:

| Entry type | Attributes |
|------------|------------|
| `request` | `method`, `path`, `status_code`, `query_count`, `duplicate_query_count`, `had_exception` |
| `query` | `is_slow`, `is_duplicate`, `duplicate_count`, `database` |
| `exception` | `exception_type`, `request_method`, `request_path` |
| Other | Empty object; the family quality becomes `partial` and lists the type in `unsupported_entry_types` |

Missing or malformed values are `null`. Valid zero values remain zero. This
distinction matters for automated verification: unknown data is not a passing
measurement.

## Limits and Ordering

```python
evidence = read_family_evidence("abc123", limit=250)
```

- Default limit: `1000`
- Valid range: `1..5000`
- Ordering: `created_at`, then entry ID
- Long paths are limited to 2,048 characters
- Family hashes and fingerprints are limited to 64 characters
- Other normalized strings are limited to 255 characters
- Query strings and URL fragments are removed from paths
- Clipped fields are listed in both the entry and quality metadata

If `truncated` is true, retry with a higher limit. If the family remains
truncated at `5000`, follow the returned `call_mcp_tool` action for
`create_incident_bundle` and treat it as not fully evaluable instead of assuming omitted evidence is
irrelevant. Invalid limits are rejected rather than silently clamped.

## Safety Boundary

Version 1 never returns:

- raw payloads;
- summaries or tags;
- request headers, cookies, bodies, query strings, or URL fragments;
- SQL text or parameters;
- exception messages, tracebacks, or locals;
- log messages;
- mail, cache, storage, user, or session values.

Endpoint paths, exception class names, database aliases, timestamps, IDs, and
fingerprints can still be sensitive in some applications. Review your
environment and access policy before exporting Evidence API output.

The adapter performs no writes and returns a structured unavailable state
instead of propagating storage errors into the host application. Callers must
still branch on `status` and `evidence_quality.status`.

## Compatibility

Fields may be added to `orbit.evidence.v1`. Consumers must ignore unknown
fields. Existing fields will not be removed, renamed, or given a different
meaning within v1. A breaking change requires a new schema identifier such as
`orbit.evidence.v2`.

Import the API from `orbit.evidence`; importing private helpers from
`orbit.agentic`, `orbit.watchers`, or the model manager is not a stable
integration contract.
