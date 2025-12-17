
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
    assert data["type"] == OrbitEntry.TYPE_REQUEST
    assert data["payload"]["foo"] == "bar"
    assert data["id"] == str(entry.id)

@pytest.mark.django_db
def test_export_not_found(client):
    import uuid
    random_id = uuid.uuid4()
    url = reverse("orbit:export", args=[random_id])
    
    response = client.get(url)
    assert response.status_code == 404
