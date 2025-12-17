
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
def test_http_client_watcher():
    """Test HTTP client request recording."""
    
    # We need to mock the actual network call to avoid external requests
    # But we need the watcher to be active.
    # The watcher patches requests.Session.request.
    # Inside, it calls original_request.
    
    # The best way to mock the response without bypassing the watcher 
    # (which wraps Session.request) is to mount a mock adapter on the session.
    
    adapter = requests.adapters.HTTPAdapter()
    adapter.send = MagicMock()
    
    # Force install watcher to be sure it's active in this test process context
    # (Since pytest might reuse process where it was patched then unpatched or flag set)
    import orbit.watchers
    orbit.watchers._requests_patched = False
    install_http_client_watcher()
    
    # Create a dummy response
    mock_response = requests.Response()
    mock_response.status_code = 201
    mock_response._content = b'{"id": 123}'
    adapter.send.return_value = mock_response
    
    session = requests.Session()
    session.mount("https://", adapter)
    
    # Make request
    session.post("https://api.example.com/users", json={"name": "test"})
    
    # Verify Orbit entry
    entry = OrbitEntry.objects.filter(type=OrbitEntry.TYPE_HTTP_CLIENT).first()
    assert entry is not None
    assert entry.payload['method'] == 'POST'
    assert entry.payload['url'] == 'https://api.example.com/users'
    assert entry.payload['status_code'] == 201
    assert entry.payload['response_size'] == 13
