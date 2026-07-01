# AI/LLM Watcher

Django Orbit v0.12.0 adds a metadata-first AI/LLM watcher for Django apps that call model providers from request handlers, jobs or service code.

The watcher is designed for agent-native debugging without turning Orbit into a prompt recorder. By default it records operational metadata only:

- provider, operation and model;
- status and error type/message;
- latency;
- input, output and total token counts when the SDK exposes usage data;
- tool-call names and ids;
- `family_hash`, so LLM calls appear inside the same request timeline as SQL, logs and exceptions.

It does **not** capture prompts, messages, completions, response text or tool-call arguments by default.

## Supported SDK Surfaces

The initial watcher patches common sync/async SDK call sites when the packages are installed:

- OpenAI chat completions;
- OpenAI responses;
- legacy `openai.ChatCompletion.create`;
- Anthropic messages.

If a provider SDK is not installed, Orbit does nothing. Missing integrations do not fail app startup.

## Configuration

```python
ORBIT_CONFIG = {
    "RECORD_LLM": True,
    "LLM_CAPTURE_CONTENT": False,
    "LLM_CAPTURE_TOOL_CALL_ARGUMENTS": False,
    "LLM_MAX_CONTENT_CHARS": 2000,
}
```

### `RECORD_LLM`

Enables or disables AI/LLM call recording.

Default: `True`

### `LLM_CAPTURE_CONTENT`

When `False`, prompts, messages, inputs, completions and response text are omitted.

Default: `False`

Set this to `True` only in local environments where the team explicitly accepts storing model input/output in Orbit. Captured content is passed through Orbit's masking logic and bounded by `LLM_MAX_CONTENT_CHARS`, but it may still include sensitive business context.

### `LLM_CAPTURE_TOOL_CALL_ARGUMENTS`

When `False`, Orbit records tool-call names and ids but omits arguments.

Default: `False`

When enabled, arguments are parsed when possible, serialized safely and masked with `MASK_KEYS`.

### `LLM_MAX_CONTENT_CHARS`

Maximum serialized size for captured LLM content before Orbit replaces it with truncation metadata.

Default: `2000`

## Payload Shape

Example metadata-only payload:

```json
{
  "provider": "openai",
  "operation": "chat.completions",
  "model": "gpt-4.1-mini",
  "status": "success",
  "metadata_only": true,
  "content_captured": false,
  "tool_call_arguments_captured": false,
  "duration_ms": 184.2,
  "usage": {
    "input_tokens": 120,
    "output_tokens": 48,
    "total_tokens": 168
  },
  "tool_calls": [
    {
      "id": "call_123",
      "type": "function",
      "name": "lookup_order"
    }
  ]
}
```

## Production Safety

For shared or production-like environments, start with metadata only:

```python
ORBIT_CONFIG = {
    "RECORD_LLM": True,
    "LLM_CAPTURE_CONTENT": False,
    "LLM_CAPTURE_TOOL_CALL_ARGUMENTS": False,
    "MCP_INCLUDE_PAYLOADS": False,
}
```

This lets developers and agents reason about latency, provider errors, token usage and tool-call flow without exposing raw prompts or completions.

## Current Limits

- No cost calculation yet.
- No LangChain/LangGraph callback integration yet.
- No LiteLLM integration yet.
- No raw HTTP fallback for provider APIs yet.
- No per-provider allowlist/denylist yet.

Those are roadmap items for later releases.

