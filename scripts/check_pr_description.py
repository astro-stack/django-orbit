"""Validate pull request descriptions used by the repository workflow."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def validate_description(body: str) -> list[str]:
    """Return actionable errors for malformed or empty pull request bodies."""
    errors: list[str] = []
    if not body.strip():
        errors.append("The pull request description must not be empty.")
    if r"\n" in body:
        errors.append(
            "The description contains literal \\n characters; use real Markdown "
            "line breaks and gh pr create/edit --body-file."
        )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, required=True)
    args = parser.parse_args()

    errors = validate_description(args.file.read_text(encoding="utf-8"))
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("Pull request description format OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
