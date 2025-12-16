# Publishing Django Orbit

## Prerequisites

1. Create accounts:
   - [PyPI](https://pypi.org/account/register/) (production)
   - [TestPyPI](https://test.pypi.org/account/register/) (testing)

2. Install build tools:
   ```bash
   pip install build twine
   ```

## Build the Package

```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info/

# Build
python -m build
```

This creates:
- `dist/django_orbit-0.1.0.tar.gz` (source)
- `dist/django_orbit-0.1.0-py3-none-any.whl` (wheel)

## Test on TestPyPI First

```bash
# Upload to TestPyPI
twine upload --repository testpypi dist/*

# Test installation
pip install --index-url https://test.pypi.org/simple/ django-orbit
```

## Publish to PyPI

```bash
# Upload to production PyPI
twine upload dist/*
```

You'll be prompted for your PyPI username and password (or API token).

## Using API Tokens (Recommended)

1. Go to https://pypi.org/manage/account/token/
2. Create a token for this project
3. Use with twine:
   ```bash
   twine upload dist/* -u __token__ -p pypi-YOUR_TOKEN_HERE
   ```

Or create `~/.pypirc`:
```ini
[pypi]
username = __token__
password = pypi-YOUR_TOKEN_HERE
```

## After Publishing

Test the installation:
```bash
pip install django-orbit
```

## Version Updates

1. Update version in `orbit/__init__.py`
2. Update CHANGELOG.md
3. Rebuild and upload:
   ```bash
   python -m build
   twine upload dist/*
   ```
