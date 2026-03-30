"""
Django Orbit Log Handler

Custom Python logging handler that captures logs to OrbitEntry.
"""

import logging
import threading
from typing import Optional

from orbit.conf import get_config
from orbit.watchers import cachalot_disabled

# Thread-local storage for current family hash
_local = threading.local()


def get_current_family_hash() -> Optional[str]:
    """Get the family hash for the current request context."""
    return getattr(_local, "family_hash", None)


def set_current_family_hash(family_hash: Optional[str]) -> None:
    """Set the family hash for the current request context."""
    _local.family_hash = family_hash


class OrbitLogHandler(logging.Handler):
    """
    Custom logging handler that captures log records to Django Orbit.

    Integrates with Python's standard logging module to automatically
    store log entries in the OrbitEntry database.
    """

    def __init__(self, level=logging.NOTSET):
        super().__init__(level)
        self._enabled = True

    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a log record to Orbit.

        Args:
            record: The log record to process
        """
        config = get_config()

        # Check if logging is enabled
        if not config.get("ENABLED", True):
            return

        if not config.get("RECORD_LOGS", True):
            return

        # Avoid recursion from our own logging
        if record.name.startswith("orbit"):
            return

        # Avoid Django's internal logs that aren't useful
        skip_loggers = [
            "django.request",  # We capture this via middleware
            "django.db.backends",  # We capture this via SQL recorder
            "django.security",
        ]

        if any(record.name.startswith(skip) for skip in skip_loggers):
            return

        try:
            self._save_log_entry(record)
        except Exception:
            pass

    def _save_log_entry(self, record: logging.LogRecord) -> None:
        """
        Save a log record to the database.

        Args:
            record: The log record to save
        """
        # Import here to avoid circular imports
        from orbit.models import OrbitEntry
        from orbit.utils import serialize_for_json

        # Build payload
        payload = {
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "filename": record.filename,
            "lineno": record.lineno,
            "function": record.funcName,
            "process": record.process,
            "thread": record.thread,
            "thread_name": record.threadName,
        }

        # Include exception info if present
        if record.exc_info:
            exc_type, exc_value, exc_tb = record.exc_info
            if exc_value:
                from orbit.utils import get_exception_info

                payload["exception"] = get_exception_info(exc_value)

        # Include extra fields from LogRecord
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in (
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "exc_info",
                "exc_text",
                "thread",
                "threadName",
                "message",
                "asctime",
            ):
                try:
                    extra_fields[key] = serialize_for_json(value)
                except Exception:
                    extra_fields[key] = str(value)

        if extra_fields:
            payload["extra"] = extra_fields

        # Get family hash if in request context
        family_hash = get_current_family_hash()

        # Create entry
        try:
            with cachalot_disabled():
                OrbitEntry.objects.create(
                    type=OrbitEntry.TYPE_LOG,
                    family_hash=family_hash,
                    payload=payload,
                )
        except Exception:
            pass


class OrbitLogContext:
    """
    Context manager for setting the log context (family hash).

    Usage:
        with OrbitLogContext(family_hash="abc123"):
            logger.info("This will be linked to the request")
    """

    def __init__(self, family_hash: str):
        self.family_hash = family_hash
        self.previous_hash = None

    def __enter__(self):
        self.previous_hash = get_current_family_hash()
        set_current_family_hash(self.family_hash)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        set_current_family_hash(self.previous_hash)
        return False
