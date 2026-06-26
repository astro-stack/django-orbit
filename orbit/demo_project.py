"""Create a small local Django project for trying Django Orbit."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DemoProjectResult:
    """Result of creating a demo project."""

    target: Path
    files: list[Path]
    with_mcp: bool = False


def create_demo_project(
    target: Path, with_mcp: bool = False, force: bool = False
) -> DemoProjectResult:
    """Create a minimal Django project that exercises Orbit web and MCP flows."""
    target = target.resolve()
    if target.exists() and any(target.iterdir()) and not force:
        raise FileExistsError(f"Target is not empty: {target}")

    package_dir = target / "orbit_demo"
    package_dir.mkdir(parents=True, exist_ok=True)

    files = {
        target / "manage.py": _manage_py(),
        package_dir / "__init__.py": "",
        package_dir / "settings.py": _settings_py(),
        package_dir / "urls.py": _urls_py(),
        package_dir / "views.py": _views_py(),
        target / "README.md": _readme(with_mcp),
    }

    written: list[Path] = []
    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        written.append(path)

    return DemoProjectResult(target=target, files=written, with_mcp=with_mcp)


def _manage_py() -> str:
    return """#!/usr/bin/env python
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "orbit_demo.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
"""


def _settings_py() -> str:
    return """from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = "django-orbit-demo-not-for-production"
DEBUG = True
ALLOWED_HOSTS = ["*"]
ROOT_URLCONF = "orbit_demo.urls"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
STATIC_URL = "static/"
USE_TZ = True
TIME_ZONE = "UTC"

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "orbit",
]

MIDDLEWARE = [
    "orbit.middleware.OrbitMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
        "orbit": {"class": "orbit.handlers.OrbitLogHandler", "level": "DEBUG"},
    },
    "root": {"handlers": ["console", "orbit"], "level": "INFO"},
    "loggers": {
        "orbit_demo": {"handlers": ["console", "orbit"], "level": "DEBUG", "propagate": False},
    },
}

ORBIT_CONFIG = {
    "ENABLED": True,
    "AUTH_CHECK": lambda request: True,
    "SLOW_QUERY_THRESHOLD_MS": 100,
}
"""


def _urls_py() -> str:
    return """from django.urls import include, path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("books/", views.books, name="books"),
    path("slow/", views.slow, name="slow"),
    path("error/", views.error, name="error"),
    path("duplicate-queries/", views.duplicate_queries, name="duplicate_queries"),
    path("orbit/", include("orbit.urls")),
]
"""


def _views_py() -> str:
    return '''import logging
import time

from django.db import connection
from django.http import HttpResponse, JsonResponse

logger = logging.getLogger(__name__)


def home(request):
    logger.info("Opened Django Orbit demo home")
    return HttpResponse(
        """
        <!doctype html>
        <html>
        <head><title>Django Orbit Demo</title></head>
        <body style="font-family: system-ui; max-width: 760px; margin: 48px auto; line-height: 1.5;">
            <h1>Django Orbit Demo</h1>
            <p>Generate events, then open <a href='/orbit/'>/orbit/</a>.</p>
            <ul>
                <li><a href='/books/'>/books/</a> - SQL and request telemetry</li>
                <li><a href='/slow/'>/slow/</a> - slow request</li>
                <li><a href='/error/'>/error/</a> - captured exception</li>
                <li><a href='/duplicate-queries/'>/duplicate-queries/</a> - duplicate query signal</li>
            </ul>
        </body>
        </html>
        """
    )


def books(request):
    logger.info("Listing demo books")
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 AS id, 'Django Orbit Field Guide' AS title")
        rows = cursor.fetchall()
    return JsonResponse({"books": [{"id": row[0], "title": row[1]} for row in rows]})


def slow(request):
    logger.warning("Starting demo slow endpoint")
    time.sleep(0.25)
    return JsonResponse({"ok": True, "duration_ms": 250})


def error(request):
    logger.error("Raising demo exception")
    raise ValueError("Demo exception for Django Orbit")


def duplicate_queries(request):
    logger.info("Generating duplicate demo queries")
    with connection.cursor() as cursor:
        for _ in range(5):
            cursor.execute("SELECT 1")
            cursor.fetchone()
    return JsonResponse({"ok": True, "duplicate_queries": 5})
'''


def _readme(with_mcp: bool) -> str:
    mcp = (
        """
## MCP

Run the local MCP server from this directory:

```bash
python manage.py orbit_mcp
```

Connect Claude, Codex, Cursor or another MCP client to that command with this directory as `cwd`.
"""
        if with_mcp
        else ""
    )

    return f"""# Django Orbit Demo Project

This project was generated by `orbit demo`.

Prerequisite: run these commands in the same Python environment where `django-orbit` is installed.

## Web Demo

```bash
python manage.py migrate
python manage.py runserver
```

Open these URLs:

- http://localhost:8000/
- http://localhost:8000/orbit/
- http://localhost:8000/books/
- http://localhost:8000/slow/
- http://localhost:8000/error/
- http://localhost:8000/duplicate-queries/
{mcp}
"""
