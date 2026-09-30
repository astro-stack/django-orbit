# Quality Gates

Django Orbit uses a gradual quality policy so new contributions improve the
repository without making the existing codebase's historical formatting debt a
barrier to every pull request.

## Required Pull Request Checks

The `Quality / static checks` workflow runs on every pull request and checks:

- dependency consistency with `pip check`;
- Python bytecode compilation for `orbit/` and `tests/`;
- the full test suite with a coverage report;
- known vulnerabilities in installed dependencies with `pip-audit`;
- Black, isort and Flake8 on Python files changed by the pull request.

The existing matrix in `CI` remains the compatibility gate for supported Python
and Django versions. The quality workflow complements it; it does not replace
the compatibility matrix.

## Why Checks Apply to Changed Files

The project contains older modules that predate the current formatting policy.
Running format and lint checks against the entire tree today would fail on
unrelated legacy code and would make routine contributions harder to review.

New or modified Python files must pass the checks immediately. A later cleanup
can expand the scope to the full tree in a focused pull request.

## Coverage Policy

Coverage is reported on every pull request but does not yet enforce a minimum
percentage. The baseline should be measured across the supported Django matrix
before introducing a threshold. The threshold will be raised in stages and
must not hide tests that are skipped for optional MCP dependencies.

## Local Verification

Install the development dependencies and run the same core checks locally:

```bash
python -m pip install -e ".[dev]" pip-audit
python -m pip check
python -m compileall -q orbit tests
python -m pytest --cov=orbit --cov-report=term-missing -q
python -m pip_audit
```

For a focused change, run formatting and lint checks on the files you touched:

```bash
python -m black --check orbit/path/to_file.py tests/test_file.py
python -m isort --check-only orbit/path/to_file.py tests/test_file.py
python -m flake8 --max-line-length=88 --extend-ignore=E203,W503 orbit/path/to_file.py tests/test_file.py
```

Do not add credentials, request payloads, generated artifacts or local
configuration files to a pull request.
