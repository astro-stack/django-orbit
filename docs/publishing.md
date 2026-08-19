# Publishing Django Orbit

This is the release checklist for publishing Django Orbit to GitHub, PyPI and the public MkDocs site.

## Release Order

1. Merge the release PR into `main`.
2. Pull the final `main` locally and confirm the version.
3. Run the full test suite and release preflight.
4. Create and push an annotated tag matching the package version:

   ```bash
   git tag -a vX.Y.Z -m "Release vX.Y.Z"
   git push origin vX.Y.Z
   ```

5. GitHub Actions verifies the tag is annotated, points at `main`, and matches
   every version surface.
6. The same workflow publishes to PyPI before creating the GitHub release. The
   `pypi` environment approval and PyPI trusted publishing (OIDC) gate the
   upload.
7. If a release needs a safe retry, run `Publish to PyPI` manually with the
   exact annotated tag; it repeats the tag, `main` ancestry and metadata checks.
8. The documentation workflow deploys the merged `main` documentation.
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

The `Create GitHub Release` workflow publishes the package first, then creates
the release automatically after the tag checks and package preflight pass.
GitHub generates the initial notes; the matching `CHANGELOG.md` section
remains the source of truth for the release contents.

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
