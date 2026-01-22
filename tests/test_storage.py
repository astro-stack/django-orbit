"""
Tests for Storage Watcher (v0.6.0)

Tests the storage watcher that tracks:
- File save operations
- File open operations
- File deletion
- File existence checks
"""
import pytest
import os
import shutil
import tempfile
from django.test import TestCase, override_settings
from django.core.files.storage import FileSystemStorage
from django.core.files.base import ContentFile
from orbit.models import OrbitEntry
import orbit.watchers as watchers

class TestStorageWatcher(TestCase):
    """Test storage operation recording."""
    
    def setUp(self):
        OrbitEntry.objects.all().delete()
        self.tmp_dir = os.path.abspath("orbit_test_storage")
        if not os.path.exists(self.tmp_dir):
            os.makedirs(self.tmp_dir)
        self.storage = FileSystemStorage(location=self.tmp_dir)
        
    def tearDown(self):
        try:
            if os.path.exists(self.tmp_dir):
                shutil.rmtree(self.tmp_dir)
        except Exception:
            pass
        
    @override_settings(ORBIT_CONFIG={"ENABLED": True, "RECORD_STORAGE": True})
    def test_record_save_operation(self):
        """Test recording a file save."""
        from orbit.watchers import install_storage_watcher, _storage_patched
        
        if not _storage_patched:
            install_storage_watcher()
            
        file_name = self.storage.save("test_file.txt", ContentFile(b"hello world"))
        
        entry = OrbitEntry.objects.filter(type="storage", payload__operation="save").last()
        assert entry is not None
        assert entry.payload["path"] == file_name
        assert entry.payload["size"] == 11
        assert "FileSystemStorage" in entry.payload["backend"]
        assert entry.duration_ms >= 0

    @override_settings(ORBIT_CONFIG={"ENABLED": True, "RECORD_STORAGE": True})
    def test_record_open_operation(self):
        """Test recording a file open."""
        from orbit.watchers import install_storage_watcher
        install_storage_watcher()
        
        file_name = self.storage.save("to_open.txt", ContentFile(b"content"))
        
        with self.storage.open(file_name) as f:
            content = f.read()
            
        entry = OrbitEntry.objects.filter(type="storage", payload__operation="open").last()
        assert entry is not None
        assert entry.payload["path"] == file_name
        assert "FileSystemStorage" in entry.payload["backend"]

    @override_settings(ORBIT_CONFIG={"ENABLED": True, "RECORD_STORAGE": True})
    def test_record_delete_operation(self):
        """Test recording a file deletion."""
        from orbit.watchers import install_storage_watcher
        install_storage_watcher()
        
        file_name = self.storage.save("to_delete.txt", ContentFile(b"bye"))
        self.storage.delete(file_name)
        
        entry = OrbitEntry.objects.filter(type="storage", payload__operation="delete").last()
        assert entry is not None
        assert entry.payload["path"] == file_name

    @override_settings(ORBIT_CONFIG={"ENABLED": True, "RECORD_STORAGE": True})
    def test_record_exists_operation(self):
        """Test recording an exists check."""
        from orbit.watchers import install_storage_watcher
        install_storage_watcher()
        
        file_name = self.storage.save("exists.txt", ContentFile(b"exist"))
        exists = self.storage.exists(file_name)
        assert exists is True
        
        entry = OrbitEntry.objects.filter(type="storage", payload__operation="exists").last()
        assert entry is not None
        assert entry.payload["path"] == file_name
        assert entry.payload["exists"] is True
