"""
Tests for Cache Backend Multi-Type Support (v0.6.0)

Tests the enhanced cache watcher that supports:
- Multiple backend types (redis, memcached, file, locmem, valkey)
- Batch operations (get_many, set_many, delete_many)
- Additional operations (incr, decr, clear)
- Duration tracking
"""
import pytest
from unittest.mock import MagicMock, patch
from django.test import TestCase, override_settings


class TestCacheBackendDetection(TestCase):
    """Test _detect_cache_backend_type function."""
    
    def test_detect_locmem_backend(self):
        """Test detection of LocMemCache backend."""
        from orbit.watchers import _detect_cache_backend_type
        from django.core.cache.backends.locmem import LocMemCache
        
        cache = LocMemCache("test", {})
        backend_type = _detect_cache_backend_type(cache)
        assert backend_type == "locmem"
    
    def test_detect_filebased_backend(self):
        """Test detection of FileBasedCache backend."""
        from orbit.watchers import _detect_cache_backend_type
        from django.core.cache.backends.filebased import FileBasedCache
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = FileBasedCache(tmpdir, {})
            backend_type = _detect_cache_backend_type(cache)
            assert backend_type == "file"
    
    def test_detect_dummy_backend(self):
        """Test detection of DummyCache backend."""
        from orbit.watchers import _detect_cache_backend_type
        from django.core.cache.backends.dummy import DummyCache
        
        cache = DummyCache("test", {})
        backend_type = _detect_cache_backend_type(cache)
        assert backend_type == "dummy"
    
    def test_detect_database_backend(self):
        """Test detection of DatabaseCache backend."""
        from orbit.watchers import _detect_cache_backend_type
        
        # Mock a database cache
        mock_cache = MagicMock()
        mock_cache.__class__.__name__ = "DatabaseCache"
        mock_cache.__class__.__module__ = "django.core.cache.backends.db"
        
        backend_type = _detect_cache_backend_type(mock_cache)
        assert backend_type == "database"
    
    def test_detect_redis_backend(self):
        """Test detection of Redis cache backend."""
        from orbit.watchers import _detect_cache_backend_type
        
        mock_cache = MagicMock()
        mock_cache.__class__.__name__ = "RedisCache"
        mock_cache.__class__.__module__ = "django_redis.cache"
        
        backend_type = _detect_cache_backend_type(mock_cache)
        assert backend_type == "redis"
    
    def test_detect_memcached_backend(self):
        """Test detection of Memcached cache backend."""
        from orbit.watchers import _detect_cache_backend_type
        
        mock_cache = MagicMock()
        mock_cache.__class__.__name__ = "MemcachedCache"
        mock_cache.__class__.__module__ = "django.core.cache.backends.memcached"
        mock_cache._cache = None
        
        backend_type = _detect_cache_backend_type(mock_cache)
        assert backend_type == "memcached"
    
    def test_detect_valkey_backend(self):
        """Test detection of Valkey cache backend (Redis fork)."""
        from orbit.watchers import _detect_cache_backend_type
        
        mock_cache = MagicMock()
        mock_cache.__class__.__name__ = "ValkeyCache"
        mock_cache.__class__.__module__ = "django_valkey.cache"
        
        backend_type = _detect_cache_backend_type(mock_cache)
        assert backend_type == "valkey"
    
    def test_detect_unknown_backend(self):
        """Test detection of unknown cache backend."""
        from orbit.watchers import _detect_cache_backend_type
        
        mock_cache = MagicMock()
        mock_cache.__class__.__name__ = "CustomCache"
        mock_cache.__class__.__module__ = "myapp.cache"
        
        backend_type = _detect_cache_backend_type(mock_cache)
        assert backend_type == "unknown"


class TestCacheOperationRecording(TestCase):
    """Test that cache operations are recorded correctly."""
    
    def setUp(self):
        from orbit.models import OrbitEntry
        OrbitEntry.objects.all().delete()
    
    @override_settings(ORBIT_CONFIG={"ENABLED": True, "RECORD_CACHE": True})
    def test_record_get_operation(self):
        """Test recording a cache get operation."""
        from orbit.watchers import record_cache_operation
        from orbit.models import OrbitEntry
        
        record_cache_operation(
            operation="get",
            key="test_key",
            hit=True,
            backend="default",
            backend_type="locmem",
            duration_ms=1.5,
        )
        
        entry = OrbitEntry.objects.filter(type="cache").first()
        assert entry is not None
        assert entry.payload["operation"] == "get"
        assert entry.payload["key"] == "test_key"
        assert entry.payload["hit"] is True
        assert entry.payload["backend"] == "default"
        assert entry.payload["backend_type"] == "locmem"
        assert entry.duration_ms == 1.5
    
    @override_settings(ORBIT_CONFIG={"ENABLED": True, "RECORD_CACHE": True})
    def test_record_set_operation(self):
        """Test recording a cache set operation."""
        from orbit.watchers import record_cache_operation
        from orbit.models import OrbitEntry
        
        record_cache_operation(
            operation="set",
            key="test_key",
            backend="default",
            backend_type="redis",
            ttl=300,
            duration_ms=2.0,
        )
        
        entry = OrbitEntry.objects.filter(type="cache").first()
        assert entry is not None
        assert entry.payload["operation"] == "set"
        assert entry.payload["ttl"] == 300
        assert entry.payload["backend_type"] == "redis"
    
    @override_settings(ORBIT_CONFIG={"ENABLED": True, "RECORD_CACHE": True})
    def test_record_get_many_operation(self):
        """Test recording a cache get_many operation."""
        from orbit.watchers import record_cache_operation
        from orbit.models import OrbitEntry
        
        record_cache_operation(
            operation="get_many",
            key="3/5 keys",
            hit=True,
            backend="default",
            backend_type="memcached",
            keys_count=5,
            duration_ms=5.0,
        )
        
        entry = OrbitEntry.objects.filter(type="cache").first()
        assert entry is not None
        assert entry.payload["operation"] == "get_many"
        assert entry.payload["keys_count"] == 5
        assert entry.payload["backend_type"] == "memcached"
    
    @override_settings(ORBIT_CONFIG={"ENABLED": True, "RECORD_CACHE": True})
    def test_record_clear_operation(self):
        """Test recording a cache clear operation."""
        from orbit.watchers import record_cache_operation
        from orbit.models import OrbitEntry
        
        record_cache_operation(
            operation="clear",
            key="*",
            backend="default",
            backend_type="file",
            duration_ms=10.0,
        )
        
        entry = OrbitEntry.objects.filter(type="cache").first()
        assert entry is not None
        assert entry.payload["operation"] == "clear"
        assert entry.payload["key"] == "*"


class TestCacheWatcherIntegration(TestCase):
    """Integration tests for the cache watcher."""
    
    def setUp(self):
        from orbit.models import OrbitEntry
        OrbitEntry.objects.all().delete()
    
    @override_settings(
        ORBIT_CONFIG={"ENABLED": True, "RECORD_CACHE": True},
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "test-cache",
            }
        }
    )
    def test_patched_cache_get_records_entry(self):
        """Test that patched cache.get() records an entry."""
        from django.core.cache import cache
        from orbit.watchers import install_cache_watcher, _cache_patched
        from orbit.models import OrbitEntry
        import orbit.watchers as watchers
        
        # Reset patch state for test
        watchers._cache_patched = False
        install_cache_watcher()
        
        # Perform cache operations
        cache.set("integration_key", "test_value", timeout=60)
        result = cache.get("integration_key")
        
        assert result == "test_value"
        
        # Check recorded entries
        entries = OrbitEntry.objects.filter(type="cache").order_by("created_at")
        assert entries.count() >= 2
        
        # Verify set operation
        set_entry = entries.filter(payload__operation="set").first()
        assert set_entry is not None
        assert set_entry.payload["key"] == "integration_key"
        assert set_entry.payload["backend_type"] == "locmem"
        
        # Verify get operation
        get_entry = entries.filter(payload__operation="get").first()
        assert get_entry is not None
        assert get_entry.payload["hit"] is True
    
    @override_settings(
        ORBIT_CONFIG={"ENABLED": True, "RECORD_CACHE": True},
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "test-cache-2",
            }
        }
    )
    def test_cache_miss_recorded(self):
        """Test that cache misses are recorded correctly."""
        from django.core.cache import cache
        from orbit.watchers import install_cache_watcher
        from orbit.models import OrbitEntry
        import orbit.watchers as watchers
        
        # Reset and install
        watchers._cache_patched = False
        install_cache_watcher()
        
        # Get a key that doesn't exist
        result = cache.get("nonexistent_key", default="fallback")
        
        assert result == "fallback"
        
        entry = OrbitEntry.objects.filter(
            type="cache", 
            payload__operation="get"
        ).last()
        assert entry is not None
        assert entry.payload["hit"] is False
