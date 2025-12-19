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


def record_command(
    command_name: str,
    args: tuple,
    options: dict,
    exit_code: int,
    output: str = "",
    duration_ms: float = 0,
):
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
    ignore_commands = config.get(
        "IGNORE_COMMANDS", ["runserver", "shell", "dbshell", "showmigrations"]
    )
    if command_name in ignore_commands:
        return

    from orbit.models import OrbitEntry

    # Filter sensitive options
    filtered_options = {
        k: v
        for k, v in options.items()
        if k not in ("settings", "pythonpath", "traceback", "verbosity")
    }

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

    try:
        OrbitEntry.objects.create(
            type=OrbitEntry.TYPE_COMMAND,
            payload=payload,
            duration_ms=duration_ms,
        )
    except Exception:
        pass


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
                            duration_ms=duration_ms,
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


def record_cache_operation(
    operation: str,
    key: str,
    hit: Optional[bool] = None,
    backend: str = "default",
    ttl: Optional[int] = None,
):
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

    try:
        OrbitEntry.objects.create(
            type=OrbitEntry.TYPE_CACHE,
            payload=payload,
        )
    except Exception:
        pass


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

    _miss_sentinel = object()

    @functools.wraps(original_get)
    def patched_get(key, default=None, version=None):
        result = original_get(key, default=_miss_sentinel, version=version)

        if result is _miss_sentinel:
            hit = False
            result = default
        else:
            hit = True

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

    try:
        OrbitEntry.objects.create(
            type=OrbitEntry.TYPE_MODEL,
            payload=payload,
        )
    except Exception:
        pass


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
        from django.db.models.signals import post_delete, post_save, pre_save

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


def record_http_client_request(
    method: str,
    url: str,
    status_code: Optional[int],
    duration_ms: float,
    request_headers: Optional[Dict] = None,
    response_size: Optional[int] = None,
    error: Optional[str] = None,
):
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

    try:
        OrbitEntry.objects.create(
            type=OrbitEntry.TYPE_HTTP_CLIENT,
            payload=payload,
            duration_ms=duration_ms,
        )
    except Exception:
        pass


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
# Mail Watcher (v0.4.0)
# =============================================================================

_mail_patched = False


def record_mail(message):
    """
    Record an outgoing email to Orbit.

    Args:
        message: EmailMessage instance
    """
    config = get_config()
    if not config.get("ENABLED", True):
        return

    if not config.get("RECORD_MAIL", True):
        return

    from orbit.models import OrbitEntry

    # Extract attachments info
    attachments = []
    for attachment in getattr(message, "attachments", []):
        if isinstance(attachment, tuple) and len(attachment) >= 2:
            name = attachment[0]
            content = attachment[1]
            content_type = attachment[2] if len(attachment) > 2 else "application/octet-stream"
            attachments.append({
                "name": name,
                "size": len(content) if content else 0,
                "content_type": content_type,
            })

    payload = {
        "subject": getattr(message, "subject", ""),
        "from_email": getattr(message, "from_email", ""),
        "to": list(getattr(message, "to", [])),
        "cc": list(getattr(message, "cc", [])),
        "bcc": list(getattr(message, "bcc", [])),
        "body": getattr(message, "body", "")[:2000],
        "attachments": attachments,
    }

    # Check for HTML alternative
    if hasattr(message, "alternatives"):
        for content, mimetype in message.alternatives:
            if mimetype == "text/html":
                payload["html_body"] = content[:5000]
                break

    try:
        OrbitEntry.objects.create(
            type=OrbitEntry.TYPE_MAIL,
            payload=payload,
        )
    except Exception:
        pass


def install_mail_watcher():
    """
    Install the mail watcher by patching EmailMessage.send.
    """
    global _mail_patched

    if _mail_patched:
        return

    try:
        from django.core.mail import EmailMessage

        original_send = EmailMessage.send

        @functools.wraps(original_send)
        def patched_send(self, fail_silently=False):
            result = original_send(self, fail_silently)
            try:
                record_mail(self)
            except Exception as e:
                logger.debug(f"Failed to record mail: {e}")
            return result

        EmailMessage.send = patched_send
        _mail_patched = True
        logger.debug("Orbit mail watcher installed")

    except Exception as e:
        logger.warning(f"Failed to install mail watcher: {e}")


# =============================================================================
# Signal Watcher (v0.4.0)
# =============================================================================

_signal_patched = False
_signal_registry = {}


def record_signal(signal, sender, **kwargs):
    """
    Record a Django signal dispatch to Orbit.

    Args:
        signal: The Signal instance
        sender: The sender class/object
        **kwargs: Signal payload
    """
    config = get_config()
    if not config.get("ENABLED", True):
        return

    if not config.get("RECORD_SIGNALS", True):
        return

    # Get signal name from registry or try to extract a better name
    signal_name = _signal_registry.get(id(signal))
    if signal_name is None:
        # Try to get a cleaner name from the signal object
        signal_str = str(signal)
        if "Signal" in signal_str and "object at" in signal_str:
            # It's a raw signal object like <django.dispatch.dispatcher.Signal object at 0x...>
            # Try to extract module path
            if hasattr(signal, '__module__'):
                module = getattr(signal, '__module__', '')
                if module:
                    signal_name = f"{module}.signal"
                else:
                    signal_name = "django.signal"
            else:
                signal_name = "django.signal"
        else:
            signal_name = signal_str[:60]

    # Check if signal should be ignored
    ignore_signals = config.get("IGNORE_SIGNALS", [])
    if signal_name in ignore_signals:
        return

    from orbit.models import OrbitEntry

    # Skip Orbit's own model to avoid infinite loops
    if sender is not None:
        sender_name = getattr(sender, "__name__", str(sender))
        if sender_name == "OrbitEntry" or "OrbitEntry" in str(sender):
            return

    # Get receiver names
    receivers = []
    for receiver_ref in getattr(signal, "receivers", []):
        if isinstance(receiver_ref, tuple) and len(receiver_ref) >= 2:
            receiver = receiver_ref[1]
            if callable(receiver):
                try:
                    receivers.append(receiver().__name__ if hasattr(receiver, '__call__') else str(receiver))
                except Exception:
                    receivers.append(str(receiver))

    # Serialize kwargs safely
    serialized_kwargs = {}
    for k, v in kwargs.items():
        if k == "signal":
            continue
        try:
            serialized_kwargs[k] = repr(v)[:200]
        except Exception:
            serialized_kwargs[k] = "<unserializable>"

    payload = {
        "signal": signal_name,
        "sender": str(sender)[:100] if sender else None,
        "receivers_count": len(getattr(signal, "receivers", [])),
        "kwargs": serialized_kwargs,
    }

    try:
        OrbitEntry.objects.create(
            type=OrbitEntry.TYPE_SIGNAL,
            payload=payload,
        )
    except Exception:
        pass


def install_signal_watcher():
    """
    Install the signal watcher by patching Signal.send.
    """
    global _signal_patched, _signal_registry

    if _signal_patched:
        return

    try:
        from django.dispatch import Signal

        # Build signal registry for friendly names
        from django.db.models import signals as model_signals
        _signal_registry[id(model_signals.pre_save)] = "django.db.models.signals.pre_save"
        _signal_registry[id(model_signals.post_save)] = "django.db.models.signals.post_save"
        _signal_registry[id(model_signals.pre_delete)] = "django.db.models.signals.pre_delete"
        _signal_registry[id(model_signals.post_delete)] = "django.db.models.signals.post_delete"
        _signal_registry[id(model_signals.pre_init)] = "django.db.models.signals.pre_init"
        _signal_registry[id(model_signals.post_init)] = "django.db.models.signals.post_init"
        _signal_registry[id(model_signals.m2m_changed)] = "django.db.models.signals.m2m_changed"

        original_send = Signal.send

        @functools.wraps(original_send)
        def patched_send(self, sender, **kwargs):
            result = original_send(self, sender, **kwargs)
            try:
                record_signal(self, sender, **kwargs)
            except Exception as e:
                logger.debug(f"Failed to record signal: {e}")
            return result

        Signal.send = patched_send
        _signal_patched = True
        logger.debug("Orbit signal watcher installed")

    except Exception as e:
        logger.warning(f"Failed to install signal watcher: {e}")


# =============================================================================
# Celery Jobs Watcher
# =============================================================================

_celery_patched = False


def record_celery_task(
    task_id: str,
    task_name: str,
    args: tuple,
    kwargs: dict,
    status: str,
    result: Any = None,
    exception: str = None,
    duration_ms: float = 0,
    retries: int = 0,
):
    """
    Record a Celery task execution to Orbit.

    Args:
        task_id: Celery task ID
        task_name: Name of the task
        args: Task positional arguments
        kwargs: Task keyword arguments
        status: Task status (started, success, failure, retry)
        result: Task result (for success)
        exception: Exception message (for failure)
        duration_ms: Execution duration
        retries: Number of retries
    """
    config = get_config()
    if not config.get("ENABLED", True):
        return

    if not config.get("RECORD_JOBS", True):
        return

    from orbit.models import OrbitEntry

    # Serialize args/kwargs safely
    try:
        serialized_args = repr(args)[:500]
    except Exception:
        serialized_args = "<unserializable>"
    
    try:
        serialized_kwargs = repr(kwargs)[:500]
    except Exception:
        serialized_kwargs = "<unserializable>"

    payload = {
        "task_id": task_id,
        "name": task_name,
        "status": status,
        "args": serialized_args,
        "kwargs": serialized_kwargs,
        "retries": retries,
    }

    if result is not None and status == "success":
        try:
            payload["result"] = repr(result)[:200]
        except Exception:
            payload["result"] = "<unserializable>"

    if exception:
        payload["error"] = exception

    try:
        OrbitEntry.objects.create(
            type=OrbitEntry.TYPE_JOB,
            payload=payload,
            duration_ms=duration_ms,
        )
    except Exception:
        pass


def install_celery_watcher():
    """
    Install the Celery task watcher using Celery signals.
    """
    global _celery_patched

    if _celery_patched:
        return

    try:
        from celery import signals
        from celery import current_task
        import threading

        # Track task start times
        _task_start_times = threading.local()

        @signals.task_prerun.connect
        def task_prerun_handler(task_id, task, args, kwargs, **kw):
            _task_start_times.times = getattr(_task_start_times, 'times', {})
            _task_start_times.times[task_id] = time.time()

        @signals.task_postrun.connect
        def task_postrun_handler(task_id, task, args, kwargs, retval, state, **kw):
            start_time = getattr(_task_start_times, 'times', {}).get(task_id)
            duration_ms = 0
            if start_time:
                duration_ms = (time.time() - start_time) * 1000
                _task_start_times.times.pop(task_id, None)

            status = "success" if state == "SUCCESS" else state.lower()
            record_celery_task(
                task_id=task_id,
                task_name=task.name,
                args=args,
                kwargs=kwargs,
                status=status,
                result=retval if state == "SUCCESS" else None,
                duration_ms=duration_ms,
                retries=getattr(task.request, 'retries', 0),
            )

        @signals.task_failure.connect
        def task_failure_handler(task_id, exception, args, kwargs, traceback, einfo, **kw):
            start_time = getattr(_task_start_times, 'times', {}).get(task_id)
            duration_ms = 0
            if start_time:
                duration_ms = (time.time() - start_time) * 1000
                _task_start_times.times.pop(task_id, None)

            record_celery_task(
                task_id=task_id,
                task_name=kw.get('sender', {}).name if hasattr(kw.get('sender'), 'name') else 'unknown',
                args=args,
                kwargs=kwargs,
                status="failure",
                exception=str(exception),
                duration_ms=duration_ms,
            )

        _celery_patched = True
        logger.debug("Orbit Celery watcher installed")

    except ImportError:
        logger.debug("Celery not installed, skipping Celery watcher")
    except Exception as e:
        logger.warning(f"Failed to install Celery watcher: {e}")


# =============================================================================
# Redis Watcher
# =============================================================================

_redis_patched = False


def record_redis_operation(
    operation: str,
    key: str = None,
    duration_ms: float = 0,
    result_size: int = None,
    error: str = None,
):
    """
    Record a Redis operation to Orbit.

    Args:
        operation: Operation type (GET, SET, DEL, HGET, etc.)
        key: Redis key
        duration_ms: Operation duration
        result_size: Size of result in bytes
        error: Error message if failed
    """
    config = get_config()
    if not config.get("ENABLED", True):
        return

    if not config.get("RECORD_REDIS", True):
        return

    from orbit.models import OrbitEntry

    payload = {
        "operation": operation.upper(),
        "key": key[:200] if key else None,
    }

    if result_size is not None:
        payload["result_size"] = result_size

    if error:
        payload["error"] = error

    try:
        OrbitEntry.objects.create(
            type=OrbitEntry.TYPE_REDIS,
            payload=payload,
            duration_ms=duration_ms,
        )
    except Exception:
        pass


def install_redis_watcher():
    """
    Install the Redis watcher by patching redis-py client.
    """
    global _redis_patched

    if _redis_patched:
        return

    try:
        import redis

        # Commands to track
        tracked_commands = [
            'get', 'set', 'setex', 'setnx', 'delete', 'del',
            'hget', 'hset', 'hdel', 'hgetall',
            'lpush', 'rpush', 'lpop', 'rpop', 'lrange',
            'sadd', 'srem', 'smembers',
            'zadd', 'zrem', 'zrange',
            'incr', 'decr', 'expire', 'ttl',
            'exists', 'keys', 'scan',
        ]

        original_execute_command = redis.Redis.execute_command

        @functools.wraps(original_execute_command)
        def patched_execute_command(self, *args, **options):
            if not args:
                return original_execute_command(self, *args, **options)

            command = args[0].lower() if isinstance(args[0], str) else str(args[0]).lower()
            key = args[1] if len(args) > 1 else None
            if isinstance(key, bytes):
                key = key.decode('utf-8', errors='replace')

            start_time = time.time()
            error = None
            result = None

            try:
                result = original_execute_command(self, *args, **options)
                return result
            except Exception as e:
                error = str(e)
                raise
            finally:
                if command in tracked_commands:
                    duration_ms = (time.time() - start_time) * 1000
                    result_size = None
                    if result is not None:
                        try:
                            if isinstance(result, bytes):
                                result_size = len(result)
                            elif isinstance(result, (list, set)):
                                result_size = len(result)
                        except Exception:
                            pass

                    try:
                        record_redis_operation(
                            operation=command,
                            key=str(key) if key else None,
                            duration_ms=duration_ms,
                            result_size=result_size,
                            error=error,
                        )
                    except Exception:
                        pass

        redis.Redis.execute_command = patched_execute_command
        _redis_patched = True
        logger.debug("Orbit Redis watcher installed")

    except ImportError:
        logger.debug("redis-py not installed, skipping Redis watcher")
    except Exception as e:
        logger.warning(f"Failed to install Redis watcher: {e}")


# =============================================================================
# Gates/Policies Watcher
# =============================================================================

_gates_patched = False


def record_permission_check(
    user: str,
    permission: str,
    obj: str = None,
    result: bool = False,
    backend: str = None,
):
    """
    Record a permission check to Orbit.

    Args:
        user: User identifier
        permission: Permission being checked
        obj: Object being checked against
        result: Whether permission was granted
        backend: Auth backend used
    """
    config = get_config()
    if not config.get("ENABLED", True):
        return

    if not config.get("RECORD_GATES", True):
        return

    from orbit.models import OrbitEntry

    payload = {
        "user": user[:100],
        "permission": permission,
        "result": "granted" if result else "denied",
    }

    if obj:
        payload["object"] = obj[:100]

    if backend:
        payload["backend"] = backend

    try:
        OrbitEntry.objects.create(
            type=OrbitEntry.TYPE_GATE,
            payload=payload,
        )
    except Exception:
        pass


def install_gates_watcher():
    """
    Install the permission/gates watcher by patching Django's permission backend.
    """
    global _gates_patched

    if _gates_patched:
        return

    try:
        from django.contrib.auth.backends import ModelBackend

        original_has_perm = ModelBackend.has_perm

        @functools.wraps(original_has_perm)
        def patched_has_perm(self, user_obj, perm, obj=None):
            result = original_has_perm(self, user_obj, perm, obj)

            try:
                user_str = str(getattr(user_obj, 'username', user_obj))
                obj_str = None
                if obj:
                    obj_str = f"{type(obj).__name__}:{getattr(obj, 'pk', obj)}"

                record_permission_check(
                    user=user_str,
                    permission=perm,
                    obj=obj_str,
                    result=result,
                    backend="ModelBackend",
                )
            except Exception:
                pass

            return result

        ModelBackend.has_perm = patched_has_perm
        _gates_patched = True
        logger.debug("Orbit gates watcher installed")

    except Exception as e:
        logger.warning(f"Failed to install gates watcher: {e}")


# =============================================================================
# Django-Q Watcher
# =============================================================================

_djangoq_patched = False


def install_djangoq_watcher():
    """
    Install Django-Q task watcher using django-q signals.
    """
    global _djangoq_patched

    if _djangoq_patched:
        return

    try:
        from django_q.signals import pre_execute, post_execute
        from orbit.models import OrbitEntry
        import threading

        _task_start_times = threading.local()

        def pre_execute_handler(sender, func, task, **kwargs):
            _task_start_times.times = getattr(_task_start_times, 'times', {})
            _task_start_times.times[task.get('id', '')] = time.time()

        def post_execute_handler(sender, task, **kwargs):
            config = get_config()
            if not config.get("ENABLED", True) or not config.get("RECORD_JOBS", True):
                return

            task_id = task.get('id', '')
            start_time = getattr(_task_start_times, 'times', {}).get(task_id)
            duration_ms = 0
            if start_time:
                duration_ms = (time.time() - start_time) * 1000
                _task_start_times.times.pop(task_id, None)

            payload = {
                "task_id": task_id,
                "name": task.get('name', 'unknown'),
                "status": "success" if task.get('success') else "failure",
                "queue": "django-q",
                "args": repr(task.get('args', []))[:500],
                "kwargs": repr(task.get('kwargs', {}))[:500],
            }

            if not task.get('success'):
                payload["error"] = task.get('result', 'Unknown error')

            try:
                OrbitEntry.objects.create(
                    type=OrbitEntry.TYPE_JOB,
                    payload=payload,
                    duration_ms=duration_ms,
                )
            except Exception:
                pass

        pre_execute.connect(pre_execute_handler)
        post_execute.connect(post_execute_handler)
        _djangoq_patched = True
        logger.debug("Orbit Django-Q watcher installed")

    except ImportError:
        logger.debug("Django-Q not installed, skipping Django-Q watcher")
    except Exception as e:
        logger.warning(f"Failed to install Django-Q watcher: {e}")


# =============================================================================
# RQ (Redis Queue) Watcher
# =============================================================================

_rq_patched = False


def install_rq_watcher():
    """
    Install RQ (Redis Queue) task watcher.
    """
    global _rq_patched

    if _rq_patched:
        return

    try:
        from rq import Worker
        from rq.job import Job
        from orbit.models import OrbitEntry

        original_perform_job = Worker.perform_job

        def patched_perform_job(self, job, queue, *args, **kwargs):
            config = get_config()
            if not config.get("ENABLED", True) or not config.get("RECORD_JOBS", True):
                return original_perform_job(self, job, queue, *args, **kwargs)

            start_time = time.time()
            result = original_perform_job(self, job, queue, *args, **kwargs)
            duration_ms = (time.time() - start_time) * 1000

            # Refresh job to get status
            job.refresh()

            payload = {
                "task_id": job.id,
                "name": job.func_name or 'unknown',
                "status": job.get_status() or "unknown",
                "queue": queue.name,
                "args": repr(job.args)[:500],
                "kwargs": repr(job.kwargs)[:500],
            }

            if job.is_failed:
                payload["status"] = "failure"
                payload["error"] = str(job.exc_info) if job.exc_info else "Unknown error"

            try:
                OrbitEntry.objects.create(
                    type=OrbitEntry.TYPE_JOB,
                    payload=payload,
                    duration_ms=duration_ms,
                )
            except Exception:
                pass

            return result

        Worker.perform_job = patched_perform_job
        _rq_patched = True
        logger.debug("Orbit RQ watcher installed")

    except ImportError:
        logger.debug("RQ not installed, skipping RQ watcher")
    except Exception as e:
        logger.warning(f"Failed to install RQ watcher: {e}")


# =============================================================================
# APScheduler Watcher
# =============================================================================

_apscheduler_patched = False


def install_apscheduler_watcher():
    """
    Install APScheduler watcher to track scheduled job executions.
    """
    global _apscheduler_patched

    if _apscheduler_patched:
        return

    try:
        from apscheduler.events import (
            EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED,
            JobExecutionEvent
        )
        from orbit.models import OrbitEntry

        def job_listener(event):
            config = get_config()
            if not config.get("ENABLED", True) or not config.get("RECORD_JOBS", True):
                return

            if not isinstance(event, JobExecutionEvent):
                return

            status = "success"
            error = None

            if event.exception:
                status = "failure"
                error = str(event.exception)
            elif hasattr(event, 'code'):
                if event.code == EVENT_JOB_MISSED:
                    status = "missed"

            duration_ms = 0
            if hasattr(event, 'run_time') and event.run_time:
                duration_ms = event.run_time * 1000

            payload = {
                "task_id": event.job_id,
                "name": event.job_id,
                "status": status,
                "queue": "apscheduler",
                "scheduled_time": event.scheduled_run_time.isoformat() if event.scheduled_run_time else None,
            }

            if error:
                payload["error"] = error[:500]

            try:
                OrbitEntry.objects.create(
                    type=OrbitEntry.TYPE_JOB,
                    payload=payload,
                    duration_ms=duration_ms,
                )
            except Exception:
                pass

        # Store listener reference for later use
        install_apscheduler_watcher.listener = job_listener
        _apscheduler_patched = True
        logger.debug("Orbit APScheduler watcher prepared (call add_listener on your scheduler)")

    except ImportError:
        logger.debug("APScheduler not installed, skipping APScheduler watcher")
    except Exception as e:
        logger.warning(f"Failed to install APScheduler watcher: {e}")


def register_apscheduler(scheduler):
    """
    Register the APScheduler listener with a scheduler instance.
    
    Usage:
        from apscheduler.schedulers.background import BackgroundScheduler
        from orbit.watchers import register_apscheduler
        
        scheduler = BackgroundScheduler()
        register_apscheduler(scheduler)
    """
    try:
        from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED
        
        install_apscheduler_watcher()
        
        if hasattr(install_apscheduler_watcher, 'listener'):
            scheduler.add_listener(
                install_apscheduler_watcher.listener,
                EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED
            )
            logger.debug("Orbit APScheduler listener registered")
    except Exception as e:
        logger.warning(f"Failed to register APScheduler: {e}")


# =============================================================================
# django-celery-beat Watcher
# =============================================================================

_celerybeat_patched = False


def install_celerybeat_watcher():
    """
    Install django-celery-beat watcher to track periodic task configurations.
    Note: This monitors task scheduling, not execution (use install_celery_watcher for execution).
    """
    global _celerybeat_patched

    if _celerybeat_patched:
        return

    try:
        from django.db.models.signals import post_save, post_delete
        from django_celery_beat.models import PeriodicTask
        from orbit.models import OrbitEntry

        def periodic_task_changed(sender, instance, created, **kwargs):
            config = get_config()
            if not config.get("ENABLED", True) or not config.get("RECORD_JOBS", True):
                return

            action = "created" if created else "updated"
            
            payload = {
                "task_id": f"periodic-{instance.id}",
                "name": instance.name,
                "status": action,
                "queue": "celery-beat",
                "task": instance.task,
                "enabled": instance.enabled,
                "schedule": str(instance.interval or instance.crontab or instance.solar or instance.clocked),
            }

            try:
                OrbitEntry.objects.create(
                    type=OrbitEntry.TYPE_JOB,
                    payload=payload,
                    duration_ms=0,
                )
            except Exception:
                pass

        def periodic_task_deleted(sender, instance, **kwargs):
            config = get_config()
            if not config.get("ENABLED", True) or not config.get("RECORD_JOBS", True):
                return

            payload = {
                "task_id": f"periodic-{instance.id}",
                "name": instance.name,
                "status": "deleted",
                "queue": "celery-beat",
                "task": instance.task,
            }

            try:
                OrbitEntry.objects.create(
                    type=OrbitEntry.TYPE_JOB,
                    payload=payload,
                    duration_ms=0,
                )
            except Exception:
                pass

        post_save.connect(periodic_task_changed, sender=PeriodicTask)
        post_delete.connect(periodic_task_deleted, sender=PeriodicTask)
        _celerybeat_patched = True
        logger.debug("Orbit django-celery-beat watcher installed")

    except ImportError:
        logger.debug("django-celery-beat not installed, skipping celery-beat watcher")
    except Exception as e:
        logger.warning(f"Failed to install celery-beat watcher: {e}")


# =============================================================================
# Install All Watchers
# =============================================================================


def install_all_watchers():
    """Install all Phase 1, Phase 2, and Phase 3 watchers."""
    config = get_config()

    if config.get("RECORD_COMMANDS", True):
        install_command_watcher()

    if config.get("RECORD_CACHE", True):
        install_cache_watcher()

    if config.get("RECORD_MODELS", True):
        install_model_watcher()

    if config.get("RECORD_HTTP_CLIENT", True):
        install_http_client_watcher()

    if config.get("RECORD_MAIL", True):
        install_mail_watcher()

    if config.get("RECORD_SIGNALS", True):
        install_signal_watcher()

    if config.get("RECORD_JOBS", True):
        install_celery_watcher()
        install_djangoq_watcher()
        install_rq_watcher()
        install_celerybeat_watcher()
        install_apscheduler_watcher()

    if config.get("RECORD_REDIS", True):
        install_redis_watcher()

    if config.get("RECORD_GATES", True):
        install_gates_watcher()

