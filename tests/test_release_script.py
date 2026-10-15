"""Tests for the dependency-light release preflight script."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from orbit import __version__

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify_release.py"
pytestmark = pytest.mark.django_db


def run_metadata_check(tag: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--metadata-only", "--tag", tag],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_release_metadata_accepts_the_project_tag() -> None:
    result = run_metadata_check(f"v{__version__}")

    assert result.returncode == 0
    assert f"Release metadata OK for v{__version__}" in result.stdout


def test_release_metadata_rejects_a_tag_for_another_version() -> None:
    result = run_metadata_check("v999.999.999")

    assert result.returncode != 0
    assert f"does not match project version {__version__}" in result.stderr
