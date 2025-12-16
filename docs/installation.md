# Installation

## Requirements

- Python 3.9 or higher
- Django 4.0 or higher

## Install from PyPI

```bash
pip install django-orbit
```

## Install from Source

For the latest development version:

```bash
git clone https://github.com/your-org/django-orbit.git
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
