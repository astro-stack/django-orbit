# Scheduled Maintenance

Django Orbit runs a weekday health check from GitHub Actions. It is designed
to detect drift in the published project without changing the repository.

## What It Checks

The scheduled workflow runs:

- the full test suite on Python 3.12;
- dependency vulnerability auditing with `pip-audit`;
- release metadata validation, package build and `twine check`;
- a strict MkDocs build.

The supported Python and Django matrix remains in the pull request CI. The
scheduled check is an additional early warning between contributions.

## Failure Handling

Failures appear in the workflow summary. The workflow opens one shared issue
named `Scheduled maintenance failure`, or adds a comment to the existing open
issue. It never commits, pushes, publishes packages, changes dependencies or
merges a pull request.

After fixing the cause, close the issue and run the workflow manually from the
Actions tab to verify the repair.

## Agent-Assisted Maintenance

An external coordinator such as Paperclip can watch the workflow and issue
without receiving repository credentials. Its safe responsibilities are:

1. read the failure summary and linked run;
2. classify the failure as dependency, test, release or documentation drift;
3. draft a small pull request with tests and documentation;
4. wait for a human review and the required GitHub checks.

It must not auto-merge, publish to PyPI, rotate credentials or change branch
protection. Any future agent integration should use a narrowly scoped token and
the same pull-request boundary.

## Manual Run

From GitHub, open **Actions**, select **Scheduled maintenance**, choose **Run
workflow**, and run it against `main`. The equivalent command is:

```bash
gh workflow run maintenance.yml --repo astro-stack/django-orbit --ref main
```
