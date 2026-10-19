# Installation

## Requirements

- Python 3.11 or higher (3.11, 3.12, 3.13 and 3.14 are tested)
- Django 5.2 or higher (5.2 LTS, 6.0 and 6.1 are tested; Django 6.x requires Python 3.12+)

## Install from PyPI

```bash
pip install django-orbit
```

## Install from Source

For the latest development version:

```bash
git clone https://github.com/astro-stack/django-orbit.git
cd django-orbit
pip install -e .
```

## Add to Django Project

### 1. Add to INSTALLED_APPS

```python
# settings.py

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Add Orbit
    'orbit',
    
    # Your apps
    'myapp',
]
```

!!! note "Static files"
    The dashboard serves its JavaScript, CSS, icons and fonts from Orbit's own
    static files (`orbit/static/orbit/`). **No CDN or internet access is needed**,
    so it works offline and in air-gapped environments. Keep
    `django.contrib.staticfiles` installed and, in production, run
    `python manage.py collectstatic` so these files are served with the rest of
    your static assets.

### 2. Add Middleware

Add `OrbitMiddleware` early in your middleware stack to capture the full request lifecycle:

```python
# settings.py

MIDDLEWARE = [
    'orbit.middleware.OrbitMiddleware',  # Add first or second
    
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```

### 3. Include URLs

```python
# urls.py

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('orbit/', include('orbit.urls')),
    
    # Your app URLs
    path('', include('myapp.urls')),
]
```

### 4. Run Migrations

```bash
python manage.py migrate orbit
```

This creates the `orbit_orbitentry` table for storing telemetry data.

!!! note "Migrations are included"
    Django Orbit includes its migrations in the package. You only need to run `migrate`, not `makemigrations`.
    
    If you see an error like `relation "orbit_orbitentry" does not exist`, ensure you've run the migration command above.

### 5. Verify Installation

1. Start your development server:
   ```bash
   python manage.py runserver
   ```

2. Make some requests to your application

3. Visit `http://localhost:8000/orbit/`

You should see the Orbit dashboard with your captured requests!

## Optional: Development Dependencies

For contributing or running tests:

```bash
pip install django-orbit[dev]
```

This installs:
- pytest and pytest-django
- black, isort, flake8
- mypy and django-stubs

## Next Steps

- [Quick Start Guide](quickstart.md)
- [Configuration Reference](configuration.md)
