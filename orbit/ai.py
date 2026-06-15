"""
AI assist layer (C1).

Opt-in, bring-your-own-key explanations and fix suggestions for exceptions, slow/duplicate
queries and N+1 requests. Privacy-first:

* Disabled by default; enabled only when ``ORBIT_CONFIG['AI']['enabled']`` is true and an
  api_key is configured.
* Entry data is **masked** (via B5's ``mask_sensitive_data``) before it ever leaves the app.
* Called only on demand (never on the recording path) and the result is cached on the entry.
* Provider-agnostic: defaults to Anthropic Claude, but any callable can be plugged in via
  ``ORBIT_CONFIG['AI']['handler']`` (also how the test suite avoids the network).
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-opus-4-8"
DEFAULT_MAX_TOKENS = 1024

_SYSTEM_PROMPT = (
    "You are a senior Django engineer embedded in the Orbit observability dashboard. "
    "Given a captured telemetry event, explain the likely root cause in 2-4 sentences, "
    "then give a concrete, minimal fix (code or config). Be specific and concise. "
    "If information is insufficient, say what else you'd need. Output GitHub-flavored Markdown."
)


def get_ai_config() -> Dict[str, Any]:
    from orbit.conf import get_config

    return get_config().get("AI") or {}


def ai_enabled() -> bool:
    """AI features are usable only when explicitly enabled with a key (or a custom handler)."""
    cfg = get_ai_config()
    if not cfg.get("enabled"):
        return False
    return bool(cfg.get("api_key")) or callable(cfg.get("handler"))


def _build_user_prompt(entry) -> str:
    """Build the user prompt from a MASKED view of the entry."""
    from orbit.utils import mask_sensitive_data

    payload = mask_sensitive_data(entry.payload or {})
    etype = entry.type
    lines = [f"Event type: {etype}", f"Duration: {entry.duration_ms} ms"]

    if etype == "exception":
        lines.append(f"Exception: {payload.get('exception_type')}: {payload.get('message')}")
        frames = payload.get("traceback") or []
        if isinstance(frames, list) and frames:
            lines.append("Traceback (deepest last):")
            for f in frames[-8:]:
                if isinstance(f, dict):
                    lines.append(f"  {f.get('filename')}:{f.get('lineno')} in {f.get('name')} — {f.get('line')}")
    elif etype == "query":
        lines.append(f"SQL: {payload.get('sql')}")
        lines.append(f"Slow: {payload.get('is_slow')} | Duplicate: {payload.get('is_duplicate')} (x{payload.get('duplicate_count', 1)})")
        caller = payload.get("caller") or {}
        lines.append(f"Called from: {caller.get('filename')}:{caller.get('lineno')}")
        lines.append("If this is an N+1 pattern, suggest select_related/prefetch_related.")
    elif etype == "request":
        lines.append(f"{payload.get('method')} {payload.get('full_path') or payload.get('path')} -> {payload.get('status_code')}")
        if payload.get("duplicate_query_count"):
            lines.append(f"Duplicate queries detected: {payload.get('duplicate_query_count')} (likely N+1).")
    else:
        import json

        lines.append("Payload: " + json.dumps(payload, default=str)[:1500])

    return "\n".join(str(line) for line in lines)


def _call_anthropic(system: str, user: str, cfg: Dict[str, Any]) -> str:
    try:
        import anthropic
    except ImportError:
        raise RuntimeError("The 'anthropic' package is required. Install with: pip install django-orbit[ai]")

    client = anthropic.Anthropic(api_key=cfg.get("api_key"))
    resp = client.messages.create(
        model=cfg.get("model", DEFAULT_MODEL),
        max_tokens=cfg.get("max_tokens", DEFAULT_MAX_TOKENS),
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    # Concatenate text blocks
    return "".join(getattr(b, "text", "") for b in resp.content).strip()


def _run_llm(system: str, user: str, cfg: Dict[str, Any]) -> str:
    """Dispatch to the configured handler, else the Anthropic provider."""
    handler = cfg.get("handler")
    if callable(handler):
        return handler(system, user, cfg)
    return _call_anthropic(system, user, cfg)


def _analyze(entry, *, kind: str, system: str, user: str, force: bool = False) -> Dict[str, Any]:
    """
    Generic on-demand LLM analysis cached on the entry under payload['ai'][kind].

    Returns {'ok': True, 'text': markdown, 'cached': bool} or {'ok': False, 'error': str}.
    Never raises.
    """
    if not ai_enabled():
        return {"ok": False, "error": "AI is disabled. Set ORBIT_CONFIG['AI'] = {'enabled': True, 'api_key': '...'}."}

    payload = entry.payload or {}
    cache = payload.get("ai") or {}
    if isinstance(cache, dict) and cache.get(kind) and not force:
        return {"ok": True, "text": cache[kind].get("text", ""), "cached": True}

    cfg = get_ai_config()
    try:
        text = _run_llm(system, user, cfg)
    except Exception as e:
        logger.debug("Orbit AI call failed: %s", e)
        return {"ok": False, "error": str(e)}

    text = (text or "").strip()
    try:
        if not isinstance(cache, dict):
            cache = {}
        cache[kind] = {"text": text, "model": cfg.get("model", DEFAULT_MODEL)}
        payload["ai"] = cache
        entry.payload = payload
        entry.save(update_fields=["payload"])
    except Exception:
        pass

    return {"ok": True, "text": text, "cached": False}


def analyze_entry(entry, force: bool = False) -> Dict[str, Any]:
    """Explain & fix for a single entry (C1)."""
    return _analyze(entry, kind="explain", system=_SYSTEM_PROMPT, user=_build_user_prompt(entry), force=force)


_TRIAGE_PROMPT = (
    "You are triaging a Django exception for an on-call engineer. Respond in this exact "
    "shape:\n**Severity:** <critical|high|medium|low>\n**Category:** <short label>\n"
    "**Why:** <one sentence>\n**Next step:** <one concrete action>"
)


def triage_exception(entry, force: bool = False) -> Dict[str, Any]:
    """Classify an exception's severity/category and suggest a next step (C4)."""
    return _analyze(entry, kind="triage", system=_TRIAGE_PROMPT, user=_build_user_prompt(entry), force=force)


_SUMMARY_PROMPT = (
    "You summarize a single Django request's lifecycle for a developer. In 3-5 sentences: "
    "what the request did, where time went, and anything suspicious (slow/duplicate queries, "
    "errors). Output GitHub-flavored Markdown."
)


def summarize_family(request_entry, force: bool = False) -> Dict[str, Any]:
    """Summarize everything that happened during a request/family (C3)."""
    from orbit.models import OrbitEntry
    from orbit.utils import mask_sensitive_data

    family = request_entry.family_hash
    children = []
    if family:
        children = list(
            OrbitEntry.objects.filter(family_hash=family)
            .exclude(id=request_entry.id)
            .order_by("created_at")[:200]
        )
    by_type: Dict[str, int] = {}
    for c in children:
        by_type[c.type] = by_type.get(c.type, 0) + 1

    rp = mask_sensitive_data(request_entry.payload or {})
    lines = [
        f"Request: {rp.get('method')} {rp.get('full_path') or rp.get('path')} -> {rp.get('status_code')}",
        f"Total duration: {request_entry.duration_ms} ms",
        f"Child events by type: {by_type}",
    ]
    # Highlight the slowest queries for context
    slow = sorted(
        [c for c in children if c.type == OrbitEntry.TYPE_QUERY and c.duration_ms],
        key=lambda c: c.duration_ms or 0,
        reverse=True,
    )[:5]
    if slow:
        lines.append("Slowest queries:")
        for c in slow:
            sql = (c.payload or {}).get("sql", "")
            lines.append(f"  {round(c.duration_ms, 1)}ms — {sql[:120]}")

    return _analyze(request_entry, kind="summary", system=_SUMMARY_PROMPT, user="\n".join(lines), force=force)


_SEARCH_PROMPT = (
    "Translate a developer's natural-language request into Orbit feed filters. "
    "Respond with ONLY a compact JSON object using these optional keys: "
    '"type" (one of: request, query, log, exception, job, command, cache, model, '
    'http_client, dump, mail, signal, redis, gate, transaction, storage), '
    '"status_min" (int, e.g. 500), "path_contains" (string), "since_minutes" (int), '
    '"tag" (string), "q" (free-text fallback). Omit keys you cannot infer. No prose.'
)

_ALLOWED_FILTER_KEYS = {"type", "status_min", "path_contains", "since_minutes", "tag", "q"}


def nl_search(question: str) -> Dict[str, Any]:
    """
    Turn a natural-language question into Orbit feed filters (C2).

    Returns {'ok': True, 'filters': {...}} or {'ok': False, 'error': str}. Never raises.
    """
    if not ai_enabled():
        return {"ok": False, "error": "AI is disabled."}
    if not question or not question.strip():
        return {"ok": False, "error": "Empty question."}

    cfg = get_ai_config()
    try:
        raw = _run_llm(_SEARCH_PROMPT, question.strip(), cfg)
    except Exception as e:
        return {"ok": False, "error": str(e)}

    filters = _parse_filters(raw)
    if not filters:
        return {"ok": False, "error": "Could not interpret the question."}
    return {"ok": True, "filters": filters}


def _parse_filters(raw: str) -> Dict[str, Any]:
    """Extract a JSON object from the model output and keep only known, well-typed keys."""
    import json
    import re

    if not raw:
        return {}
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return {}
    try:
        data = json.loads(match.group(0))
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}

    out: Dict[str, Any] = {}
    for key in _ALLOWED_FILTER_KEYS:
        if key not in data or data[key] in (None, ""):
            continue
        value = data[key]
        if key in ("status_min", "since_minutes"):
            try:
                out[key] = int(value)
            except (TypeError, ValueError):
                continue
        else:
            out[key] = str(value)
    return out


def entry_supports_ai(entry) -> bool:
    """Which entry types get an 'Explain with AI' affordance."""
    if entry.type in ("exception",):
        return True
    if entry.type == "query" and (entry.payload or {}).get("is_slow") or (entry.payload or {}).get("is_duplicate"):
        return True
    if entry.type == "request" and (entry.payload or {}).get("duplicate_query_count"):
        return True
    return False
