"""
Django Orbit Watchers

Additional recorders for Phase 1 features:
- Command Watcher (management commands)
- Cache Watcher (cache operations)
- Model Watcher (ORM events)
- HTTP Client Watcher (outgoing requests)
"""

import functools
import logging
import time
from typing import Any, Dict, Optional

from django.apps import apps
from django.conf import settings

from orbit.conf import get_config

logger = logging.getLogger(__name__)


# =============================================================================
# Command Watcher
# =============================================================================

_original_execute = None


def record_command(command_name: str, args: tuple, options: dict, 
                   exit_code: int, output: str = "", duration_ms: float = 0):
    """
    Record a management command execution to Orbit.
    
    Args:
        command_name: Name of the command (e.g., "migrate")
        args: Positional arguments
        options: Command options
        exit_code: Exit code (0 = success)
        output: Command output (truncated)
        duration_ms: Execution duration in milliseconds
    """
    config = get_config()
    if not config.get("ENABLED", True):
        return
    
    # Check if command recording is enabled
    if not config.get("RECORD_COMMANDS", True):
        return
    
    # Ignore certain commands
    ignore_commands = config.get("IGNORE_COMMANDS", [
        "runserver", "shell", "dbshell", "showmigrations"
    ])
    if command_name in ignore_commands:
        return
    
    from orbit.models import OrbitEntry
    
    # Filter sensitive options
    filtered_options = {k: v for k, v in options.items() 
                       if k not in ("settings", "pythonpath", "traceback", "verbosity")}
    
    # Truncate output
    max_output = config.get("MAX_COMMAND_OUTPUT", 5000)
    if len(output) > max_output:
        output = output[:max_output] + "\n... (truncated)"
    
    payload = {
        "command": command_name,
        "args": list(args),
        "options": filtered_options,
        "exit_code": exit_code,
        "output": output,
    }
    
    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_COMMAND,
        payload=payload,
        duration_ms=duration_ms,
    )


def install_command_watcher():
    """
    Install the command watcher by patching Django's BaseCommand.execute.
    """
    global _original_execute
    
    if _original_execute is not None:
        return  # Already installed
    
    try:
        from django.core.management.base import BaseCommand
        
        _original_execute = BaseCommand.execute
        
        @functools.wraps(_original_execute)
        def patched_execute(self, *args, **options):
            import io
            import sys
            
            command_name = self.__class__.__module__.split(".")[-1]
            
            # Capture output
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            captured_output = io.StringIO()
            
            try:
                # Redirect stdout/stderr to capture output
                sys.stdout = captured_output
                sys.stderr = captured_output
                
                start_time = time.perf_counter()
                try:
                    result = _original_execute(self, *args, **options)
                    exit_code = 0
                except SystemExit as e:
                    exit_code = e.code if e.code is not None else 0
                    raise
                except Exception:
                    exit_code = 1
                    raise
                finally:
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    output = captured_output.getvalue()
                    
                    # Restore stdout/stderr before recording
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                    
                    # Record to Orbit
                    try:
                        record_command(
                            command_name=command_name,
                            args=args,
                            options=options,
                            exit_code=exit_code,
                            output=output,
                            duration_ms=duration_ms
                        )
                    except Exception as e:
                        logger.debug(f"Failed to record command: {e}")
                
                return result
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr
        
        BaseCommand.execute = patched_execute
        logger.debug("Orbit command watcher installed")
        
    except Exception as e:
        logger.warning(f"Failed to install command watcher: {e}")


# =============================================================================
# Cache Watcher
# =============================================================================

_cache_patched = False


def record_cache_operation(operation: str, key: str, hit: Optional[bool] = None,
                           backend: str = "default", ttl: Optional[int] = None):
    """
    Record a cache operation to Orbit.
    
    Args:
        operation: get, set, delete, clear
        key: Cache key
        hit: True if cache hit, False if miss (for get operations)
        backend: Cache backend name
        ttl: Time-to-live in seconds (for set operations)
    """
    config = get_config()
    if not config.get("ENABLED", True):
        return
    
    if not config.get("RECORD_CACHE", True):
        return
    
    from orbit.models import OrbitEntry
    
    payload = {
        "operation": operation,
        "key": key,
        "backend": backend,
    }
    
    if hit is not None:
        payload["hit"] = hit
    
    if ttl is not None:
        payload["ttl"] = ttl
    
    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_CACHE,
        payload=payload,
    )


def install_cache_watcher():
    """
    Install the cache watcher by patching Django's cache backends.
    """
    global _cache_patched
    
    if _cache_patched:
        return
    
    try:
        from django.core.cache import caches
        
        for alias in caches:
            cache = caches[alias]
            _patch_cache_backend(cache, alias)
        
        _cache_patched = True
        logger.debug("Orbit cache watcher installed")
        
    except Exception as e:
        logger.warning(f"Failed to install cache watcher: {e}")


def _patch_cache_backend(cache, alias: str):
    """Patch a single cache backend."""
    original_get = cache.get
    original_set = cache.set
    original_delete = cache.delete
    
    @functools.wraps(original_get)
    def patched_get(key, default=None, version=None):
        result = original_get(key, default=default, version=version)
        hit = result is not default
        try:
            record_cache_operation("get", key, hit=hit, backend=alias)
        except Exception:
            pass
        return result
    
    @functools.wraps(original_set)
    def patched_set(key, value, timeout=None, version=None):
        result = original_set(key, value, timeout=timeout, version=version)
        try:
            record_cache_operation("set", key, backend=alias, ttl=timeout)
        except Exception:
            pass
        return result
    
    @functools.wraps(original_delete)
    def patched_delete(key, version=None):
        result = original_delete(key, version=version)
        try:
            record_cache_operation("delete", key, backend=alias)
        except Exception:
            pass
        return result
    
    cache.get = patched_get
    cache.set = patched_set
    cache.delete = patched_delete


# =============================================================================
# Model Watcher
# =============================================================================

_model_signals_connected = False


def record_model_event(sender, instance, action: str, changes: Optional[Dict] = None):
    """
    Record a model event to Orbit.
    
    Args:
        sender: Model class
        instance: Model instance
        action: created, updated, deleted
        changes: Dictionary of field changes (for updates)
    """
    config = get_config()
    if not config.get("ENABLED", True):
        return
    
    if not config.get("RECORD_MODELS", True):
        return
    
    # Ignore Orbit's own model
    if sender.__name__ == "OrbitEntry":
        return
    
    from orbit.models import OrbitEntry
    
    model_name = f"{sender._meta.app_label}.{sender._meta.model_name}"
    
    payload = {
        "model": model_name,
        "action": action,
        "pk": str(instance.pk) if instance.pk else None,
    }
    
    if changes:
        payload["changes"] = changes
    
    # Get string representation
    try:
        payload["representation"] = str(instance)[:100]
    except Exception:
        pass
    
    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_MODEL,
        payload=payload,
    )


def _on_pre_save(sender, instance, raw, using, update_fields, **kwargs):
    """Pre-save signal handler to capture field changes."""
    if raw:
        return
    
    # Store original values for comparison in post_save
    if instance.pk:
        try:
            original = sender.objects.get(pk=instance.pk)
            instance._orbit_original = {
                field.name: getattr(original, field.name)
                for field in sender._meta.fields
            }
        except sender.DoesNotExist:
            instance._orbit_original = None
    else:
        instance._orbit_original = None


def _on_post_save(sender, instance, created, raw, using, update_fields, **kwargs):
    """Post-save signal handler."""
    if raw:
        return
    
    if created:
        record_model_event(sender, instance, "created")
    else:
        # Calculate changes
        changes = {}
        original = getattr(instance, "_orbit_original", None)
        if original:
            for field in sender._meta.fields:
                old_val = original.get(field.name)
                new_val = getattr(instance, field.name)
                if old_val != new_val:
                    changes[field.name] = {
                        "old": str(old_val)[:100] if old_val else None,
                        "new": str(new_val)[:100] if new_val else None,
                    }
        
        if changes:
            record_model_event(sender, instance, "updated", changes=changes)


def _on_post_delete(sender, instance, using, **kwargs):
    """Post-delete signal handler."""
    record_model_event(sender, instance, "deleted")


def install_model_watcher():
    """
    Install the model watcher by connecting to Django signals.
    """
    global _model_signals_connected
    
    if _model_signals_connected:
        return
    
    try:
        from django.db.models.signals import pre_save, post_save, post_delete
        
        # Connect to all models
        pre_save.connect(_on_pre_save, dispatch_uid="orbit_pre_save")
        post_save.connect(_on_post_save, dispatch_uid="orbit_post_save")
        post_delete.connect(_on_post_delete, dispatch_uid="orbit_post_delete")
        
        _model_signals_connected = True
        logger.debug("Orbit model watcher installed")
        
    except Exception as e:
        logger.warning(f"Failed to install model watcher: {e}")


# =============================================================================
# HTTP Client Watcher
# =============================================================================

_requests_patched = False


def record_http_client_request(method: str, url: str, status_code: Optional[int],
                                duration_ms: float, request_headers: Optional[Dict] = None,
                                response_size: Optional[int] = None, error: Optional[str] = None):
    """
    Record an outgoing HTTP request to Orbit.
    
    Args:
        method: HTTP method
        url: Request URL
        status_code: Response status code
        duration_ms: Request duration in milliseconds
        request_headers: Request headers (filtered)
        response_size: Response body size in bytes
        error: Error message if request failed
    """
    config = get_config()
    if not config.get("ENABLED", True):
        return
    
    if not config.get("RECORD_HTTP_CLIENT", True):
        return
    
    from orbit.models import OrbitEntry
    from orbit.utils import filter_sensitive_data
    
    # Filter sensitive headers
    if request_headers:
        request_headers = filter_sensitive_data(request_headers)
    
    payload = {
        "method": method.upper(),
        "url": url,
        "status_code": status_code,
    }
    
    if request_headers:
        payload["request_headers"] = request_headers
    
    if response_size is not None:
        payload["response_size"] = response_size
    
    if error:
        payload["error"] = error
    
    OrbitEntry.objects.create(
        type=OrbitEntry.TYPE_HTTP_CLIENT,
        payload=payload,
        duration_ms=duration_ms,
    )


def install_http_client_watcher():
    """
    Install the HTTP client watcher by patching the requests library.
    """
    global _requests_patched
    
    if _requests_patched:
        return
    
    try:
        import requests
        
        original_request = requests.Session.request
        
        @functools.wraps(original_request)
        def patched_request(self, method, url, **kwargs):
            start_time = time.perf_counter()
            error = None
            status_code = None
            response_size = None
            
            try:
                response = original_request(self, method, url, **kwargs)
                status_code = response.status_code
                response_size = len(response.content) if response.content else 0
                return response
            except Exception as e:
                error = str(e)
                raise
            finally:
                duration_ms = (time.perf_counter() - start_time) * 1000
                
                # Get request headers
                headers = kwargs.get("headers", {})
                
                try:
                    record_http_client_request(
                        method=method,
                        url=url,
                        status_code=status_code,
                        duration_ms=duration_ms,
                        request_headers=dict(headers) if headers else None,
                        response_size=response_size,
                        error=error,
                    )
                except Exception as e:
                    logger.debug(f"Failed to record HTTP client request: {e}")
        
        requests.Session.request = patched_request
        _requests_patched = True
        logger.debug("Orbit HTTP client watcher installed")
        
    except ImportError:
        logger.debug("requests library not installed, HTTP client watcher disabled")
    except Exception as e:
        logger.warning(f"Failed to install HTTP client watcher: {e}")


# =============================================================================
# Install All Watchers
# =============================================================================

def install_all_watchers():
    """Install all Phase 1 watchers."""
    config = get_config()
    
    if config.get("RECORD_COMMANDS", True):
        install_command_watcher()
    
    if config.get("RECORD_CACHE", True):
        install_cache_watcher()
    
    if config.get("RECORD_MODELS", True):
        install_model_watcher()
    
    if config.get("RECORD_HTTP_CLIENT", True):
        install_http_client_watcher()
