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
