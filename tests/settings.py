from example_project.settings import *

# Overwrite database to use in-memory SQLite for speed
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Disable logging to console during tests to keep output clean
LOGGING = {}

# Override Orbit config for tests
ORBIT_CONFIG = {
    "ENABLED": True,
    "AUTH_CHECK": None,  # Disable auth for tests
    "RECORD_REQUESTS": True,
    "RECORD_QUERIES": True,
    "RECORD_LOGS": True,
    "RECORD_EXCEPTIONS": True,
    "RECORD_COMMANDS": True,
    "RECORD_CACHE": True,
    "RECORD_MODELS": True,
    "RECORD_HTTP_CLIENT": True,
    "RECORD_DUMPS": True,
    "RECORD_MAIL": True,
    "RECORD_SIGNALS": False,  # Disable signals in tests to avoid noise
}
