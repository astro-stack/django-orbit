# Publishing Django Orbit

This is the release checklist for publishing Django Orbit to GitHub, PyPI and the public MkDocs site.

## Release Order

1. Merge the release PR into `main`.
2. Pull the final `main` locally and confirm the version.
3. Run the full test suite.
4. Build the package from a clean `dist/`.
5. Verify the built wheel and sdist.
6. Publish to PyPI.
7. Create the GitHub release and tag.
8. Deploy the documentation site.
9. Verify PyPI, GitHub release, docs and a fresh install.

## Preflight

For release PRs and final publishing, run the local guard before pushing or uploading:

```bash
python scripts/verify_release.py
```

This checks release metadata, runs the test suite, builds docs in strict mode, rebuilds package artifacts and runs Twine checks.

If you only need the lightweight metadata check used by CI:

```bash
python scripts/verify_release.py --metadata-only
```

Confirm these files are aligned before publishing:

- `pyproject.toml` project version
- `orbit/__init__.py` `__version__`
- `CHANGELOG.md` release section
- `README.md` package landing page
- `docs/` and `mkdocs.yml` for user-visible changes

## Build

`python scripts/verify_release.py` already cleans old artifacts, builds fresh distributions and runs Twine checks. To run the build steps manually:

```bash
rm -rf dist/ build/ *.egg-info/
python -m build
python -m twine check dist/*
```

Expected files for version `X.Y.Z`:

- `dist/django_orbit-X.Y.Z.tar.gz`
- `dist/django_orbit-X.Y.Z-py3-none-any.whl`

## Pull Request Merge Guard

Release PRs must have these GitHub checks green before merge:

- `Release metadata`
- `Tests / Python 3.9 / Django 4.2 / core`
- `Tests / Python 3.10 / Django 4.2 / full+mcp`
- `Tests / Python 3.12 / Django 5.0 / full+mcp`
- `Documentation`
- `Package build`

In GitHub repository settings, configure branch protection for `main` to require those checks before merge and require branches to be up to date before merging.

## Publish to PyPI

```bash
python -m twine upload dist/django_orbit-X.Y.Z*
```

Use a PyPI project token when prompted:

```bash
python -m twine upload dist/django_orbit-X.Y.Z* -u __token__ -p pypi-...
```

## GitHub Release

Create a GitHub release from the same version and changelog section:

```bash
gh release create vX.Y.Z --target main --title "vX.Y.Z" --notes-file RELEASE_NOTES.md
```

The release notes should summarize:

- highlights for users;
- compatibility or migration notes;
- security/safety changes;
- test plan used for the release.

## Deploy Documentation

```bash
mkdocs build --strict
mkdocs gh-deploy
```

Documentation must be deployed from the same code that was released.

## Post-Publish Verification

Check the public package page:

```bash
python -m pip index versions django-orbit
```

Test a clean install in a temporary environment:

```bash
python -m venv .venv-release-check
.venv-release-check\Scripts\python -m pip install --upgrade pip
.venv-release-check\Scripts\python -m pip install "django-orbit[mcp]==X.Y.Z"
.venv-release-check\Scripts\python -c "import orbit; print(orbit.__version__)"
```

Verify these public URLs:

- PyPI: `https://pypi.org/project/django-orbit/`
- GitHub release: `https://github.com/astro-stack/django-orbit/releases/tag/vX.Y.Z`
- Docs: `https://astro-stack.github.io/django-orbit/`
- MCP docs: `https://astro-stack.github.io/django-orbit/mcp/`

## If Upload Fails

PyPI versions are immutable. If `X.Y.Z` was already uploaded, bump to the next patch version, update changelog/version files, rebuild and upload again.