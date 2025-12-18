
import pytest
import requests
from unittest.mock import MagicMock, patch
from example_project.demo.models import Book
from orbit.models import OrbitEntry
from orbit.watchers import install_model_watcher, install_http_client_watcher

@pytest.fixture(autouse=True)
def enable_watchers():
    """Ensure watchers are installed for tests."""
    install_model_watcher()
    install_http_client_watcher()
    yield

@pytest.mark.django_db
def test_model_watcher_lifecycle():
    """Test model creation, update, and deletion."""
    # 1. Create
    book = Book.objects.create(
        title="Test Book", 
        author="Test Author",
    )
    
    assert OrbitEntry.objects.filter(type=OrbitEntry.TYPE_MODEL).count() == 1
    entry = OrbitEntry.objects.first()
    assert entry.payload['action'] == 'created'
    assert entry.payload['model'] == 'demo.book'
    assert entry.payload['pk'] == str(book.pk)
    
    # 2. Update
    OrbitEntry.objects.all().delete()
    book.title = "Updated Title"
    book.save()
    
    assert OrbitEntry.objects.count() == 1
    entry = OrbitEntry.objects.first()
    assert entry.payload['action'] == 'updated'
    assert 'changes' in entry.payload
    assert entry.payload['changes']['title']['old'] == "Test Book"
    assert entry.payload['changes']['title']['new'] == "Updated Title"
    
    # 3. Delete
    OrbitEntry.objects.all().delete()
    book.delete()
    
    assert OrbitEntry.objects.count() == 1
    entry = OrbitEntry.objects.first()
    assert entry.payload['action'] == 'deleted'

@pytest.mark.django_db
def test_http_client_watcher(settings):
    """Test HTTP client request recording via direct function call."""
    from orbit.watchers import record_http_client_request
    
    # Ensure HTTP client recording is enabled
    settings.ORBIT_CONFIG = {
        "ENABLED": True,
        "RECORD_HTTP_CLIENT": True,
    }
    
    # Directly call the record function (simulating what the watcher does)
    record_http_client_request(
        method="POST",
        url="https://api.example.com/users",
        status_code=201,
        duration_ms=150.5,
        request_headers={"Content-Type": "application/json"},
        response_size=13,
        error=None,
    )
    
    # Verify Orbit entry was created
    entry = OrbitEntry.objects.filter(type=OrbitEntry.TYPE_HTTP_CLIENT).first()
    assert entry is not None, "Expected HTTP_CLIENT entry"
    assert entry.payload['method'] == 'POST'
    assert entry.payload['url'] == 'https://api.example.com/users'
    assert entry.payload['status_code'] == 201
    assert entry.duration_ms == 150.5
