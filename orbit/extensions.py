"""Neutral, read-only runtime adapter boundary for optional extensions."""

from __future__ import annotations

from typing import Any

from orbit import __version__
from orbit.evidence import EVIDENCE_SCHEMA_VERSION
from orbit.verification import is_valid_verification_id

ADAPTER_CONTRACT_VERSION = "orbit.runtime-adapter.v1"


def get_runtime_adapter_manifest() -> dict[str, Any]:
    """Describe evidence resources without loading optional Pro packages."""
    return {
        "contract_version": ADAPTER_CONTRACT_VERSION,
        "adapter_id": "django-orbit",
        "adapter_version": __version__,
        "evidence_schema_versions": [EVIDENCE_SCHEMA_VERSION],
        "capabilities": {
            "family_evidence.read": {
                "status": "available",
                "schema_versions": [EVIDENCE_SCHEMA_VERSION],
            },
            "capture_health.read": {
                "status": "available",
                "schema_versions": [EVIDENCE_SCHEMA_VERSION],
            },
            "verification_families.read": {
                "status": "available",
                "schema_versions": [EVIDENCE_SCHEMA_VERSION],
            },
        },
    }


def _invalid(reason: str) -> dict[str, Any]:
    return {
        "contract_version": ADAPTER_CONTRACT_VERSION,
        "status": "invalid",
        "reason": reason,
    }


def read_runtime_evidence(
    resource: str, reference: dict[str, str], *, limit: int | None = None
) -> dict[str, Any]:
    """Read a supported resource only through the versioned Evidence API."""
    if resource not in {"family_evidence", "capture_health"}:
        return _invalid("unsupported_resource")
    if limit is not None and (
        isinstance(limit, bool) or not isinstance(limit, int) or limit < 1
    ):
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
        return read_family_evidence(
            family_hash, limit=limit if limit is not None else 1000
        )
    except Exception:
        return {
            "contract_version": ADAPTER_CONTRACT_VERSION,
            "status": "unavailable",
            "reason": "read_failed",
        }


def is_dashboard_request_authorized(request):
    """Expose Orbit dashboard authorization for explicitly mounted extensions."""
    from orbit.mixins import is_orbit_request_authorized

    return is_orbit_request_authorized(request)


def read_verification_families(verification_id: str, *, limit: int = 100):
    """Find request families recorded for one explicit verification run."""
    if not is_valid_verification_id(verification_id):
        return _invalid("invalid_verification_id")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 500:
        return _invalid("invalid_limit")

    try:
        from orbit.conf import get_config
        from orbit.backends import get_storage_db_alias
        from orbit.models import OrbitEntry
        from orbit.watchers import _table_exists, cachalot_disabled

        if not get_config().get("RECORD_VERIFICATION_CONTEXT", False):
            return {
                "contract_version": ADAPTER_CONTRACT_VERSION,
                "status": "unavailable",
                "reason": "verification_context_disabled",
            }
        if not _table_exists():
            return {
                "contract_version": ADAPTER_CONTRACT_VERSION,
                "status": "unavailable",
                "reason": "storage_unavailable",
            }
        queryset = (
            OrbitEntry.objects.using(get_storage_db_alias())
            .filter(
                type=OrbitEntry.TYPE_REQUEST, payload__verification_id=verification_id
            )
            .exclude(family_hash__isnull=True)
            .exclude(family_hash="")
            .order_by("created_at", "id")
            .values_list("family_hash", flat=True)[:limit]
        )
        with cachalot_disabled():
            family_hashes = tuple(dict.fromkeys(queryset))
    except Exception:
        return {
            "contract_version": ADAPTER_CONTRACT_VERSION,
            "status": "unavailable",
            "reason": "read_failed",
        }

    return {
        "contract_version": ADAPTER_CONTRACT_VERSION,
        "status": "ok",
        "reason": None,
        "verification_id": verification_id,
        "family_hashes": family_hashes,
    }
