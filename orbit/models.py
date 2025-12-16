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
    
    def slow_queries(self):
        """Get all slow queries (marked in payload)."""
        return self.filter(
            type=OrbitEntry.TYPE_QUERY,
            payload__is_slow=True
        )
    
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
            keep_ids = self.order_by("-created_at").values_list(
                "id", flat=True
            )[:limit]
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
    
    TYPE_CHOICES = [
        (TYPE_REQUEST, "HTTP Request"),
        (TYPE_QUERY, "SQL Query"),
        (TYPE_LOG, "Log Entry"),
        (TYPE_EXCEPTION, "Exception"),
        (TYPE_JOB, "Background Job"),
    ]
    
    # Type to icon mapping for UI
    TYPE_ICONS = {
        TYPE_REQUEST: "globe",
        TYPE_QUERY: "database",
        TYPE_LOG: "file-text",
        TYPE_EXCEPTION: "alert-triangle",
        TYPE_JOB: "clock",
    }
    
    # Type to color mapping for UI
    TYPE_COLORS = {
        TYPE_REQUEST: "cyan",
        TYPE_QUERY: "emerald",
        TYPE_LOG: "slate",
        TYPE_EXCEPTION: "rose",
        TYPE_JOB: "amber",
    }
    
    # Primary key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for this entry"
    )
    
    # Entry classification
    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        db_index=True,
        help_text="Type of telemetry entry"
    )
    
    # Family grouping (links queries/logs to parent request)
    family_hash = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        db_index=True,
        help_text="Hash to group related entries (e.g., all queries for one request)"
    )
    
    # Flexible payload storage
    payload = models.JSONField(
        default=dict,
        help_text="JSON payload containing event-specific data"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When this entry was created"
    )
    
    # Performance metric
    duration_ms = models.FloatField(
        null=True,
        blank=True,
        help_text="Duration in milliseconds (for performance tracking)"
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
