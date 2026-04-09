"""
Tests for HTML email preview (v0.8.1).

Covers:
- html_body captured correctly from EmailMultiAlternatives
- plain-text-only email captured without html_body key
- 100 KB limit on html_body
- body plain-text limit increased to 10 000 chars
- record_mail skips when table missing / RECORD_MAIL disabled
"""

import pytest
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.test import override_settings
from unittest.mock import patch

import orbit.watchers as watchers
from orbit.models import OrbitEntry


# ---------------------------------------------------------------------------
# Override conftest autouse fixture
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_orbit_entries(request):
    if request.node.get_closest_marker("django_db"):
        OrbitEntry.objects.all().delete()
    yield
    if request.node.get_closest_marker("django_db"):
        OrbitEntry.objects.all().delete()


# ---------------------------------------------------------------------------
# Payload capture
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@override_settings(ORBIT_CONFIG={"ENABLED": True, "RECORD_MAIL": True})
def test_html_body_captured_from_multi_alternatives():
    """EmailMultiAlternatives HTML alternative is stored in payload['html_body']."""
    html = "<html><body><h1>Hello</h1></body></html>"
    msg = EmailMultiAlternatives(
        subject="Test",
        body="Hello (plain)",
        from_email="from@example.com",
        to=["to@example.com"],
    )
    msg.attach_alternative(html, "text/html")

    watchers.record_mail(msg)

    entry = OrbitEntry.objects.filter(type="mail").first()
    assert entry is not None
    assert entry.payload["html_body"] == html


@pytest.mark.django_db
@override_settings(ORBIT_CONFIG={"ENABLED": True, "RECORD_MAIL": True})
def test_plain_text_email_has_no_html_body():
    """Plain-text EmailMessage should not set html_body in payload."""
    msg = EmailMessage(
        subject="Plain only",
        body="Just text",
        from_email="from@example.com",
        to=["to@example.com"],
    )
    watchers.record_mail(msg)

    entry = OrbitEntry.objects.filter(type="mail").first()
    assert entry is not None
    assert "html_body" not in entry.payload


@pytest.mark.django_db
@override_settings(ORBIT_CONFIG={"ENABLED": True, "RECORD_MAIL": True})
def test_plain_text_body_captured():
    """Plain-text body is stored in payload['body']."""
    msg = EmailMessage(
        subject="S",
        body="Hello world",
        from_email="from@example.com",
        to=["to@example.com"],
    )
    watchers.record_mail(msg)

    entry = OrbitEntry.objects.filter(type="mail").first()
    assert entry.payload["body"] == "Hello world"


@pytest.mark.django_db
@override_settings(ORBIT_CONFIG={"ENABLED": True, "RECORD_MAIL": True})
def test_html_body_truncated_at_100k():
    """html_body is capped at 100 000 characters."""
    html = "x" * 200_000
    msg = EmailMultiAlternatives(
        subject="Big", body="plain", from_email="a@b.com", to=["c@d.com"]
    )
    msg.attach_alternative(html, "text/html")

    watchers.record_mail(msg)

    entry = OrbitEntry.objects.filter(type="mail").first()
    assert len(entry.payload["html_body"]) == 100_000


@pytest.mark.django_db
@override_settings(ORBIT_CONFIG={"ENABLED": True, "RECORD_MAIL": True})
def test_body_truncated_at_10k():
    """Plain-text body is capped at 10 000 characters."""
    msg = EmailMessage(
        subject="S", body="y" * 20_000, from_email="a@b.com", to=["c@d.com"]
    )
    watchers.record_mail(msg)

    entry = OrbitEntry.objects.filter(type="mail").first()
    assert len(entry.payload["body"]) == 10_000


@pytest.mark.django_db
@override_settings(ORBIT_CONFIG={"ENABLED": True, "RECORD_MAIL": True})
def test_email_headers_captured():
    """to, cc, bcc, subject, from_email all stored."""
    msg = EmailMultiAlternatives(
        subject="Invoice #42",
        body="See attached",
        from_email="billing@company.com",
        to=["alice@example.com", "bob@example.com"],
        cc=["manager@example.com"],
        bcc=["archive@company.com"],
    )
    watchers.record_mail(msg)

    entry = OrbitEntry.objects.filter(type="mail").first()
    p = entry.payload
    assert p["subject"] == "Invoice #42"
    assert p["from_email"] == "billing@company.com"
    assert "alice@example.com" in p["to"]
    assert "bob@example.com" in p["to"]
    assert p["cc"] == ["manager@example.com"]
    assert p["bcc"] == ["archive@company.com"]


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------

def test_record_mail_skips_when_table_missing(monkeypatch):
    monkeypatch.setattr(watchers, "_table_exists", lambda: False)
    with patch.object(OrbitEntry.objects, "create") as mock_create:
        msg = EmailMessage(subject="S", body="B", to=["a@b.com"])
        watchers.record_mail(msg)
    mock_create.assert_not_called()


@override_settings(ORBIT_CONFIG={"ENABLED": True, "RECORD_MAIL": False})
def test_record_mail_skips_when_disabled(monkeypatch):
    monkeypatch.setattr(watchers, "_table_exists", lambda: True)
    with patch.object(OrbitEntry.objects, "create") as mock_create:
        msg = EmailMessage(subject="S", body="B", to=["a@b.com"])
        watchers.record_mail(msg)
    mock_create.assert_not_called()


def test_record_mail_writes_when_table_present(monkeypatch):
    monkeypatch.setattr(watchers, "_table_exists", lambda: True)
    with patch.object(OrbitEntry.objects, "create") as mock_create:
        msg = EmailMessage(subject="S", body="B", to=["a@b.com"])
        watchers.record_mail(msg)
    mock_create.assert_called_once()
