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


def analyze_entry(entry, force: bool = False) -> Dict[str, Any]:
    """
    Return {'ok': True, 'text': markdown, 'cached': bool} or {'ok': False, 'error': str}.

    Never raises. Result is cached in entry.payload['ai'] so repeat views are free.
    """
    if not ai_enabled():
        return {"ok": False, "error": "AI is disabled. Set ORBIT_CONFIG['AI'] = {'enabled': True, 'api_key': '...'}."}

    payload = entry.payload or {}
    cached = payload.get("ai")
    if cached and not force:
        return {"ok": True, "text": cached.get("text", ""), "cached": True}

    cfg = get_ai_config()
    handler = cfg.get("handler")
    user = _build_user_prompt(entry)
    try:
        if callable(handler):
            text = handler(_SYSTEM_PROMPT, user, cfg)
        else:
            text = _call_anthropic(_SYSTEM_PROMPT, user, cfg)
    except Exception as e:
        logger.debug("Orbit AI call failed: %s", e)
        return {"ok": False, "error": str(e)}

    text = (text or "").strip()
    # Cache on the entry (derived data under a dedicated key); never break on failure.
    try:
        payload["ai"] = {"text": text, "model": cfg.get("model", DEFAULT_MODEL)}
        entry.payload = payload
        entry.save(update_fields=["payload"])
    except Exception:
        pass

    return {"ok": True, "text": text, "cached": False}


def entry_supports_ai(entry) -> bool:
    """Which entry types get an 'Explain with AI' affordance."""
    if entry.type in ("exception",):
        return True
    if entry.type == "query" and (entry.payload or {}).get("is_slow") or (entry.payload or {}).get("is_duplicate"):
        return True
    if entry.type == "request" and (entry.payload or {}).get("duplicate_query_count"):
        return True
    return False
