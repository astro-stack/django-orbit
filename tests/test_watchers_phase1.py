
import pytest
from django.core.cache import cache
from django.core.management import call_command
from orbit.models import OrbitEntry
from orbit.watchers import install_cache_watcher, install_command_watcher

@pytest.fixture(autouse=True)
def enable_watchers():
    """Ensure watchers are installed for tests."""
    install_cache_watcher()
    install_command_watcher()
    yield

@pytest.mark.django_db
def test_cache_watcher_ops():
    """Test basic cache operations recording."""
    # Test SET
    cache.set("test_key", "test_value", 60)
    
    assert OrbitEntry.objects.filter(type=OrbitEntry.TYPE_CACHE).count() == 1
    entry = OrbitEntry.objects.first()
    assert entry.payload['operation'] == 'set'
    assert entry.payload['key'] == 'test_key'
    assert entry.payload['ttl'] == 60

    # Test GET (hit)
    OrbitEntry.objects.all().delete()
    val = cache.get("test_key")
    assert val == "test_value"
    
    assert OrbitEntry.objects.count() == 1
    entry = OrbitEntry.objects.first()
    assert entry.payload['operation'] == 'get'
    assert entry.payload['hit'] is True

    # Test GET (miss)
    OrbitEntry.objects.all().delete()
    val = cache.get("missing_key")
    assert val is None
    
    entry = OrbitEntry.objects.first()
    assert entry.payload['operation'] == 'get'
    assert entry.payload['hit'] is False

@pytest.mark.django_db
def test_cache_sentinel_fix():
    """Test that default values work correctly with sentinel fix."""
    key = "default_test_key"
    default_val = "my_default"
    
    # 1. Miss (should return default, hit=False)
    OrbitEntry.objects.all().delete()
    val = cache.get(key, default=default_val)
    assert val == default_val
    
    entry = OrbitEntry.objects.first()
    assert entry.payload['operation'] == 'get'
    assert entry.payload['hit'] is False
    
    # 2. Set explicitly to default value
    cache.set(key, default_val)
    
    # 3. Hit (stored value is same as default)
    OrbitEntry.objects.all().delete()
    val = cache.get(key, default=default_val)
    assert val == default_val
    
    entry = OrbitEntry.objects.first()
    assert entry.payload['operation'] == 'get'
    assert entry.payload['hit'] is True  # This was the bug: previously reported False

@pytest.mark.django_db
def test_command_watcher(capsys):
    """Test management command recording."""
    # Run a simple command
    call_command("check")
    
    # Check if entry was created
    entry = OrbitEntry.objects.filter(type=OrbitEntry.TYPE_COMMAND).first()
    assert entry is not None
    assert entry.payload['command'] == 'check'
    assert entry.payload['exit_code'] == 0
    # 'check' command usually outputs "System check identified no issues."
    assert "System check identified no issues" in entry.payload['output']
