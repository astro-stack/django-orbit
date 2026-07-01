"""
AI/LLM watcher primitives for Django Orbit.

The watcher is metadata-first by default. It records provider, model, token
counts, latency, status and tool-call names, but it does not store prompts,
responses or tool-call arguments unless explicitly enabled in ORBIT_CONFIG.
"""

from __future__ import annotations

import functools
import importlib
import inspect
import json
import time
from typing import Any, Callable

from orbit.conf import get_config
from orbit.utils import mask_sensitive_data, normalize_tags, serialize_for_json

_PATCHED: set[tuple[int, str]] = set()


def _get_value(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _truncate(value: Any, max_chars: int) -> Any:
    serialized = serialize_for_json(value)
    if serialized is None:
        return None
    text = serialized if isinstance(serialized, str) else repr(serialized)
    if len(text) <= max_chars:
        return serialized
    return {
        "truncated": True,
        "original_length": len(text),
        "preview": text[:max_chars],
    }


def _extract_usage(response: Any) -> dict[str, Any]:
    usage = _get_value(response, "usage", {}) or {}
    input_tokens = (
        _get_value(usage, "input_tokens")
        or _get_value(usage, "prompt_tokens")
        or _get_value(usage, "input_token_count")
    )
    output_tokens = (
        _get_value(usage, "output_tokens")
        or _get_value(usage, "completion_tokens")
        or _get_value(usage, "output_token_count")
    )
    total_tokens = _get_value(usage, "total_tokens")
    if total_tokens is None and (input_tokens is not None or output_tokens is not None):
        total_tokens = (input_tokens or 0) + (output_tokens or 0)
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
    }


def _iter_choices(response: Any) -> list[Any]:
    choices = _get_value(response, "choices", []) or []
    return list(choices) if isinstance(choices, (list, tuple)) else []


def _extract_tool_calls(
    response: Any, include_arguments: bool = False
) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    for choice in _iter_choices(response):
        message = _get_value(choice, "message", {}) or {}
        for call in _get_value(message, "tool_calls", []) or []:
            function = _get_value(call, "function", {}) or {}
            item = {
                "id": _get_value(call, "id"),
                "type": _get_value(call, "type"),
                "name": _get_value(function, "name") or _get_value(call, "name"),
            }
            if include_arguments:
                item["arguments"] = _safe_arguments(_get_value(function, "arguments"))
            calls.append({k: v for k, v in item.items() if v is not None})

    for block in _get_value(response, "content", []) or []:
        if _get_value(block, "type") != "tool_use":
            continue
        item = {
            "id": _get_value(block, "id"),
            "type": "tool_use",
            "name": _get_value(block, "name"),
        }
        if include_arguments:
            item["arguments"] = _safe_arguments(_get_value(block, "input"))
        calls.append({k: v for k, v in item.items() if v is not None})

    for item in _get_value(response, "output", []) or []:
        if _get_value(item, "type") not in {"function_call", "tool_call"}:
            continue
        call = {
            "id": _get_value(item, "id") or _get_value(item, "call_id"),
            "type": _get_value(item, "type"),
            "name": _get_value(item, "name"),
        }
        if include_arguments:
            call["arguments"] = _safe_arguments(_get_value(item, "arguments"))
        calls.append({k: v for k, v in call.items() if v is not None})

    return calls


def _safe_arguments(value: Any) -> Any:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except Exception:
            pass
    return mask_sensitive_data(serialize_for_json(value))


def _extract_response_text(response: Any) -> Any:
    output_text = _get_value(response, "output_text")
    if output_text:
        return output_text
    texts = []
    for choice in _iter_choices(response):
        message = _get_value(choice, "message", {}) or {}
        content = _get_value(message, "content")
        if content:
            texts.append(content)
    if texts:
        return texts
    content = _get_value(response, "content")
    if content:
        return content
    return None


def _build_payload(
    *,
    provider: str,
    operation: str,
    model: str | None = None,
    duration_ms: float | None = None,
    status: str = "success",
    response: Any = None,
    error: BaseException | None = None,
    kwargs: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = get_config()
    kwargs = kwargs or {}
    include_content = bool(config.get("LLM_CAPTURE_CONTENT", False))
    include_tool_args = bool(config.get("LLM_CAPTURE_TOOL_CALL_ARGUMENTS", False))
    max_chars = int(config.get("LLM_MAX_CONTENT_CHARS", 2000) or 2000)

    payload = {
        "provider": provider,
        "operation": operation,
        "model": model or _get_value(response, "model") or kwargs.get("model"),
        "status": status,
        "metadata_only": not include_content,
        "content_captured": include_content,
        "tool_call_arguments_captured": include_tool_args,
        "usage": _extract_usage(response),
        "tool_calls": _extract_tool_calls(response, include_tool_args),
    }

    if duration_ms is not None:
        payload["duration_ms"] = round(duration_ms, 3)

    if error is not None:
        payload["error"] = {
            "type": type(error).__name__,
            "message": str(error),
        }

    if metadata:
        payload["metadata"] = metadata

    if include_content:
        content = {
            "request": {
                key: kwargs.get(key)
                for key in ("messages", "input", "prompt", "system")
                if key in kwargs
            },
            "response": _extract_response_text(response),
        }
        payload["content"] = mask_sensitive_data(_truncate(content, max_chars))

    return serialize_for_json(payload)


def record_llm_call(
    *,
    provider: str,
    operation: str,
    model: str | None = None,
    duration_ms: float | None = None,
    status: str = "success",
    response: Any = None,
    error: BaseException | None = None,
    kwargs: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    config = get_config()
    if not config.get("ENABLED", True) or not config.get("RECORD_LLM", True):
        return

    from orbit.watchers import _table_exists

    if not _table_exists():
        return

    from orbit.handlers import get_current_family_hash
    from orbit.models import OrbitEntry
    from orbit.watchers import cachalot_disabled

    payload = _build_payload(
        provider=provider,
        operation=operation,
        model=model,
        duration_ms=duration_ms,
        status=status,
        response=response,
        error=error,
        kwargs=kwargs,
        metadata=metadata,
    )

    try:
        with cachalot_disabled():
            OrbitEntry.objects.create(
                type=OrbitEntry.TYPE_LLM,
                family_hash=get_current_family_hash(),
                payload=payload,
                duration_ms=duration_ms,
                tags=normalize_tags(["llm", provider]),
            )
    except Exception:
        pass


def _patch_method(owner: Any, method_name: str, provider: str, operation: str) -> bool:
    original = getattr(owner, method_name, None)
    if original is None or getattr(original, "_orbit_llm_patched", False):
        return False

    key = (id(owner), method_name)
    if key in _PATCHED:
        return False

    if inspect.iscoroutinefunction(original):

        @functools.wraps(original)
        async def async_wrapper(self, *args, **kwargs):
            start = time.perf_counter()
            try:
                response = await original(self, *args, **kwargs)
            except Exception as exc:
                duration_ms = (time.perf_counter() - start) * 1000
                record_llm_call(
                    provider=provider,
                    operation=operation,
                    duration_ms=duration_ms,
                    status="error",
                    error=exc,
                    kwargs=kwargs,
                )
                raise
            duration_ms = (time.perf_counter() - start) * 1000
            record_llm_call(
                provider=provider,
                operation=operation,
                duration_ms=duration_ms,
                response=response,
                kwargs=kwargs,
            )
            return response

        async_wrapper._orbit_llm_patched = True
        setattr(owner, method_name, async_wrapper)
    else:

        @functools.wraps(original)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                response = original(*args, **kwargs)
            except Exception as exc:
                duration_ms = (time.perf_counter() - start) * 1000
                record_llm_call(
                    provider=provider,
                    operation=operation,
                    duration_ms=duration_ms,
                    status="error",
                    error=exc,
                    kwargs=kwargs,
                )
                raise
            duration_ms = (time.perf_counter() - start) * 1000
            record_llm_call(
                provider=provider,
                operation=operation,
                duration_ms=duration_ms,
                response=response,
                kwargs=kwargs,
            )
            return response

        wrapper._orbit_llm_patched = True
        setattr(owner, method_name, wrapper)

    _PATCHED.add(key)
    return True


def _import_optional(path: str) -> Any:
    try:
        return importlib.import_module(path)
    except Exception:
        return None


def _patch_openai() -> int:
    patched = 0
    legacy = _import_optional("openai")
    if legacy is not None:
        chat_completion = getattr(legacy, "ChatCompletion", None)
        if chat_completion is not None:
            patched += int(
                _patch_method(chat_completion, "create", "openai", "chat.completions")
            )

    completions = _import_optional("openai.resources.chat.completions")
    if completions is not None:
        for class_name in ("Completions", "AsyncCompletions"):
            owner = getattr(completions, class_name, None)
            if owner is not None:
                patched += int(
                    _patch_method(owner, "create", "openai", "chat.completions")
                )

    responses = _import_optional("openai.resources.responses")
    if responses is not None:
        for class_name in ("Responses", "AsyncResponses"):
            owner = getattr(responses, class_name, None)
            if owner is not None:
                patched += int(_patch_method(owner, "create", "openai", "responses"))

    return patched


def _patch_anthropic() -> int:
    patched = 0
    messages = _import_optional("anthropic.resources.messages")
    if messages is not None:
        for class_name in ("Messages", "AsyncMessages"):
            owner = getattr(messages, class_name, None)
            if owner is not None:
                patched += int(_patch_method(owner, "create", "anthropic", "messages"))
    return patched


def install_llm_watcher() -> None:
    """Patch supported AI SDKs when installed."""
    config = get_config()
    if not config.get("RECORD_LLM", True):
        return

    _patch_openai()
    _patch_anthropic()
