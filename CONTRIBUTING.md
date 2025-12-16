# Contributing to Django Orbit

Thank you for your interest in contributing to Django Orbit! This document provides guidelines and information for contributors.

## Development Setup

### Prerequisites

- Python 3.9 or higher
- Django 4.0 or higher
- Git

### Setting Up Your Development Environment

1. **Fork and clone the repository**

```bash
git clone https://github.com/astro-stack/django-orbit.git
cd django-orbit
```

2. **Create a virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install development dependencies**

```bash
pip install -e ".[dev]"
```

4. **Run the test suite**

```bash
pytest
```

## Code Style

We use several tools to maintain code quality:

- **Black** for code formatting
- **isort** for import sorting
- **Flake8** for linting
- **mypy** for type checking

Run all formatters and linters:

```bash
black orbit tests
isort orbit tests
flake8 orbit tests
mypy orbit
```

## Making Changes

### Branch Naming

Use descriptive branch names:

- `feature/add-redis-storage`
- `fix/sql-recorder-crash`
- `docs/update-installation-guide`

### Commit Messages

Follow the [Conventional Commits](https://www.conventionalcommits.org/) format:

```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### Pull Request Process

1. Create a new branch from `main`
2. Make your changes
3. Add or update tests as needed
4. Ensure all tests pass
5. Update documentation if necessary
6. Open a pull request with a clear description

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=orbit --cov-report=html

# Run specific test file
pytest tests/test_middleware.py

# Run with verbose output
pytest -v
```

### Writing Tests

- Place tests in the `tests/` directory
- Use pytest fixtures for common setup
- Test both success and error cases
- Mock external dependencies

Example test:

```python
import pytest
from django.test import RequestFactory
from orbit.middleware import OrbitMiddleware
from orbit.models import OrbitEntry

@pytest.mark.django_db
def test_middleware_captures_request():
    factory = RequestFactory()
    request = factory.get('/api/users/')
    
    middleware = OrbitMiddleware(lambda r: HttpResponse('OK'))
    response = middleware(request)
    
    assert response.status_code == 200
    assert OrbitEntry.objects.filter(type='request').exists()
```

## Architecture Overview

### Key Components

1. **Models** (`models.py`)
   - `OrbitEntry`: Central storage for all telemetry data

2. **Middleware** (`middleware.py`)
   - `OrbitMiddleware`: Orchestrates request/response capture

3. **Recorders** (`recorders.py`)
   - SQL query interception using `connection.execute_wrapper`

4. **Handlers** (`handlers.py`)
   - `OrbitLogHandler`: Python logging integration

5. **Views** (`views.py`)
   - Dashboard and HTMX partial views

### Data Flow

```
Request → OrbitMiddleware → Your App → Response
              ↓                 ↓
         SQL Recorder      Log Handler
              ↓                 ↓
           OrbitEntry ← ← ← ← ←
```

## Documentation

### Updating Documentation

- Keep the README.md up to date with new features
- Update the CHANGELOG.md following Keep a Changelog format
- Add docstrings to all public functions and classes

### Building Documentation

Currently, documentation is maintained in Markdown files. A full documentation site may be added in the future.

## Release Process

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create a git tag: `git tag v0.1.0`
4. Push tags: `git push --tags`
5. Build and publish to PyPI

## Getting Help

- Open an issue for bugs or feature requests
- Use discussions for questions and ideas
- Join our community chat (link TBD)

## Code of Conduct

Please be respectful and inclusive in all interactions. We follow the [Contributor Covenant](https://www.contributor-covenant.org/) code of conduct.

## License

By contributing to Django Orbit, you agree that your contributions will be licensed under the MIT License.
