"""Neutral, read-only runtime adapter boundary for optional extensions."""

from __future__ import annotations

from typing import Any

from orbit import __version__
from orbit.evidence import EVIDENCE_SCHEMA_VERSION

ADAPTER_CONTRACT_VERSION = "orbit.runtime-adapter.v1"


def get_runtime_adapter_manifest() -> dict[str, Any]:
    """Describe evidence resources without loading optional Pro packages."""
    return {
        "contract_version": ADAPTER_CONTRACT_VERSION,
        "adapter_id": "django-orbit",
        "adapter_version": __version__,
        "evidence_schema_versions": [EVIDENCE_SCHEMA_VERSION],
        "capabilities": {
            "family_evidence.read": {"status": "available", "schema_versions": [EVIDENCE_SCHEMA_VERSION]},
            "capture_health.read": {"status": "available", "schema_versions": [EVIDENCE_SCHEMA_VERSION]},
            "release_window.compare": {"status": "unavailable", "reason": "provided_by_orbit_pro"},
        },
    }


def _invalid(reason: str) -> dict[str, Any]:
    return {"contract_version": ADAPTER_CONTRACT_VERSION, "status": "invalid", "reason": reason}


def read_runtime_evidence(resource: str, reference: dict[str, str], *, limit: int | None = None) -> dict[str, Any]:
    """Read a supported resource only through the versioned Evidence API."""
    if resource not in {"family_evidence", "capture_health"}:
        return _invalid("unsupported_resource")
    if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int) or limit < 1):
        return _invalid("invalid_limit")
    if not isinstance(reference, dict):
        return _invalid("invalid_reference")
    try:
        from orbit.evidence import read_capture_health, read_family_evidence
        if resource == "capture_health":
            return read_capture_health()
        family_hash = reference.get("family_hash")
        if not isinstance(family_hash, str) or not family_hash:
            return _invalid("invalid_reference")
        return read_family_evidence(family_hash, limit=limit if limit is not None else 1000)
    except Exception:
        return {"contract_version": ADAPTER_CONTRACT_VERSION, "status": "unavailable", "reason": "read_failed"}
