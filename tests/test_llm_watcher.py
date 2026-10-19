import sys
import types
from types import SimpleNamespace

from django.test import override_settings

import pytest

from orbit.handlers import set_current_family_hash
from orbit.models import OrbitEntry

pytestmark = pytest.mark.django_db


def _openai_response():
    return SimpleNamespace(
        model="gpt-test",
        usage=SimpleNamespace(input_tokens=12, output_tokens=8, total_tokens=20),
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content="Safe response",
                    tool_calls=[
                        SimpleNamespace(
                            id="call_1",
                            type="function",
                            function=SimpleNamespace(
                                name="lookup_order",
                                arguments='{"api_token": "secret"}',
                            ),
                        )
                    ],
                )
            )
        ],
    )


def test_record_llm_call_is_metadata_only_by_default():
    from orbit.llm import record_llm_call

    set_current_family_hash("fam-llm")
    record_llm_call(
        provider="openai",
        operation="chat.completions",
        response=_openai_response(),
        duration_ms=42.4,
        kwargs={"messages": [{"role": "user", "content": "contains password"}]},
    )
    set_current_family_hash(None)

    entry = OrbitEntry.objects.get(type=OrbitEntry.TYPE_LLM)
    assert entry.family_hash == "fam-llm"
    assert entry.duration_ms == 42.4
    assert entry.payload["provider"] == "openai"
    assert entry.payload["model"] == "gpt-test"
    assert entry.payload["metadata_only"] is True
    assert entry.payload["content_captured"] is False
    assert entry.payload["usage"] == {
        "input_tokens": 12,
        "output_tokens": 8,
        "total_tokens": 20,
    }
    assert entry.payload["tool_calls"] == [
        {"id": "call_1", "type": "function", "name": "lookup_order"}
    ]
    assert "content" not in entry.payload
    assert "arguments" not in entry.payload["tool_calls"][0]
    assert ",llm,openai," == entry.tags


@override_settings(
    ORBIT_CONFIG={
        "ENABLED": True,
        "RECORD_LLM": True,
        "LLM_CAPTURE_CONTENT": True,
        "LLM_CAPTURE_TOOL_CALL_ARGUMENTS": True,
        "LLM_MAX_CONTENT_CHARS": 500,
    }
)
def test_record_llm_call_can_capture_masked_content_when_enabled():
    from orbit.llm import record_llm_call

    record_llm_call(
        provider="openai",
        operation="responses",
        response=_openai_response(),
        kwargs={
            "input": "summarize this",
            "messages": [{"role": "user", "password": "secret"}],
        },
    )

    entry = OrbitEntry.objects.get(type=OrbitEntry.TYPE_LLM)
    assert entry.payload["metadata_only"] is False
    assert entry.payload["content_captured"] is True
    assert (
        entry.payload["content"]["request"]["messages"][0]["password"] == "***HIDDEN***"
    )
    assert entry.payload["tool_calls"][0]["arguments"] == {"api_token": "***HIDDEN***"}


def test_install_llm_watcher_patches_openai_chat_completions(monkeypatch):
    from orbit.llm import install_llm_watcher

    completions_module = types.ModuleType("openai.resources.chat.completions")

    class Completions:
        def create(self, **kwargs):
            return _openai_response()

    completions_module.Completions = Completions
    completions_module.AsyncCompletions = None

    monkeypatch.setitem(sys.modules, "openai", types.ModuleType("openai"))
    monkeypatch.setitem(
        sys.modules, "openai.resources", types.ModuleType("openai.resources")
    )
    monkeypatch.setitem(
        sys.modules, "openai.resources.chat", types.ModuleType("openai.resources.chat")
    )
    monkeypatch.setitem(
        sys.modules, "openai.resources.chat.completions", completions_module
    )

    install_llm_watcher()

    response = Completions().create(model="gpt-test")

    assert response.model == "gpt-test"
    entry = OrbitEntry.objects.get(type=OrbitEntry.TYPE_LLM)
    assert entry.payload["provider"] == "openai"
    assert entry.payload["operation"] == "chat.completions"


def test_patch_method_keys_on_live_method_not_owner_id():
    # Regression: installation used to be skipped when id(owner) matched an owner
    # patched earlier. Python reuses ids after an object is collected, so a fresh
    # class landing on a freed id went unwrapped and recorded nothing. Patching
    # must depend only on the live method's marker, so a second, distinct owner is
    # always wrapped and re-patching the same owner stays idempotent.
    from orbit.llm import _patch_method

    class First:
        def create(self, **kwargs):
            return _openai_response()

    class Second:
        def create(self, **kwargs):
            return _openai_response()

    assert _patch_method(First, "create", "openai", "chat.completions") is True
    assert _patch_method(Second, "create", "openai", "chat.completions") is True
    assert getattr(First.create, "_orbit_llm_patched", False) is True
    assert getattr(Second.create, "_orbit_llm_patched", False) is True
    # Re-patching an already-wrapped method is a no-op.
    assert _patch_method(Second, "create", "openai", "chat.completions") is False


def test_llm_watcher_records_errors_and_reraises(monkeypatch):
    from orbit.llm import install_llm_watcher

    completions_module = types.ModuleType("openai.resources.chat.completions")

    class Completions:
        def create(self, **kwargs):
            raise RuntimeError("provider unavailable")

    completions_module.Completions = Completions
    completions_module.AsyncCompletions = None

    monkeypatch.setitem(sys.modules, "openai", types.ModuleType("openai"))
    monkeypatch.setitem(
        sys.modules, "openai.resources", types.ModuleType("openai.resources")
    )
    monkeypatch.setitem(
        sys.modules, "openai.resources.chat", types.ModuleType("openai.resources.chat")
    )
    monkeypatch.setitem(
        sys.modules, "openai.resources.chat.completions", completions_module
    )

    install_llm_watcher()

    with pytest.raises(RuntimeError, match="provider unavailable"):
        Completions().create(model="gpt-test")

    entry = OrbitEntry.objects.get(type=OrbitEntry.TYPE_LLM)
    assert entry.payload["status"] == "error"
    assert entry.payload["error"]["type"] == "RuntimeError"
