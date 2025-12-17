
import pytest
from django.urls import reverse
from orbit.models import OrbitEntry

@pytest.mark.django_db
def test_dashboard_access(client):
    """Test that dashboard loads correctly."""
    url = reverse("orbit:dashboard")
    response = client.get(url)
    assert response.status_code == 200
    assert "Orbit" in response.content.decode()

@pytest.mark.django_db
def test_request_middleware(client):
    """Test that requests are captured by middleware."""
    # We must ensure OrbitMiddleware is active. 
    # example_project.settings has it.
    
    # Make a request to a URL that should be captured
    # Avoid orbit/ urls as they might be ignored by default config?
    # orbit/conf.py says IGNORE_PATHS defaults to ["/orbit/", ...]
    # So we should request something else.
    
    response = client.get("/", follow=True) # Home of example_project
    
    # Check if OrbitEntry was created
    entries = OrbitEntry.objects.filter(type=OrbitEntry.TYPE_REQUEST)
    assert entries.exists()
    
    entry = entries.latest('created_at')
    assert entry.payload['method'] == 'GET'
    assert entry.payload['status_code'] == response.status_code

@pytest.mark.django_db
def test_pagination_htmx_logic(client):
    """Test pagination HTMX endpoint returns correct page."""
    # Create enough entries to force pagination (25 per page)
    # We'll create 30 entries.
    # Sorted by -created_at.
    # Page 1: 0-24 (indices 0..24? No, count=25)
    # Page 2: 25-29 (5 items)
    
    # Let's verify existing count first
    initial_count = OrbitEntry.objects.count()
    
    for i in range(30):
        OrbitEntry.objects.create(type=OrbitEntry.TYPE_LOG, payload={"message": f"PaginationTest {i}"})
        
    url = reverse("orbit:feed")
    response = client.get(url, {"page": 2, "per_page": 25, "type": "log"}, headers={"HX-Request": "true"})
    
    assert response.status_code == 200
    content = response.content.decode()
    
    # Page 2 should contain the OLDEST entries if we order by -created_at?
    # No, typically:
    # Page 1 = Newest 25
    # Page 2 = Remaining 5 (Oldest)
    # created_at increases. 
    # Test 0 (Oldest) -> Test 29 (Newest)
    # Page 1: Test 29 down to Test 5 (25 items)
    # Page 2: Test 4 down to Test 0 (5 items)
    
    assert "PaginationTest 4" in content
    assert "PaginationTest 29" not in content
