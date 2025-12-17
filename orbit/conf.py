"""
Django Orbit Configuration

Provides default configuration and allows user overrides via Django settings.
"""

from django.conf import settings

# Default configuration
DEFAULTS = {
    "ENABLED": True,
    "SLOW_QUERY_THRESHOLD_MS": 500,
    "IGNORE_PATHS": ["/orbit/", "/static/", "/admin/jsi18n/", "/favicon.ico"],
    "HIDE_REQUEST_HEADERS": ["Authorization", "Cookie", "X-CSRFToken"],
    "HIDE_REQUEST_BODY_KEYS": ["password", "token", "secret", "api_key"],
    "MAX_BODY_SIZE": 65536,  # 64KB
    "STORAGE_LIMIT": 1000,  # Max entries to keep
    # Original watchers
    "RECORD_REQUESTS": True,
    "RECORD_QUERIES": True,
    "RECORD_LOGS": True,
    "RECORD_EXCEPTIONS": True,
    # Phase 1 watchers
    "RECORD_COMMANDS": True,
    "RECORD_CACHE": True,
    "RECORD_MODELS": True,
    "RECORD_HTTP_CLIENT": True,
    "RECORD_DUMPS": True,
    # Command watcher settings
    "IGNORE_COMMANDS": ["runserver", "shell", "dbshell", "showmigrations"],
    "MAX_COMMAND_OUTPUT": 5000,
}


def get_config():
    """
    Get the Orbit configuration, merging defaults with user settings.
    
    Returns:
        dict: Complete configuration dictionary
    """
    user_config = getattr(settings, "ORBIT_CONFIG", {})
    config = DEFAULTS.copy()
    config.update(user_config)
    return config


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
