import os
import sys
import django
from unittest.mock import patch

# Add project root to path
sys.path.insert(0, os.getcwd())

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")
django.setup()

from django.db import transaction
from orbit.watchers import install_transaction_watcher
import orbit.watchers as watchers

# Mock the record function in the module
original_record = watchers.record_transaction
mock_calls = []

def mock_record(*args, **kwargs):
    print(f"Recorded: {kwargs}")
    mock_calls.append(kwargs)

watchers.record_transaction = mock_record

print("Installing watcher...")
install_transaction_watcher()

print("\n--- Test 1: Commit ---")
with transaction.atomic():
    pass

print("\n--- Test 2: Rollback ---")
try:
    with transaction.atomic():
        print("Raising error...")
        raise ValueError("Boom")
except ValueError:
    print("Caught error")

print(f"\nTotal calls: {len(mock_calls)}")
for i, call in enumerate(mock_calls):
    print(f"Call {i+1}: {call['status']}")
