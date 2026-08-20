## Summary

<!-- What changed and why? -->
<!-- Keep this as real multiline Markdown. If using gh, pass a file with
     --body-file; do not encode line breaks as literal \n characters. -->

## Release / PR Safeguards

- [ ] Version files are aligned when this is a release PR (`pyproject.toml` and `orbit/__init__.py`).
- [ ] `CHANGELOG.md` has the release/user-visible entry.
- [ ] README/PyPI copy is updated for user-visible changes.
- [ ] MkDocs docs are updated for user-visible changes.
- [ ] The version bump follows the policy in [`docs/publishing.md`](../blob/main/docs/publishing.md): patch for fixes, minor for new capability lines, and `v1.0.0` only for an explicit stable-API commitment.
- [ ] If this PR changes the project version, I will complete the tag/PyPI/GitHub release follow-up after merge (the guard will open an issue if it is missing).
- [ ] Local preflight was run before push when preparing a release:

```bash
python scripts/verify_release.py
```

## Test Plan

- [ ] `python -m pytest --tb=short -q`
- [ ] `python -m mkdocs build --strict`
- [ ] `python -m build`
- [ ] `python -m twine check dist/*`

## UX / Contributor Experience

- [ ] User-facing copy is clear for both Django experts and AI-assisted developers.
- [ ] Dashboard/UI changes include a screenshot, short recording or written visual verification.
- [ ] MCP/agentic tool changes include a sample response and the recommended next tool/action.
- [ ] New contributor impact is documented when setup, tests, docs, or release workflow changes.
- [ ] Errors, empty states and safety warnings tell the user what to do next.

## Merge Requirements

Required GitHub checks should be green before merge:

- `Release metadata`
- `Tests / Python 3.9 / Django 4.2 / core`
- `Tests / Python 3.10 / Django 4.2 / full+mcp`
- `Tests / Python 3.12 / Django 5.0 / full+mcp`
- `Documentation`
- `Package build`
