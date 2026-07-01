"""Release and PR preflight checks for Django Orbit.

This script is intentionally dependency-light. It gives maintainers one local
command that mirrors the important free GitHub Actions checks before pushing or
publishing a release.
"""

from __future__ import annotations

import argparse
import glob
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def project_version() -> str:
    text = read_text("pyproject.toml")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise SystemExit("Could not find project.version in pyproject.toml")
    return match.group(1)


def package_version() -> str:
    text = read_text("orbit/__init__.py")
    match = re.search(r'^__version__\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise SystemExit("Could not find orbit.__version__")
    return match.group(1)


def check_release_metadata() -> str:
    version = project_version()
    package = package_version()
    errors: list[str] = []

    if package != version:
        errors.append(
            f"Version mismatch: pyproject={version}, orbit.__version__={package}"
        )

    changelog = read_text("CHANGELOG.md")
    if f"## [{version}]" not in changelog:
        errors.append(f"CHANGELOG.md is missing a ## [{version}] section")

    readme = read_text("README.md")
    if f"v{version}" not in readme:
        errors.append(f"README.md does not mention v{version}")

    docs_index = read_text("docs/index.md")
    if f"v{version}" not in docs_index:
        errors.append(f"docs/index.md does not mention v{version}")

    pyproject = read_text("pyproject.toml")
    if 'readme = "README.md"' not in pyproject:
        errors.append(
            'pyproject.toml must keep readme = "README.md" so PyPI matches GitHub'
        )

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)

    print(f"Release metadata OK for v{version}")
    return version


def run(command: list[str]) -> None:
    print("+ " + " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)


def remove_path(path: Path) -> None:
    if path.exists():
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()


def clean_build_artifacts() -> None:
    remove_path(ROOT / "dist")
    remove_path(ROOT / "build")
    for path in ROOT.glob("*.egg-info"):
        remove_path(path)


def verify_artifacts(version: str) -> None:
    expected = {
        f"django_orbit-{version}.tar.gz",
        f"django_orbit-{version}-py3-none-any.whl",
    }
    found = {Path(path).name for path in glob.glob(str(ROOT / "dist" / "*"))}
    missing = expected - found
    if missing:
        raise SystemExit(
            f"Missing expected build artifacts: {', '.join(sorted(missing))}"
        )


def full_preflight() -> None:
    version = check_release_metadata()
    run([sys.executable, "-m", "pytest", "--tb=short", "-q"])
    run([sys.executable, "-m", "mkdocs", "build", "--strict"])
    clean_build_artifacts()
    run([sys.executable, "-m", "build"])
    verify_artifacts(version)
    artifacts = sorted(glob.glob(str(ROOT / "dist" / "*")))
    run([sys.executable, "-m", "twine", "check", *artifacts])
    print("Release preflight OK")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify Django Orbit release readiness"
    )
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="Only check version/changelog/README/docs metadata alignment",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.metadata_only:
        check_release_metadata()
    else:
        full_preflight()


if __name__ == "__main__":
    main()
