# Publishing Django Orbit

This is the release checklist for publishing Django Orbit to GitHub, PyPI and the public MkDocs site.

## Versioning Policy

Use [Semantic Versioning](https://semver.org/spec/v2.0.0.html) with an
explicit pre-1.0 project policy:

- `v0.12.PATCH` is for fixes, security corrections, dependency updates and
  release-process repairs that should not add a new product capability. For
  example, the next hotfix after `v0.12.1` is `v0.12.2`.
- `v0.MINOR.0` is for a new capability line or substantial user-visible
  behavior. The current agentic/evidence work is therefore the pending
  `v0.13.0` release, not a patch on `v0.12`.
- `v1.0.0` is reserved for the moment we explicitly commit to a stable public
  API, compatibility guarantees and a migration policy. A release being
  large does not automatically make it `v1.0.0`.

Do not skip a viable pending feature line. Only use `v0.14.0` if the
`v0.13.0` line is explicitly abandoned or re-scoped before release. Every
version change still follows the release PR, full preflight, merge, annotated
tag, PyPI publication, GitHub release and post-publish verification sequence
below.

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

## Post-Merge Release Guard

Every push to `main` and every merged pull request targeting `main` is checked
by the `Release follow-up guard` workflow. If `pyproject.toml` changes to a
new version and the matching GitHub release is missing, the workflow opens one
deduplicated issue with the exact tag and preflight commands.

The guard intentionally does not tag, upload to PyPI or create a release by
itself. Those actions remain behind the annotated-tag, metadata, build and
PyPI trusted-publishing checks in `Create GitHub Release`. Close the follow-up
issue only after the public package, release and docs have been verified.

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
