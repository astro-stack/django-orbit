"""Quickstart installer for Django Orbit projects."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence

ORBIT_APP = '"orbit"'
ORBIT_MIDDLEWARE = '"orbit.middleware.OrbitMiddleware"'
ORBIT_URL_INCLUDE = 'include("orbit.urls")'


@dataclass(frozen=True)
class QuickstartOptions:
    """Options used to generate or apply an Orbit install plan."""

    settings_path: Optional[Path] = None
    urls_path: Optional[Path] = None
    url_prefix: str = "orbit/"
    with_mcp: bool = False
    write: bool = False


def normalize_url_prefix(url_prefix: str) -> str:
    """Return a Django path prefix without a leading slash and with a slash suffix."""
    normalized = url_prefix.strip()
    if normalized.startswith("/"):
        normalized = normalized[1:]
    if not normalized:
        raise ValueError("url prefix cannot be empty")
    if not normalized.endswith("/"):
        normalized = f"{normalized}/"
    return normalized


def build_install_plan(options: QuickstartOptions) -> str:
    """Build a human-readable install plan for manual or automated setup."""
    url_prefix = normalize_url_prefix(options.url_prefix)
    package = "django-orbit[mcp]" if options.with_mcp else "django-orbit"
    assistant_note = " with MCP tools" if options.with_mcp else ""

    return "\n".join(
        [
            "Django Orbit quickstart plan (dry-run by default)",
            "",
            f"1. Install{assistant_note}:",
            f"   pip install {package}",
            "",
            "2. Apply project wiring:",
            "   django-orbit-quickstart --settings path/to/settings.py --urls path/to/urls.py --write",
            "",
            "3. Expected settings.py additions:",
            '   INSTALLED_APPS += ["orbit"]',
            '   MIDDLEWARE starts with "orbit.middleware.OrbitMiddleware"',
            "",
            "4. Expected urls.py addition:",
            f'   path("{url_prefix}", include("orbit.urls"))',
            "",
            "5. Finish setup:",
            "   python manage.py migrate orbit",
            "   python manage.py runserver",
            f"   open http://localhost:8000/{url_prefix}",
        ]
    )


def patch_settings_text(text: str) -> tuple[str, list[str]]:
    """Add Orbit app and middleware to settings.py text if missing."""
    changes: list[str] = []
    updated = text

    if "'orbit'" not in updated and '"orbit"' not in updated:
        updated, changed = _insert_after_list_start(
            updated,
            "INSTALLED_APPS",
            f"    {ORBIT_APP},",
        )
        if changed:
            changes.append("added orbit to INSTALLED_APPS")

    if "orbit.middleware.OrbitMiddleware" not in updated:
        updated, changed = _insert_after_list_start(
            updated,
            "MIDDLEWARE",
            f"    {ORBIT_MIDDLEWARE},",
        )
        if changed:
            changes.append("added OrbitMiddleware to MIDDLEWARE")

    return updated, changes


def patch_urls_text(text: str, url_prefix: str = "orbit/") -> tuple[str, list[str]]:
    """Add Orbit URL routing to urls.py text if missing."""
    prefix = normalize_url_prefix(url_prefix)
    changes: list[str] = []
    updated = text

    if "include(" not in updated.split("urlpatterns", 1)[0]:
        updated, changed = _ensure_django_include_import(updated)
        if changed:
            changes.append("added include import to urls.py")

    if (
        'include("orbit.urls")' not in updated
        and "include('orbit.urls')" not in updated
    ):
        updated, changed = _insert_after_list_start(
            updated,
            "urlpatterns",
            f'    path("{prefix}", {ORBIT_URL_INCLUDE}),',
        )
        if changed:
            changes.append(f"mounted Orbit URLs at {prefix}")

    return updated, changes


def run_quickstart(argv: Optional[Sequence[str]] = None) -> int:
    """CLI implementation for django-orbit-quickstart."""
    parser = argparse.ArgumentParser(
        prog="django-orbit-quickstart",
        description="Print or apply the minimal Django Orbit project wiring.",
    )
    parser.add_argument("--settings", type=Path, help="Path to Django settings.py")
    parser.add_argument("--urls", type=Path, help="Path to Django urls.py")
    parser.add_argument(
        "--url-prefix",
        default="orbit/",
        help="URL prefix for the Orbit dashboard, default: orbit/",
    )
    parser.add_argument(
        "--with-mcp",
        action="store_true",
        help="Show install command with the MCP extra: django-orbit[mcp]",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write changes to settings.py and urls.py. Without this flag, runs as dry-run.",
    )
    args = parser.parse_args(argv)

    try:
        options = QuickstartOptions(
            settings_path=args.settings,
            urls_path=args.urls,
            url_prefix=normalize_url_prefix(args.url_prefix),
            with_mcp=args.with_mcp,
            write=args.write,
        )
    except ValueError as exc:
        parser.error(str(exc))

    if not options.settings_path and not options.urls_path:
        print(build_install_plan(options))
        return 0

    planned_changes: list[str] = []

    if options.settings_path:
        settings_text = _read_required_file(options.settings_path)
        patched_settings, settings_changes = patch_settings_text(settings_text)
        planned_changes.extend(settings_changes)
        if options.write and patched_settings != settings_text:
            options.settings_path.write_text(patched_settings, encoding="utf-8")

    if options.urls_path:
        urls_text = _read_required_file(options.urls_path)
        patched_urls, urls_changes = patch_urls_text(urls_text, options.url_prefix)
        planned_changes.extend(urls_changes)
        if options.write and patched_urls != urls_text:
            options.urls_path.write_text(patched_urls, encoding="utf-8")

    mode = "Applied" if options.write else "Dry run"
    print(f"{mode}: Django Orbit quickstart")
    if planned_changes:
        for change in planned_changes:
            print(f"- {change}")
    else:
        print("- no changes needed")
    print("Next: python manage.py migrate orbit")
    print(f"Open: http://localhost:8000/{options.url_prefix}")
    return 0


def main() -> int:
    """Console entrypoint."""
    return run_quickstart()


def _read_required_file(path: Path) -> str:
    if not path.exists():
        raise SystemExit(f"File not found: {path}")
    return path.read_text(encoding="utf-8")


def _insert_after_list_start(
    text: str, variable_name: str, line_to_add: str
) -> tuple[str, bool]:
    lines = text.splitlines(keepends=True)
    marker = f"{variable_name} = ["

    for index, line in enumerate(lines):
        if line.strip() == marker:
            newline = "\r\n" if line.endswith("\r\n") else "\n"
            lines.insert(index + 1, f"{line_to_add}{newline}")
            return "".join(lines), True
        if line.strip() == f"{variable_name} = []":
            newline = "\r\n" if line.endswith("\r\n") else "\n"
            lines[index] = (
                f"{variable_name} = [{newline}{line_to_add}{newline}]{newline}"
            )
            return "".join(lines), True

    return text, False


def _ensure_django_include_import(text: str) -> tuple[str, bool]:
    lines = text.splitlines(keepends=True)

    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("from django.urls import "):
            continue

        imports = [
            part.strip()
            for part in stripped.removeprefix("from django.urls import ").split(",")
        ]
        if "include" in imports:
            return text, False
        imports.append("include")
        ordered = _order_django_url_imports(imports)
        newline = "\r\n" if line.endswith("\r\n") else "\n"
        lines[index] = f"from django.urls import {', '.join(ordered)}{newline}"
        return "".join(lines), True

    return f"from django.urls import include, path\n{text}", True


def _order_django_url_imports(imports: Iterable[str]) -> list[str]:
    unique = {item for item in imports if item}
    preferred = ["include", "path", "re_path"]
    ordered = [item for item in preferred if item in unique]
    ordered.extend(sorted(unique.difference(preferred)))
    return ordered


if __name__ == "__main__":
    raise SystemExit(main())
