import os
import sys
import django
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from unittest.mock import MagicMock

# Add project root to path
sys.path.insert(0, os.getcwd())

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")
django.setup()

from orbit.watchers import install_storage_watcher
import orbit.watchers as watchers

# Mock record function
watchers.record_storage_operation = MagicMock()

import tempfile

print("Installing storage watcher...")
install_storage_watcher()

tmp_dir = os.path.join(tempfile.gettempdir(), "orbit_repro_storage")
if not os.path.exists(tmp_dir):
    os.makedirs(tmp_dir)

print(f"Using storage at {tmp_dir}")
storage = FileSystemStorage(location=tmp_dir)

print("\n--- Test 1: Save ---")
try:
    name = storage.save("test.txt", ContentFile(b"hello"))
    print(f"Saved: {name}")
except Exception as e:
    print(f"Save FAILED: {e}")
    import traceback
    traceback.print_exc()

print("\n--- Test 2: Open ---")
try:
    with storage.open("test.txt") as f:
        print(f"Read: {f.read()}")
except Exception as e:
    print(f"Open FAILED: {e}")

print("\n--- Test 3: Exists ---")
try:
    exists = storage.exists("test.txt")
    print(f"Exists: {exists}")
except Exception as e:
    print(f"Exists FAILED: {e}")

print("\n--- Test 4: Delete ---")
try:
    storage.delete("test.txt")
    print("Deleted")
except Exception as e:
    print(f"Delete FAILED: {e}")

# Clean up
import shutil
shutil.rmtree(tmp_dir)

print("\nWatcher calls:")
for call in watchers.record_storage_operation.call_args_list:
    print(call)
