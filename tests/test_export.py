
import pytest
import json
from orbit.models import OrbitEntry
from django.urls import reverse

@pytest.mark.django_db
def test_export_single_entry(client):
    # Create entry
    entry = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        payload={"foo": "bar", "status": 200}
    )
    
    # Get export URL (we assume we'll name it orbit:export)
    url = reverse("orbit:export", args=[entry.id])
    
    response = client.get(url)
    
    # Check basics
    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"
    assert f'attachment; filename="orbit_entry_{entry.id}.json"' in response["Content-Disposition"]
    
    # Check content
    data = json.loads(response.content)
    
    # New structure: {"entry": {...}, "related": [...]}
    assert "entry" in data
    assert "related" in data
    assert isinstance(data["related"], list)
    
    # Check entry data
    assert data["entry"]["type"] == OrbitEntry.TYPE_REQUEST
    assert data["entry"]["payload"]["foo"] == "bar"
    assert data["entry"]["id"] == str(entry.id)

@pytest.mark.django_db
def test_export_related_entries(client):
    """Test that related entries (same family_hash) are included."""
    family_hash = "test_family_123"
    
    # Parent (Request)
    parent = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        family_hash=family_hash,
        payload={"url": "/test"}
    )
    
    # Child (Query)
    child = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_QUERY,
        family_hash=family_hash,
        payload={"sql": "SELECT *"}
    )
    
    # Unrelated
    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        family_hash="other_family",
        payload={}
    )
    
    url = reverse("orbit:export", args=[parent.id])
    response = client.get(url)
    assert response.status_code == 200
    
    data = json.loads(response.content)
    
    # Check parent
    assert data["entry"]["id"] == str(parent.id)
    
    # Check related
    assert len(data["related"]) == 1
    assert data["related"][0]["id"] == str(child.id)
    assert data["related"][0]["type"] == OrbitEntry.TYPE_QUERY

@pytest.mark.django_db
def test_export_not_found(client):
    import uuid
    random_id = uuid.uuid4()
    url = reverse("orbit:export", args=[random_id])
    
    response = client.get(url)
    assert response.status_code == 404

@pytest.mark.django_db
def test_export_all_streaming(client):
    """Test bulk export streaming."""
    # Create mix of entries
    OrbitEntry.objects.create(type=OrbitEntry.TYPE_REQUEST, payload={"a": 1})
    OrbitEntry.objects.create(type=OrbitEntry.TYPE_QUERY, payload={"b": 2})
    
    url = reverse("orbit:export_all")
    response = client.get(url)
    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"
    assert "orbit_export_all.json" in response["Content-Disposition"]
    
    # Consume stream
    content = b"".join(response.streaming_content).decode('utf-8')
    data = json.loads(content)
    
    assert isinstance(data, list)
    assert len(data) == 2
    
    # Test Filtering
    url_filtered = reverse("orbit:export_all") + f"?type={OrbitEntry.TYPE_REQUEST}"
    response_filtered = client.get(url_filtered)
    content_filtered = b"".join(response_filtered.streaming_content).decode('utf-8')
    data_filtered = json.loads(content_filtered)
    
    assert len(data_filtered) == 1
    assert data_filtered[0]["type"] == OrbitEntry.TYPE_REQUEST
