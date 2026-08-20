"""Detect version changes that still need a GitHub/PyPI release follow-up."""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION_PATTERN = re.compile(
    r'^version\s*=\s*"([^"\r\n]+)"', re.MULTILINE
)
SAFE_VERSION_PATTERN = re.compile(r"^[0-9][0-9A-Za-z.+!-]*$")
SAFE_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def extract_version(pyproject: str) -> str:
    """Return the safe project version from a pyproject.toml fragment."""

    match = VERSION_PATTERN.search(pyproject)
    if not match:
        raise ValueError("Could not find a project version")

    version = match.group(1)
    if not SAFE_VERSION_PATTERN.fullmatch(version):
        raise ValueError("Project version is not a valid release version")
    return version


def changed_version(base_pyproject: str, merge_pyproject: str) -> str | None:
    """Return the merged version when the project version changed."""

    base_version = extract_version(base_pyproject)
    merge_version = extract_version(merge_pyproject)
    return merge_version if merge_version != base_version else None


def git_file(commit: str, path: str) -> str:
    """Read one tracked file from a full commit SHA without invoking a shell."""

    if not SAFE_SHA_PATTERN.fullmatch(commit):
        raise ValueError("Commit must be a full lowercase SHA-1")
    result = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Report a version changed between two trusted commits"
    )
    parser.add_argument("--base-ref", required=True, help="Full base commit SHA")
    parser.add_argument("--merge-ref", required=True, help="Full merged commit SHA")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    version = changed_version(
        git_file(args.base_ref, "pyproject.toml"),
        git_file(args.merge_ref, "pyproject.toml"),
    )
    if version is not None:
        print(version)


if __name__ == "__main__":
    main()
