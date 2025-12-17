
import pytest
import uuid
from orbit.models import OrbitEntry
from django.urls import reverse
from django.db.models.functions import Cast
from django.db.models import TextField

@pytest.mark.django_db
def test_search_by_uuid(client):
    # Create entries
    entry1 = OrbitEntry.objects.create(payload={"message": "First"})
    entry2 = OrbitEntry.objects.create(payload={"message": "Second"})
    
    # Search by UUID
    response = client.get(reverse("orbit:feed"), {"q": str(entry1.id)})
    
    assert response.status_code == 200
    if hasattr(response, 'render'):
        response.render()
    
    assert str(entry1.id) in response.content.decode()
    assert str(entry2.id) not in response.content.decode()

@pytest.mark.django_db
def test_search_by_text_content(client):
    # Create entries
    OrbitEntry.objects.create(type=OrbitEntry.TYPE_LOG, payload={"message": "Hello World", "user": "alice"})
    OrbitEntry.objects.create(type=OrbitEntry.TYPE_LOG, payload={"message": "Foo Bar", "user": "bob"})
    
    # Search for "World"
    response = client.get(reverse("orbit:feed"), {"q": "World"})
    assert response.status_code == 200
    if hasattr(response, 'render'):
        response.render()
        
    content = response.content.decode()
        
    assert "Hello World" in content
    assert "Foo Bar" not in content
    
    # Search for "bob"
    response = client.get(reverse("orbit:feed"), {"q": "bob"})
    assert response.status_code == 200
    if hasattr(response, 'render'):
        response.render()
    assert "Foo Bar" in response.content.decode()
    
    # Search case insensitive "world"
    response = client.get(reverse("orbit:feed"), {"q": "world"})
    if hasattr(response, 'render'):
        response.render()
    assert "Hello World" in response.content.decode()

