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
