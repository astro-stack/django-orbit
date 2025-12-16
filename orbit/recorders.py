"""
Django Orbit SQL Recorder

Intercepts SQL queries using Django's database wrapper mechanism.
"""

import hashlib
import threading
import time
import traceback
from contextlib import contextmanager
from typing import Any, Callable, Dict, List, Optional

from django.db import connection

from orbit.conf import get_config


# Thread-local storage for tracking queries per request
_local = threading.local()


def get_current_queries() -> List[Dict[str, Any]]:
    """Get the list of queries for the current request."""
    if not hasattr(_local, "queries"):
        _local.queries = []
    return _local.queries


def get_current_family_hash() -> Optional[str]:
    """Get the family hash for the current request."""
    return getattr(_local, "family_hash", None)


def set_current_family_hash(family_hash: str) -> None:
    """Set the family hash for the current request."""
    _local.family_hash = family_hash


def clear_current_context() -> None:
    """Clear the current request context."""
    _local.queries = []
    _local.family_hash = None


def _get_query_hash(sql: str) -> str:
    """Generate a hash for a SQL query (for duplicate detection)."""
    return hashlib.md5(sql.encode()).hexdigest()[:12]


def _extract_caller_info() -> Dict[str, Any]:
    """
    Extract information about the code that triggered the query.
    
    Returns:
        Dictionary with filename, line number, and function name
    """
    # Walk up the stack to find the first non-Django, non-Orbit frame
    stack = traceback.extract_stack()
    
    for frame in reversed(stack):
        filename = frame.filename
        
        # Skip Django internals and Orbit itself
        if any(skip in filename for skip in [
            "django/db",
            "django/core",
            "orbit/recorders.py",
            "orbit/middleware.py",
        ]):
            continue
        
        return {
            "filename": filename,
            "lineno": frame.lineno,
            "function": frame.name,
            "line": frame.line,
        }
    
    return {}


class OrbitQueryWrapper:
    """
    Database query wrapper that intercepts and records SQL queries.
    
    Works with Django's connection.execute_wrapper() mechanism.
    """
    
    def __init__(self, family_hash: Optional[str] = None):
        self.family_hash = family_hash
        self.queries = []
        self.query_hashes = {}  # For duplicate detection
    
    def __call__(self, execute, sql, params, many, context):
        """
        Wrap database query execution.
        
        Args:
            execute: The original execute function
            sql: The SQL query string
            params: Query parameters
            many: Boolean indicating executemany
            context: Execution context
            
        Returns:
            The result of the original execute function
        """
        config = get_config()
        slow_threshold = config.get("SLOW_QUERY_THRESHOLD_MS", 500)
        
        # Record start time
        start_time = time.perf_counter()
        
        try:
            result = execute(sql, params, many, context)
            return result
        finally:
            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            # Check for duplicates
            query_hash = _get_query_hash(sql)
            is_duplicate = query_hash in self.query_hashes
            self.query_hashes[query_hash] = self.query_hashes.get(query_hash, 0) + 1
            duplicate_count = self.query_hashes[query_hash]
            
            # Check if slow
            is_slow = duration_ms > slow_threshold
            
            # Get caller info
            caller = _extract_caller_info()
            
            # Build query info
            query_info = {
                "sql": sql,
                "params": self._serialize_params(params),
                "duration_ms": round(duration_ms, 3),
                "is_slow": is_slow,
                "is_duplicate": is_duplicate,
                "duplicate_count": duplicate_count,
                "database": context.get("alias", "default") if context else "default",
                "caller": caller,
            }
            
            self.queries.append(query_info)
            
            # Also add to thread-local for access from middleware
            get_current_queries().append(query_info)
    
    def _serialize_params(self, params) -> Any:
        """Serialize query parameters for JSON storage."""
        from orbit.utils import serialize_for_json
        
        if params is None:
            return None
        
        try:
            return serialize_for_json(params)
        except Exception:
            return str(params)


@contextmanager
def record_queries(family_hash: Optional[str] = None):
    """
    Context manager to record SQL queries within a block.
    
    Args:
        family_hash: Optional hash to group queries with a request
        
    Yields:
        OrbitQueryWrapper instance with captured queries
    """
    wrapper = OrbitQueryWrapper(family_hash=family_hash)
    
    with connection.execute_wrapper(wrapper):
        yield wrapper


def save_queries_to_orbit(
    queries: List[Dict[str, Any]],
    family_hash: Optional[str] = None
) -> None:
    """
    Save captured queries to OrbitEntry records.
    
    Args:
        queries: List of query info dictionaries
        family_hash: Optional hash to group with parent request
    """
    from orbit.models import OrbitEntry
    
    entries = []
    for query in queries:
        entry = OrbitEntry(
            type=OrbitEntry.TYPE_QUERY,
            family_hash=family_hash,
            payload=query,
            duration_ms=query.get("duration_ms"),
        )
        entries.append(entry)
    
    if entries:
        OrbitEntry.objects.bulk_create(entries)
