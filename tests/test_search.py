
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
    assert str(entry1.id) in response.content.decode()
    assert str(entry2.id) not in response.content.decode()

@pytest.mark.django_db
def test_search_by_text_content(client):
    # Create entries
    OrbitEntry.objects.create(payload={"message": "Hello World", "user": "alice"})
    OrbitEntry.objects.create(payload={"message": "Foo Bar", "user": "bob"})
    
    # Search for "World"
    response = client.get(reverse("orbit:feed"), {"q": "World"})
    assert response.status_code == 200
    assert "Hello World" in response.content.decode()
    assert "Foo Bar" not in response.content.decode()
    
    # Search for "bob"
    response = client.get(reverse("orbit:feed"), {"q": "bob"})
    assert response.status_code == 200
    assert "Foo Bar" in response.content.decode()
    
    # Search case insensitive "world"
    response = client.get(reverse("orbit:feed"), {"q": "world"})
    assert "Hello World" in response.content.decode()

