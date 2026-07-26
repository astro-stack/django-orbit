"""Opt-in correlation between a verification run and captured request families."""

import pytest
from django.http import HttpResponse
from django.test import RequestFactory, override_settings

from orbit.extensions import read_verification_families
from orbit.middleware import OrbitMiddleware
from orbit.models import OrbitEntry

pytestmark = pytest.mark.django_db


@override_settings(
    ORBIT_CONFIG={"RECORD_VERIFICATION_CONTEXT": True, "STORAGE_LIMIT": 1000}
)
def test_opted_in_verification_header_is_correlated_and_redacted():
    request = RequestFactory().get(
        "/checkout/", HTTP_X_ORBIT_VERIFICATION="run_checkout_2026"
    )

    OrbitMiddleware(lambda received: HttpResponse("ok"))(request)

    entry = OrbitEntry.objects.requests().get(payload__path="/checkout/")
    assert entry.payload["verification_id"] == "run_checkout_2026"
    assert entry.payload["headers"]["X-Orbit-Verification"] == "***HIDDEN***"

    result = read_verification_families("run_checkout_2026")
    assert result["status"] == "ok"
    assert result["family_hashes"] == (entry.family_hash,)


@override_settings(
    ORBIT_CONFIG={"RECORD_VERIFICATION_CONTEXT": True, "STORAGE_LIMIT": 1000}
)
def test_invalid_verification_header_is_neither_stored_nor_queryable():
    request = RequestFactory().get(
        "/checkout/", HTTP_X_ORBIT_VERIFICATION="run checkout\nprivate"
    )

    OrbitMiddleware(lambda received: HttpResponse("ok"))(request)

    entry = OrbitEntry.objects.requests().get(payload__path="/checkout/")
    assert "verification_id" not in entry.payload
    assert read_verification_families("run checkout")["status"] == "invalid"


@override_settings(ORBIT_CONFIG={"STORAGE_LIMIT": 1000})
def test_verification_context_is_disabled_by_default():
    request = RequestFactory().get(
        "/checkout/", HTTP_X_ORBIT_VERIFICATION="run_checkout_2026"
    )

    OrbitMiddleware(lambda received: HttpResponse("ok"))(request)

    entry = OrbitEntry.objects.requests().get(payload__path="/checkout/")
    assert "verification_id" not in entry.payload
    assert read_verification_families("run_checkout_2026") == {
        "contract_version": "orbit.runtime-adapter.v1",
        "status": "unavailable",
        "reason": "verification_context_disabled",
    }
