import os

import django
from django.conf import settings


def pytest_configure():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")
    django.setup()

import pytest
from orbit.models import OrbitEntry

@pytest.fixture(autouse=True)
def clean_orbit_entries():
    """Ensure OrbitEntry table is clean before each test."""
    OrbitEntry.objects.all().delete()
    yield
    OrbitEntry.objects.all().delete()
