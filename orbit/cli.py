"""Django Orbit command-line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

from .demo_project import create_demo_project
from .quickstart import run_quickstart


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the short `orbit` CLI."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in {"quick", "quickstart"}:
        return run_quickstart(argv[1:], prog=f"orbit {argv[0]}")

    parser = argparse.ArgumentParser(
        prog="orbit",
        description="Django Orbit project helpers.",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser(
        "quick",
        help="Print, check or apply Django Orbit project wiring.",
    )
    subparsers.add_parser(
        "quickstart",
        help="Print, check or apply Django Orbit project wiring.",
    )

    demo = subparsers.add_parser(
        "demo",
        help="Create a local demo project for web and MCP testing.",
    )
    demo.add_argument(
        "--target",
        type=Path,
        default=Path("django-orbit-demo"),
        help="Directory to create, default: django-orbit-demo",
    )
    demo.add_argument(
        "--with-mcp",
        action="store_true",
        help="Include MCP run instructions in the generated README.",
    )
    demo.add_argument(
        "--force",
        action="store_true",
        help="Allow writing into a non-empty target directory.",
    )

    args = parser.parse_args(argv)

    if args.command in {"quick", "quickstart"}:
        return run_quickstart([], prog=f"orbit {args.command}")

    if args.command == "demo":
        result = create_demo_project(
            args.target, with_mcp=args.with_mcp, force=args.force
        )
        print(f"Created Django Orbit demo project: {result.target}")
        print("Next:")
        print(f"  cd {result.target}")
        print("  python manage.py migrate")
        print("  python manage.py runserver")
        print("  open http://localhost:8000/orbit/")
        if args.with_mcp:
            print("MCP:")
            print("  python manage.py orbit_mcp")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
