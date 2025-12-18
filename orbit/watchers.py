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
# Install All Watchers
# =============================================================================


def install_all_watchers():
    """Install all Phase 1 and Phase 2 watchers."""
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
