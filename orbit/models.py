"""
Django Orbit Models

Central model for storing all telemetry events.
"""

import uuid

from django.db import models


class OrbitEntryManager(models.Manager):
    """Custom manager for OrbitEntry with useful query methods."""

    def requests(self):
        """Get all request entries."""
        return self.filter(type=OrbitEntry.TYPE_REQUEST)

    def queries(self):
        """Get all SQL query entries."""
        return self.filter(type=OrbitEntry.TYPE_QUERY)

    def logs(self):
        """Get all log entries."""
        return self.filter(type=OrbitEntry.TYPE_LOG)

    def exceptions(self):
        """Get all exception entries."""
        return self.filter(type=OrbitEntry.TYPE_EXCEPTION)

    def jobs(self):
        """Get all job/task entries."""
        return self.filter(type=OrbitEntry.TYPE_JOB)

    def commands(self):
        """Get all management command entries."""
        return self.filter(type=OrbitEntry.TYPE_COMMAND)

    def cache_ops(self):
        """Get all cache operation entries."""
        return self.filter(type=OrbitEntry.TYPE_CACHE)

    def models(self):
        """Get all model event entries."""
        return self.filter(type=OrbitEntry.TYPE_MODEL)

    def http_client(self):
        """Get all outgoing HTTP request entries."""
        return self.filter(type=OrbitEntry.TYPE_HTTP_CLIENT)

    def dumps(self):
        """Get all dump entries."""
        return self.filter(type=OrbitEntry.TYPE_DUMP)

    def mails(self):
        """Get all mail entries."""
        return self.filter(type=OrbitEntry.TYPE_MAIL)

    def signals(self):
        """Get all signal entries."""
        return self.filter(type=OrbitEntry.TYPE_SIGNAL)

    def redis_ops(self):
        """Get all Redis operation entries."""
        return self.filter(type=OrbitEntry.TYPE_REDIS)

    def gates(self):
        """Get all gate/permission entries."""
        return self.filter(type=OrbitEntry.TYPE_GATE)

    def slow_queries(self):
        """Get all slow queries (marked in payload)."""
        return self.filter(type=OrbitEntry.TYPE_QUERY, payload__is_slow=True)

    def for_family(self, family_hash):
        """Get all entries for a specific request family."""
        return self.filter(family_hash=family_hash).order_by("created_at")

    def cleanup_old_entries(self, limit=1000):
        """
        Remove old entries keeping only the most recent `limit` entries.
        """
        count = self.count()
        if count > limit:
            # Get IDs of entries to keep
            keep_ids = self.order_by("-created_at").values_list("id", flat=True)[:limit]
            # Delete entries not in keep list
            deleted, _ = self.exclude(id__in=list(keep_ids)).delete()
            return deleted
        return 0


class OrbitEntry(models.Model):
    """
    Central model for storing all telemetry events in Django Orbit.

    Uses a flexible JSONField for payload to accommodate different
    event types without requiring schema changes.
    """

    # Entry type choices
    TYPE_REQUEST = "request"
    TYPE_QUERY = "query"
    TYPE_LOG = "log"
    TYPE_EXCEPTION = "exception"
    TYPE_JOB = "job"
    # Phase 1 types
    TYPE_COMMAND = "command"
    TYPE_CACHE = "cache"
    TYPE_MODEL = "model"
    TYPE_HTTP_CLIENT = "http_client"
    TYPE_DUMP = "dump"
    # Phase 2 types (v0.4.0)
    TYPE_MAIL = "mail"
    TYPE_SIGNAL = "signal"
    # Phase 3 types (v0.5.0)
    TYPE_REDIS = "redis"
    TYPE_GATE = "gate"
    TYPE_TRANSACTION = "transaction"
    TYPE_STORAGE = "storage"

    TYPE_CHOICES = [
        (TYPE_REQUEST, "HTTP Request"),
        (TYPE_QUERY, "SQL Query"),
        (TYPE_LOG, "Log Entry"),
        (TYPE_EXCEPTION, "Exception"),
        (TYPE_JOB, "Background Job"),
        (TYPE_COMMAND, "Command"),
        (TYPE_CACHE, "Cache"),
        (TYPE_MODEL, "Model Event"),
        (TYPE_HTTP_CLIENT, "HTTP Client"),
        (TYPE_DUMP, "Dump"),
        (TYPE_MAIL, "Mail"),
        (TYPE_SIGNAL, "Signal"),
        (TYPE_REDIS, "Redis"),
        (TYPE_GATE, "Gate/Policy"),
        (TYPE_TRANSACTION, "Transaction"),
        (TYPE_STORAGE, "Storage"),
    ]

    # Type to icon mapping for UI
    TYPE_ICONS = {
        TYPE_REQUEST: "globe",
        TYPE_QUERY: "database",
        TYPE_LOG: "file-text",
        TYPE_EXCEPTION: "alert-triangle",
        TYPE_JOB: "clock",
        TYPE_COMMAND: "terminal",
        TYPE_CACHE: "hard-drive",
        TYPE_MODEL: "box",
        TYPE_HTTP_CLIENT: "send",
        TYPE_DUMP: "bug",
        TYPE_MAIL: "mail",
        TYPE_SIGNAL: "zap",
        TYPE_REDIS: "server",
        TYPE_GATE: "shield",
        TYPE_TRANSACTION: "layers",
        TYPE_STORAGE: "archive",
    }

    # Type to color mapping for UI
    TYPE_COLORS = {
        TYPE_REQUEST: "cyan",
        TYPE_QUERY: "emerald",
        TYPE_LOG: "slate",
        TYPE_EXCEPTION: "rose",
        TYPE_JOB: "amber",
        TYPE_COMMAND: "violet",
        TYPE_CACHE: "orange",
        TYPE_MODEL: "blue",
        TYPE_HTTP_CLIENT: "pink",
        TYPE_DUMP: "lime",
        TYPE_MAIL: "fuchsia",
        TYPE_SIGNAL: "yellow",
        TYPE_REDIS: "red",
        TYPE_GATE: "indigo",
        TYPE_TRANSACTION: "teal",
        TYPE_STORAGE: "sky",
    }

    # Primary key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for this entry",
    )

    # Entry classification
    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        db_index=True,
        help_text="Type of telemetry entry",
    )

    # Family grouping (links queries/logs to parent request)
    family_hash = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        db_index=True,
        help_text="Hash to group related entries (e.g., all queries for one request)",
    )

    # Flexible payload storage
    payload = models.JSONField(
        default=dict, help_text="JSON payload containing event-specific data"
    )

    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True, db_index=True, help_text="When this entry was created"
    )

    # Performance metric
    duration_ms = models.FloatField(
        null=True,
        blank=True,
        help_text="Duration in milliseconds (for performance tracking)",
    )

    # Custom manager
    objects = OrbitEntryManager()

    class Meta:
        verbose_name = "Orbit Entry"
        verbose_name_plural = "Orbit Entries"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at", "type"]),
            models.Index(fields=["family_hash", "created_at"]),
        ]

    def __str__(self):
        return f"[{self.type.upper()}] {self.created_at.strftime('%H:%M:%S')}"

    @property
    def icon(self):
        """Get the icon name for this entry type."""
        return self.TYPE_ICONS.get(self.type, "circle")

    @property
    def color(self):
        """Get the color name for this entry type."""
        return self.TYPE_COLORS.get(self.type, "slate")

    @property
    def summary(self):
        """Get a human-readable summary of this entry."""
        payload = self.payload or {}

        if self.type == self.TYPE_REQUEST:
            method = payload.get("method", "?")
            path = payload.get("path", "?")
            status = payload.get("status_code", "?")
            return f"{method} {path} → {status}"

        elif self.type == self.TYPE_QUERY:
            sql = payload.get("sql", "")
            # Truncate long queries
            if len(sql) > 80:
                sql = sql[:77] + "..."
            return sql

        elif self.type == self.TYPE_LOG:
            level = payload.get("level", "INFO")
            message = payload.get("message", "")
            if len(message) > 80:
                message = message[:77] + "..."
            return f"[{level}] {message}"

        elif self.type == self.TYPE_EXCEPTION:
            exc_type = payload.get("exception_type", "Exception")
            message = payload.get("message", "")
            if len(message) > 60:
                message = message[:57] + "..."
            return f"{exc_type}: {message}"

        elif self.type == self.TYPE_JOB:
            name = payload.get("name", "Unknown Job")
            status = payload.get("status", "?")
            return f"{name} ({status})"

        elif self.type == self.TYPE_COMMAND:
            command = payload.get("command", "unknown")
            exit_code = payload.get("exit_code", "?")
            return f"{command} → exit {exit_code}"

        elif self.type == self.TYPE_CACHE:
            operation = payload.get("operation", "?")
            key = payload.get("key", "")
            if len(key) > 40:
                key = key[:37] + "..."
            hit = payload.get("hit")
            hit_str = " (hit)" if hit else " (miss)" if hit is False else ""
            return f"{operation.upper()} {key}{hit_str}"

        elif self.type == self.TYPE_MODEL:
            model = payload.get("model", "?")
            action = payload.get("action", "?")
            pk = payload.get("pk", "?")
            return f"{model} {action} (pk={pk})"

        elif self.type == self.TYPE_HTTP_CLIENT:
            method = payload.get("method", "?")
            url = payload.get("url", "?")
            if len(url) > 50:
                url = url[:47] + "..."
            status = payload.get("status_code", "?")
            return f"{method} {url} → {status}"

        elif self.type == self.TYPE_DUMP:
            count = payload.get("count", 1)
            caller = payload.get("caller", {})
            func = caller.get("function", "unknown")
            return f"dump() in {func} ({count} value{'s' if count > 1 else ''})"

        elif self.type == self.TYPE_MAIL:
            subject = payload.get("subject", "(no subject)")
            to = payload.get("to", [])
            to_str = to[0] if to else "?"
            if len(to) > 1:
                to_str += f" (+{len(to) - 1})"
            return f"{subject[:40]} → {to_str}"

        elif self.type == self.TYPE_SIGNAL:
            signal = payload.get("signal", "unknown")
            sender = payload.get("sender") or "?"
            # Clean up sender if it's a class reference
            if sender.startswith("<class '"):
                sender = sender.replace("<class '", "").replace("'>", "")
                if "." in sender:
                    sender = sender.split(".")[-1]  # Get just the class name
            elif len(sender) > 30:
                sender = sender[:27] + "..."
            # Keep full signal path for developer context (truncate if too long)
            if len(signal) > 50:
                signal = "..." + signal[-47:]
            return f"{signal} → {sender}"

        elif self.type == self.TYPE_REDIS:
            operation = payload.get("operation", "?")
            key = payload.get("key", "?")
            if key and len(key) > 40:
                key = key[:37] + "..."
            result_size = payload.get("result_size")
            size_str = f" ({result_size} items)" if result_size is not None else ""
            return f"{operation} {key}{size_str}"

        elif self.type == self.TYPE_GATE:
            permission = payload.get("permission", "?")
            user = payload.get("user", "?")
            result = payload.get("result", "?")
            icon = "✓" if result == "granted" else "✗"
            return f"{icon} {permission} → {user}"
        
        elif self.type == self.TYPE_TRANSACTION:
            status = payload.get("status", "?")
            using = payload.get("using", "default")
            exception = payload.get("exception")
            icon = "✓" if status == "committed" else "✗"
            duration = f" {self.duration_ms:.0f}ms" if self.duration_ms else ""
            if status == "rolled_back" and exception:
                # Show exception name for rollbacks
                exc_short = exception.split(":")[0] if ":" in exception else exception
                if len(exc_short) > 25:
                    exc_short = exc_short[:22] + "..."
                return f"{icon} rollback: {exc_short}{duration} ({using})"
            return f"{icon} {status}{duration} ({using})"

        elif self.type == self.TYPE_STORAGE:
            operation = payload.get("operation", "?")
            path = payload.get("path", "?")
            backend = payload.get("backend", "")
            size = payload.get("size")
            # Truncate path but keep filename visible
            if len(path) > 35:
                path = "..." + path[-32:]
            # Format size
            size_str = ""
            if size and operation == "save":
                if size >= 1024 * 1024:
                    size_str = f" ({size / 1024 / 1024:.1f}MB)"
                elif size >= 1024:
                    size_str = f" ({size / 1024:.1f}KB)"
                else:
                    size_str = f" ({size}B)"
            # Short backend name
            backend_short = backend.replace("Storage", "") if backend else ""
            return f"{operation.upper()} {path}{size_str} [{backend_short}]"

        return str(self.id)[:8]

    @property
    def is_error(self):
        """Check if this entry represents an error state."""
        if self.type == self.TYPE_EXCEPTION:
            return True
        if self.type == self.TYPE_REQUEST:
            status = self.payload.get("status_code", 200)
            return status >= 400
        if self.type == self.TYPE_LOG:
            level = self.payload.get("level", "")
            return level in ("ERROR", "CRITICAL")
        return False

    @property
    def is_warning(self):
        """Check if this entry represents a warning state."""
        if self.type == self.TYPE_QUERY:
            return self.payload.get("is_slow", False)
        if self.type == self.TYPE_LOG:
            return self.payload.get("level") == "WARNING"
        return False
