# Contributing

!!! info "We Welcome Contributions!"
    Django Orbit is open source and we love contributions from the community.

## How to Contribute

1. **Fork** the repository on GitHub
2. **Clone** your fork locally
3. **Create a branch** for your feature or fix
4. **Make your changes** with tests
5. **Push** to your fork
6. **Open a Pull Request**

## Development Setup

```bash
git clone https://github.com/astro-stack/django-orbit.git
cd django-orbit
python -m venv venv
source venv/bin/activate  # or .\venv\Scripts\activate on Windows
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest
```

Pull requests also run GitHub Actions CI on supported Python/Django combinations, release metadata, documentation builds, package builds and Twine metadata checks.

## Reproduce GitHub Checks

Run the matching command locally before updating a pull request. The commands
below intentionally mirror the free checks in GitHub Actions; use a clean
virtual environment when switching Django versions.

| GitHub check | Local command |
| --- | --- |
| `Tests / Python 3.9 / Django 4.2 / core` | `python -m pip install -e . "Django>=4.2,<4.3" pytest pytest-django requests` then `python -m pytest --tb=short -q --ignore=tests/test_mcp.py -k "not mcp"` |
| `Tests / Python 3.10 / Django 4.2 / full+mcp` | `python -m pip install -e ".[dev]" "Django>=4.2,<4.3"` then `python -m pytest --tb=short -q` |
| `Tests / Python 3.12 / Django 5.0 / full+mcp` | `python -m pip install -e ".[dev]" "Django>=5.0,<5.1"` then `python -m pytest --tb=short -q` |
| `Release metadata` | `python scripts/verify_release.py --metadata-only` |
| `Documentation` | `python -m mkdocs build --strict` |
| `Package build` | `python -m build && python -m twine check dist/*` |

When a matrix check fails, reproduce the exact row first. Fix the code or
compatibility issue, then run the normal full suite in the project's supported
development environment before pushing again. Do not change the matrix merely
to hide a supported-version failure.

Before pushing a release PR, run the same local preflight used by maintainers:

```bash
python scripts/verify_release.py
```

For a quick metadata-only check:

```bash
python scripts/verify_release.py --metadata-only
```

Maintainers can also run **Actions → Release Check → Run workflow** for any
branch. It runs the same full preflight without publishing a package, creating
a release, or using publishing credentials. See [Publishing](publishing.md)
for the final release sequence.

## Code Style

We use Black and isort for code formatting:

```bash
black orbit/
isort orbit/
```

## Questions?

- Open an [issue on GitHub](https://github.com/astro-stack/django-orbit/issues)
- Start a [discussion](https://github.com/astro-stack/django-orbit/discussions)

---

*Thank you for contributing! 🚀*
