"""Neutral registration of optional local dashboard navigation links."""

from __future__ import annotations

_EXTENSIONS: dict[str, dict[str, str]] = {}


def register_dashboard_extension(key: str, label: str, url: str) -> None:
    """Register an explicitly mounted, same-site dashboard link."""
    if not isinstance(key, str) or not key.replace("_", "").isalnum():
        raise ValueError("Extension key must be alphanumeric.")
    if not isinstance(label, str) or not label.strip() or len(label) > 80:
        raise ValueError("Extension label is invalid.")
    if (
        not isinstance(url, str)
        or not url.startswith("/")
        or "?" in url
        or "#" in url
        or "//" in url
    ):
        raise ValueError(
            "Extension URL must be a local path without query or fragment."
        )
    _EXTENSIONS[key] = {"key": key, "label": label, "url": url}


def list_dashboard_extensions() -> tuple[dict[str, str], ...]:
    return tuple(_EXTENSIONS[key].copy() for key in sorted(_EXTENSIONS))


def clear_dashboard_extensions() -> None:
    _EXTENSIONS.clear()
