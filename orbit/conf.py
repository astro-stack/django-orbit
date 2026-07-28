"""
Django Orbit Configuration

Provides default configuration and allows user overrides via Django settings.
"""

from collections.abc import Mapping

from django.conf import settings

# Default configuration
DEFAULTS = {
    "ENABLED": True,
    "PROJECT_NAME": "",
    "ENVIRONMENT": "",
    "RELEASE": "",
    # Authentication check (callable or path to function)
    "AUTH_CHECK": None,
    "SLOW_QUERY_THRESHOLD_MS": 500,
    "N_PLUS_ONE_ENABLED": True,
    "N_PLUS_ONE_MIN_OCCURRENCES": 4,
    "N_PLUS_ONE_MAX_QUERIES": 1000,
    "IGNORE_PATHS": ["/orbit/", "/static/", "/admin/jsi18n/", "/favicon.ico"],
    "HIDE_REQUEST_HEADERS": [
        "Authorization",
        "Cookie",
        "X-CSRFToken",
        "X-Orbit-Verification",
    ],
    "HIDE_REQUEST_BODY_KEYS": ["password", "token", "secret", "api_key"],
    # Sensitive-data masking (B5). Any payload key *containing* one of these terms
    # (case-insensitive) has its value redacted. Used to strengthen request masking and,
    # importantly, to scrub data before it is ever sent to an AI provider (Track C).
    "MASK_KEYS": [
        "password",
        "passwd",
        "secret",
        "token",
        "api_key",
        "apikey",
        "access_key",
        "authorization",
        "auth",
        "cookie",
        "csrf",
        "credential",
        "private_key",
        "client_secret",
        "session",
        "ssn",
        "card_number",
    ],
    # When True, every entry's payload is recursively masked at write time (defense in
    # depth across all watchers). Off by default to avoid over-redaction; request
    # headers/body are always masked regardless.
    "MASK_ALL_PAYLOADS": False,
    # B1: optional callable (or dotted path) receiving an OrbitEntry and returning a list
    # of tags to attach. Lets you tag entries (e.g. by tenant, feature, status) for search.
    "TAG_CALLBACK": None,
    # B2: on-demand query EXPLAIN from the detail panel. EXPLAIN_ANALYZE actually executes
    # the statement (only ever allowed for SELECT, in a rolled-back savepoint), so it is off
    # by default.
    "ENABLE_EXPLAIN": True,
    "EXPLAIN_ANALYZE": False,
    "MAX_BODY_SIZE": 65536,  # 64KB
    "STORAGE_LIMIT": 1000,  # Max entries to keep
    # Original watchers
    "RECORD_REQUESTS": True,
    "RECORD_QUERIES": True,
    "RECORD_LOGS": True,
    "RECORD_EXCEPTIONS": True,
    # Opt-in verification correlation. Orbit stores only a validated opaque
    # identifier, never the raw request header, so local release tools can find
    # the request families deliberately generated for one verification run.
    "RECORD_VERIFICATION_CONTEXT": False,
    # Phase 1 watchers
    "RECORD_COMMANDS": True,
    "RECORD_CACHE": True,
    "RECORD_MODELS": True,
    "RECORD_HTTP_CLIENT": True,
    "RECORD_DUMPS": True,
    # Phase 2 watchers (v0.4.0)
    "RECORD_MAIL": True,
    # Django emits many unnamed framework lifecycle signals. Keep these opt-in
    # so an otherwise useful event feed is not dominated by implementation noise.
    "RECORD_SIGNALS": False,
    "RECORD_ANONYMOUS_SIGNALS": False,
    "IGNORE_SIGNALS": [
        "django.db.models.signals.pre_init",
        "django.db.models.signals.post_init",
        "django.db.models.signals.pre_save",
        "django.db.models.signals.post_save",
        "django.db.models.signals.pre_delete",
        "django.db.models.signals.post_delete",
        "django.db.models.signals.m2m_changed",
    ],
    # Phase 3 watchers (v0.5.0)
    "RECORD_JOBS": True,
    "RECORD_REDIS": True,
    "RECORD_GATES": True,
    # Phase 4 watchers (v0.6.0)
    "RECORD_TRANSACTIONS": True,
    "RECORD_STORAGE": True,
    # AI/LLM watcher (v0.12.0+). Metadata-first by default: provider/model/tokens,
    # latency, status and tool-call names are recorded, but prompts/responses and
    # tool-call arguments are not captured unless explicitly enabled.
    "RECORD_LLM": True,
    "LLM_CAPTURE_CONTENT": False,
    "LLM_CAPTURE_TOOL_CALL_ARGUMENTS": False,
    "LLM_MAX_CONTENT_CHARS": 2000,
    # Plug-and-play: if True, watchers fail silently and don't break the app
    "WATCHER_FAIL_SILENTLY": True,
    # Command watcher settings
    "IGNORE_COMMANDS": ["runserver", "shell", "dbshell", "showmigrations"],
    "MAX_COMMAND_OUTPUT": 5000,
    # MCP server (v0.7.0+)
    "MCP_ENABLED": True,
    "MCP_INCLUDE_PAYLOADS": True,
    "MCP_MAX_LIMIT": 100,
    "MCP_MAX_PAYLOAD_CHARS": 12000,
    # Storage backend (v0.8.0+)
    "STORAGE_BACKEND": "orbit.backends.database.DatabaseBackend",
    "STORAGE_DB_ALIAS": "orbit",  # only used by DjangoDBBackend
    # bulk_create batch size for query recording (v0.9.0+)
    # None = single INSERT (original behaviour).
    # Set to a positive integer (e.g. 500) to split large requests into
    # multiple smaller INSERTs, avoiding MySQL's max_allowed_packet limit.
    "BULK_CREATE_BATCH_SIZE": None,
}


def get_config_diagnostics():
    """Return the effective configuration and explain which alias supplied it."""
    orbit_defined = hasattr(settings, "ORBIT")
    orbit_config_defined = hasattr(settings, "ORBIT_CONFIG")
    raw_orbit = getattr(settings, "ORBIT", None)
    raw_orbit_config = getattr(settings, "ORBIT_CONFIG", None)
    orbit_value = dict(raw_orbit) if isinstance(raw_orbit, Mapping) else {}
    orbit_config_value = (
        dict(raw_orbit_config) if isinstance(raw_orbit_config, Mapping) else {}
    )
    invalid_sources = [
        name
        for name, defined, value in (
            ("ORBIT", orbit_defined, raw_orbit),
            ("ORBIT_CONFIG", orbit_config_defined, raw_orbit_config),
        )
        if defined and value is not None and not isinstance(value, Mapping)
    ]

    if orbit_config_defined:
        source = "ORBIT_CONFIG"
    elif orbit_defined:
        source = "ORBIT"
    else:
        source = "defaults"

    effective = DEFAULTS.copy()
    effective.update(orbit_value)
    effective.update(orbit_config_value)
    shared_keys = set(orbit_value) & set(orbit_config_value)
    conflicting_keys = sorted(
        key
        for key in shared_keys
        if orbit_value.get(key) != orbit_config_value.get(key)
    )

    return {
        "source": source,
        "effective": effective,
        "both_defined": orbit_defined and orbit_config_defined,
        "conflicting_keys": conflicting_keys,
        "invalid_sources": invalid_sources,
    }


def get_config():
    """
    Get the Orbit configuration, merging defaults with user settings.

    Returns:
        dict: Complete configuration dictionary
    """
    return get_config_diagnostics()["effective"]


def is_enabled():
    """Check if Orbit is enabled."""
    return get_config().get("ENABLED", True)


def should_ignore_path(path):
    """
    Check if a path should be ignored by Orbit.

    Args:
        path: The request path to check

    Returns:
        bool: True if path should be ignored
    """
    config = get_config()
    ignore_paths = config.get("IGNORE_PATHS", [])

    for ignore_path in ignore_paths:
        if path.startswith(ignore_path):
            return True
    return False
