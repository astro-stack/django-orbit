"""
Django Orbit Utilities

Helper functions for JSON serialization, request context extraction,
and payload sanitization.
"""

import datetime
import decimal
import hashlib
import json
import traceback
import uuid
from typing import Any, Dict, List, Optional

from django.http import HttpRequest


class OrbitJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that handles Django-specific types.
    
    Converts datetime, date, time, UUID, Decimal, bytes, and sets
    to JSON-serializable formats.
    """
    
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        elif isinstance(obj, datetime.date):
            return obj.isoformat()
        elif isinstance(obj, datetime.time):
            return obj.isoformat()
        elif isinstance(obj, datetime.timedelta):
            return str(obj)
        elif isinstance(obj, uuid.UUID):
            return str(obj)
        elif isinstance(obj, decimal.Decimal):
            return float(obj)
        elif isinstance(obj, bytes):
            try:
                return obj.decode("utf-8")
            except UnicodeDecodeError:
                return f"<bytes: {len(obj)} bytes>"
        elif isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, frozenset):
            return list(obj)
        elif hasattr(obj, "__dict__"):
            return str(obj)
        return super().default(obj)


def serialize_for_json(data: Any) -> Any:
    """
    Recursively serialize data for JSON storage.
    
    Args:
        data: Any Python object to serialize
        
    Returns:
        JSON-serializable version of the data
    """
    if data is None:
        return None
    
    if isinstance(data, (str, int, float, bool)):
        return data
    
    if isinstance(data, (datetime.datetime, datetime.date, datetime.time)):
        return data.isoformat()
    
    if isinstance(data, datetime.timedelta):
        return str(data)
    
    if isinstance(data, uuid.UUID):
        return str(data)
    
    if isinstance(data, decimal.Decimal):
        return float(data)
    
    if isinstance(data, bytes):
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return f"<bytes: {len(data)} bytes>"
    
    if isinstance(data, dict):
        return {str(k): serialize_for_json(v) for k, v in data.items()}
    
    if isinstance(data, (list, tuple, set, frozenset)):
        return [serialize_for_json(item) for item in data]
    
    # Fallback: convert to string
    try:
        return str(data)
    except Exception:
        return f"<unserializable: {type(data).__name__}>"


def generate_family_hash() -> str:
    """
    Generate a unique hash for grouping related events.
    
    Returns:
        A 16-character hex string
    """
    unique_id = uuid.uuid4().hex
    return hashlib.sha256(unique_id.encode()).hexdigest()[:16]


def sanitize_headers(
    headers: Dict[str, str], 
    hide_keys: Optional[List[str]] = None
) -> Dict[str, str]:
    """
    Sanitize request headers by hiding sensitive values.
    
    Args:
        headers: Dictionary of header names and values
        hide_keys: List of header names to hide (case-insensitive)
        
    Returns:
        Sanitized headers dictionary
    """
    if hide_keys is None:
        hide_keys = ["Authorization", "Cookie", "X-CSRFToken"]
    
    hide_keys_lower = [k.lower() for k in hide_keys]
    sanitized = {}
    
    for key, value in headers.items():
        if key.lower() in hide_keys_lower:
            sanitized[key] = "***HIDDEN***"
        else:
            sanitized[key] = value
    
    return sanitized


def sanitize_body(
    body: Dict[str, Any],
    hide_keys: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Sanitize request body by hiding sensitive values.
    
    Args:
        body: Dictionary of body data
        hide_keys: List of keys to hide (case-insensitive)
        
    Returns:
        Sanitized body dictionary
    """
    if hide_keys is None:
        hide_keys = ["password", "token", "secret", "api_key", "apikey"]
    
    hide_keys_lower = [k.lower() for k in hide_keys]
    
    def _sanitize(data):
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                if key.lower() in hide_keys_lower:
                    result[key] = "***HIDDEN***"
                else:
                    result[key] = _sanitize(value)
            return result
        elif isinstance(data, list):
            return [_sanitize(item) for item in data]
        return data
    
    return _sanitize(body)


def extract_request_headers(request: HttpRequest) -> Dict[str, str]:
    """
    Extract headers from a Django request object.
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        Dictionary of header names and values
    """
    headers = {}
    
    # Standard headers
    for key, value in request.META.items():
        if key.startswith("HTTP_"):
            # Convert HTTP_ACCEPT_LANGUAGE to Accept-Language
            header_name = key[5:].replace("_", "-").title()
            headers[header_name] = value
        elif key in ("CONTENT_TYPE", "CONTENT_LENGTH"):
            header_name = key.replace("_", "-").title()
            headers[header_name] = value
    
    return headers


def extract_client_ip(request: HttpRequest) -> str:
    """
    Extract the client IP address from a request.
    
    Handles X-Forwarded-For headers for proxied requests.
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        Client IP address string
    """
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        # Take the first IP in the chain
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR", "unknown")
    return ip


def extract_request_body(request: HttpRequest, max_size: int = 65536) -> Optional[Any]:
    """
    Extract and parse the request body.
    
    Args:
        request: Django HttpRequest object
        max_size: Maximum body size to capture (bytes)
        
    Returns:
        Parsed body data or None
    """
    try:
        body = request.body
        
        if not body:
            return None
        
        if len(body) > max_size:
            return f"<body too large: {len(body)} bytes>"
        
        content_type = request.content_type or ""
        
        if "application/json" in content_type:
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                return body.decode("utf-8", errors="replace")
        
        elif "application/x-www-form-urlencoded" in content_type:
            return dict(request.POST)
        
        elif "multipart/form-data" in content_type:
            # Don't include file contents, just metadata
            data = dict(request.POST)
            files = {}
            for key, file_list in request.FILES.lists():
                files[key] = [
                    {
                        "name": f.name,
                        "size": f.size,
                        "content_type": f.content_type,
                    }
                    for f in file_list
                ]
            if files:
                data["_files"] = files
            return data
        
        else:
            # Try to decode as text
            try:
                return body.decode("utf-8")
            except UnicodeDecodeError:
                return f"<binary data: {len(body)} bytes>"
    
    except Exception:
        return None


def format_traceback(exc: Exception) -> List[Dict[str, Any]]:
    """
    Format an exception traceback as a list of frame dictionaries.
    
    Args:
        exc: The exception to format
        
    Returns:
        List of dictionaries with frame information
    """
    frames = []
    tb = traceback.extract_tb(exc.__traceback__)
    
    for frame in tb:
        frames.append({
            "filename": frame.filename,
            "lineno": frame.lineno,
            "name": frame.name,
            "line": frame.line,
        })
    
    return frames


def get_exception_info(exc: Exception) -> Dict[str, Any]:
    """
    Extract detailed information from an exception.
    
    Args:
        exc: The exception to extract info from
        
    Returns:
        Dictionary with exception details
    """
    return {
        "exception_type": type(exc).__name__,
        "exception_module": type(exc).__module__,
        "message": str(exc),
        "traceback": format_traceback(exc),
        "traceback_string": "".join(traceback.format_exception(
            type(exc), exc, exc.__traceback__
        )),
    }


def truncate_string(s: str, max_length: int = 1000) -> str:
    """
    Truncate a string to a maximum length.
    
    Args:
        s: String to truncate
        max_length: Maximum length
        
    Returns:
        Truncated string with ellipsis if needed
    """
    if len(s) <= max_length:
        return s
    return s[:max_length - 3] + "..."
