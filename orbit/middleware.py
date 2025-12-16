"""
Django Orbit Middleware

Main middleware that captures HTTP requests, responses, exceptions,
and coordinates SQL query recording.
"""

import time
import traceback
from typing import Callable, Optional

from django.db import connection
from django.http import HttpRequest, HttpResponse

from orbit.conf import get_config, is_enabled, should_ignore_path
from orbit.handlers import OrbitLogContext, set_current_family_hash
from orbit.recorders import OrbitQueryWrapper, clear_current_context, get_current_queries
from orbit.utils import (
    extract_client_ip,
    extract_request_body,
    extract_request_headers,
    generate_family_hash,
    get_exception_info,
    sanitize_body,
    sanitize_headers,
    serialize_for_json,
)


class OrbitMiddleware:
    """
    Main Orbit middleware that orchestrates request/response capture.
    
    This middleware:
    - Captures incoming request details
    - Wraps database queries for recording
    - Captures response details and timing
    - Handles uncaught exceptions
    - Links all events via family_hash
    """
    
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        """
        Process the request through Orbit's capture pipeline.
        """
        config = get_config()
        
        # Check if Orbit is enabled
        if not config.get("ENABLED", True):
            return self.get_response(request)
        
        # Check if we should ignore this path
        if should_ignore_path(request.path):
            return self.get_response(request)
        
        # Generate family hash for this request
        family_hash = generate_family_hash()
        
        # Clear any previous context
        clear_current_context()
        
        # Set up logging context
        set_current_family_hash(family_hash)
        
        # Record start time
        start_time = time.perf_counter()
        
        # Extract request data before processing
        request_data = self._extract_request_data(request, config)
        
        # Create query wrapper
        query_wrapper = OrbitQueryWrapper(family_hash=family_hash)
        
        # Process request with query recording
        response = None
        exception_info = None
        
        try:
            with connection.execute_wrapper(query_wrapper):
                response = self.get_response(request)
        except Exception as e:
            # Capture exception info
            exception_info = get_exception_info(e)
            
            # Save exception entry
            if config.get("RECORD_EXCEPTIONS", True):
                self._save_exception(e, family_hash, request_data)
            
            # Re-raise the exception
            raise
        finally:
            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            # Save SQL queries
            if config.get("RECORD_QUERIES", True) and query_wrapper.queries:
                self._save_queries(query_wrapper.queries, family_hash)
            
            # Save request entry
            if config.get("RECORD_REQUESTS", True):
                self._save_request(
                    request_data=request_data,
                    response=response,
                    family_hash=family_hash,
                    duration_ms=duration_ms,
                    query_count=len(query_wrapper.queries),
                    exception_info=exception_info,
                )
            
            # Clean up old entries if needed
            self._cleanup_if_needed(config)
            
            # Clear context
            set_current_family_hash(None)
            clear_current_context()
        
        return response
    
    def _extract_request_data(self, request: HttpRequest, config: dict) -> dict:
        """
        Extract data from the incoming request.
        """
        hide_headers = config.get("HIDE_REQUEST_HEADERS", [])
        hide_body_keys = config.get("HIDE_REQUEST_BODY_KEYS", [])
        max_body_size = config.get("MAX_BODY_SIZE", 65536)
        
        # Extract headers
        headers = extract_request_headers(request)
        headers = sanitize_headers(headers, hide_headers)
        
        # Extract body
        body = extract_request_body(request, max_body_size)
        if isinstance(body, dict):
            body = sanitize_body(body, hide_body_keys)
        
        # Build request data
        return {
            "method": request.method,
            "path": request.path,
            "full_path": request.get_full_path(),
            "scheme": request.scheme,
            "host": request.get_host(),
            "client_ip": extract_client_ip(request),
            "headers": headers,
            "body": serialize_for_json(body),
            "query_params": dict(request.GET),
            "session_key": getattr(request.session, "session_key", None) if hasattr(request, "session") else None,
            "user_id": request.user.id if hasattr(request, "user") and request.user.is_authenticated else None,
            "user_str": str(request.user) if hasattr(request, "user") else None,
            "is_ajax": request.headers.get("X-Requested-With") == "XMLHttpRequest",
            "content_type": request.content_type,
        }
    
    def _save_request(
        self,
        request_data: dict,
        response: Optional[HttpResponse],
        family_hash: str,
        duration_ms: float,
        query_count: int,
        exception_info: Optional[dict] = None,
    ) -> None:
        """
        Save the request/response entry to the database.
        """
        from orbit.models import OrbitEntry
        
        # Build payload
        payload = {
            **request_data,
            "duration_ms": round(duration_ms, 3),
            "query_count": query_count,
        }
        
        # Add response data if available
        if response:
            payload["status_code"] = response.status_code
            payload["reason_phrase"] = response.reason_phrase
            payload["response_headers"] = dict(response.headers) if hasattr(response, "headers") else {}
            
            # Detect response type
            content_type = response.get("Content-Type", "")
            payload["content_type"] = content_type
            
            # Don't capture response body (can be large and sensitive)
            payload["content_length"] = len(response.content) if hasattr(response, "content") else 0
        else:
            payload["status_code"] = 500
            payload["reason_phrase"] = "Internal Server Error"
        
        # Add exception summary if present
        if exception_info:
            payload["had_exception"] = True
            payload["exception_type"] = exception_info.get("exception_type")
            payload["exception_message"] = exception_info.get("message")
        else:
            payload["had_exception"] = False
        
        # Create entry
        OrbitEntry.objects.create(
            type=OrbitEntry.TYPE_REQUEST,
            family_hash=family_hash,
            payload=payload,
            duration_ms=duration_ms,
        )
    
    def _save_queries(self, queries: list, family_hash: str) -> None:
        """
        Save captured SQL queries to the database.
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
    
    def _save_exception(
        self,
        exception: Exception,
        family_hash: str,
        request_data: dict,
    ) -> None:
        """
        Save an exception entry to the database.
        """
        from orbit.models import OrbitEntry
        
        exception_info = get_exception_info(exception)
        
        payload = {
            **exception_info,
            "request_method": request_data.get("method"),
            "request_path": request_data.get("path"),
            "request_host": request_data.get("host"),
        }
        
        OrbitEntry.objects.create(
            type=OrbitEntry.TYPE_EXCEPTION,
            family_hash=family_hash,
            payload=payload,
        )
    
    def _cleanup_if_needed(self, config: dict) -> None:
        """
        Clean up old entries if we've exceeded the storage limit.
        """
        from orbit.models import OrbitEntry
        
        limit = config.get("STORAGE_LIMIT", 1000)
        
        # Only check periodically (roughly every 10 requests)
        import random
        if random.random() < 0.1:
            OrbitEntry.objects.cleanup_old_entries(limit=limit)
