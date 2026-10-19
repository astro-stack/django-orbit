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

Pull requests also run GitHub Actions CI on supported Python/Django combinations, release metadata, documentation builds, package builds and Twine metadata checks.

Dashboard clipboard behavior is also checked with Node.js 24 and its built-in
test runner (no npm dependencies):

```bash
node --test tests/js/handoff_clipboard.test.cjs
```

Before pushing a release PR, run the same local preflight used by maintainers:

```bash
python scripts/verify_release.py
```

For a quick metadata-only check:

```bash
python scripts/verify_release.py --metadata-only
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

## Rebuilding dashboard assets

The dashboard ships compiled assets in `orbit/static/orbit/` (CSS, vendored
libraries, icon bundle and fonts). Their sources and build tooling live in
`frontend/`. You only need Node.js 20+ when you change Tailwind classes, icons
or a vendored library version:

```bash
cd frontend
npm ci
npm run build:css     # compile orbit.css (Tailwind CSS 3.4) from input.css
npm run build:icons   # bundle only the Lucide icons listed in build-icons.mjs
npm run vendor        # copy pinned htmx/Alpine/ApexCharts/fonts from node_modules
npm run build         # all of the above
```

Commit the regenerated files under `orbit/static/orbit/`; never commit
`frontend/node_modules`. Add new icon names to `frontend/build-icons.mjs`, bump
versions in `frontend/package.json` and `orbit/static/orbit/vendor/LICENSES.md`
together, and keep dynamically built Tailwind class names in the `safelist` in
`frontend/tailwind.config.js`.
