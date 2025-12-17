
import pytest
from datetime import timedelta
from django.utils import timezone
from django.core.management import call_command
from orbit.models import OrbitEntry

@pytest.mark.django_db
def test_prune_command():
    # Create entries
    now = timezone.now()
    
    # Old entry (should be deleted)
    old = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        payload={"foo": "bar"},
        created_at=now - timedelta(hours=25)
    )
    # Hack to force created_at (auto_now_add usually overrides, but we can update)
    OrbitEntry.objects.filter(id=old.id).update(created_at=now - timedelta(hours=25))
    
    # Recent entry (should be kept)
    recent = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_REQUEST,
        payload={"foo": "bar"}
    )
    
    # Run prune (default 24h)
    call_command("orbit_prune")
    
    assert not OrbitEntry.objects.filter(id=old.id).exists()
    assert OrbitEntry.objects.filter(id=recent.id).exists()

@pytest.mark.django_db
def test_prune_keep_important():
    now = timezone.now()
    
    # Old exception (should be kept with flag)
    old_exc = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_EXCEPTION,
        payload={"message": "Error"},
        created_at=now - timedelta(hours=48)
    )
    OrbitEntry.objects.filter(id=old_exc.id).update(created_at=now - timedelta(hours=48))
    
    # Old normal Log (should be deleted)
    old_log = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_LOG,
        payload={"level": "INFO", "message": "Info"},
        created_at=now - timedelta(hours=48)
    )
    OrbitEntry.objects.filter(id=old_log.id).update(created_at=now - timedelta(hours=48))
    
    # Old ERROR Log (should be kept with flag)
    old_error = OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_LOG,
        payload={"level": "ERROR", "message": "Bad"},
        created_at=now - timedelta(hours=48)
    )
    OrbitEntry.objects.filter(id=old_error.id).update(created_at=now - timedelta(hours=48))
    
    # Run prune with flag
    call_command("orbit_prune", hours=24, keep_important=True)
    
    assert OrbitEntry.objects.filter(id=old_exc.id).exists()
    assert not OrbitEntry.objects.filter(id=old_log.id).exists()
    assert OrbitEntry.objects.filter(id=old_error.id).exists()
