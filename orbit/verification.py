"""Shared validation for explicit, opt-in verification correlation."""

from __future__ import annotations

import re
from typing import Any

VERIFICATION_HEADER = "X-Orbit-Verification"
_VERIFICATION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def is_valid_verification_id(value: Any) -> bool:
    """Return whether a value is a bounded opaque verification identifier."""
    return isinstance(value, str) and _VERIFICATION_ID_RE.fullmatch(value) is not None
