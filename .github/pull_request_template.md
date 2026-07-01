## Summary

<!-- What changed and why? -->

## Release / PR Safeguards

- [ ] Version files are aligned when this is a release PR (`pyproject.toml` and `orbit/__init__.py`).
- [ ] `CHANGELOG.md` has the release/user-visible entry.
- [ ] README/PyPI copy is updated for user-visible changes.
- [ ] MkDocs docs are updated for user-visible changes.
- [ ] Local preflight was run before push when preparing a release:

```bash
python scripts/verify_release.py
```

## Test Plan

- [ ] `python -m pytest --tb=short -q`
- [ ] `python -m mkdocs build --strict`
- [ ] `python -m build`
- [ ] `python -m twine check dist/*`

## Merge Requirements

Required GitHub checks should be green before merge:

- `Release metadata`
- `Tests / Python 3.9 / Django 4.2 / core`
- `Tests / Python 3.10 / Django 4.2 / full+mcp`
- `Tests / Python 3.12 / Django 5.0 / full+mcp`
- `Documentation`
- `Package build`
