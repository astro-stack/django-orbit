
import threading
import time
from django.db import transaction
from django.test import TestCase, TransactionTestCase
from orbit.watchers import install_transaction_watcher, record_transaction
from unittest.mock import patch

class AtomicFixTests(TransactionTestCase):
    def setUp(self):
        install_transaction_watcher()

    def test_decorator_usage(self):
        """Test usage as a decorator (@transaction.atomic)."""
        @transaction.atomic
        def decorated_func():
            return "ok"
        
        with patch('orbit.watchers.record_transaction') as mock_record:
            result = decorated_func()
            self.assertEqual(result, "ok")
            mock_record.assert_called_once()
            args, kwargs = mock_record.call_args
            self.assertEqual(kwargs['status'], 'committed')

    def test_nested_decorator(self):
        """Test nested usage of decorators."""
        @transaction.atomic
        def outer():
            return inner()

        @transaction.atomic
        def inner():
            return "inner"

        with patch('orbit.watchers.record_transaction') as mock_record:
            result = outer()
            self.assertEqual(result, "inner")
            # Should be called twice (once for inner, once for outer)
            self.assertEqual(mock_record.call_count, 2)

    def test_recursion(self):
        """Test recursive usage."""
        @transaction.atomic
        def recursive(n):
            if n <= 0:
                return 0
            return 1 + recursive(n - 1)

        with patch('orbit.watchers.record_transaction') as mock_record:
            result = recursive(3)
            self.assertEqual(result, 3)
            # Called 4 times (3, 2, 1, 0)
            self.assertEqual(mock_record.call_count, 4)

    def test_thread_safety(self):
        """Test that start_time stack is thread-local."""
        
        wrapper = transaction.atomic  # The patched atomic function

        results = []
        
        def thread_task(delay):
            @transaction.atomic
            def task():
                time.sleep(delay)
                return "done"
            results.append(task())

        with patch('orbit.watchers.record_transaction') as mock_record:
            t1 = threading.Thread(target=thread_task, args=(0.1,))
            t2 = threading.Thread(target=thread_task, args=(0.2,))
            
            t1.start()
            t2.start()
            
            t1.join()
            t2.join()
            
            self.assertEqual(len(results), 2)
            self.assertEqual(mock_record.call_count, 2)
            
            # Verify durations are roughly correct (distinct)
            # We can't easily verify exact durations on mock calls because call order is indeterminate
            # but if they weren't thread local, one might pop the other's start time and get negative or wrong duration.
            durations = [kwargs['duration_ms'] for args, kwargs in mock_record.call_args_list]
            self.assertTrue(all(d > 0 for d in durations))

    def test_context_manager_usage(self):
        """Test usage as context manager."""
        with patch('orbit.watchers.record_transaction') as mock_record:
            with transaction.atomic():
                pass
            mock_record.assert_called_once()

    def test_atomic_requests_simulation(self):
        """Simulate ATOMIC_REQUESTS behavior (decorator calling)."""
        # This simulates what Django does in TransactionMiddleware
        # atomic(using=db)(view_func)
        
        def view_func():
            return "view"
        
        # This is how Django wraps the view
        wrapped_view = transaction.atomic(using='default')(view_func)
        
        with patch('orbit.watchers.record_transaction') as mock_record:
            result = wrapped_view()
            self.assertEqual(result, "view")
            mock_record.assert_called_once()
