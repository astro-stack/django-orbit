# Troubleshooting

!!! info "Need Help?"
    If you can't find your answer here, [open an issue](https://github.com/astro-stack/django-orbit/issues) on GitHub.

## Common Issues

### Dashboard shows "No entries yet"

**Possible causes:**

1. **Middleware not configured** - Make sure `OrbitMiddleware` is in your `MIDDLEWARE` list
2. **Orbit disabled** - Check that `ORBIT['ENABLED']` is `True`
3. **No requests made** - Make some requests to your app first

### Queries not being captured

**Solution:** Ensure the middleware is at the **first position** in `MIDDLEWARE`:

```python
MIDDLEWARE = [
    'orbit.middleware.OrbitMiddleware',  # Must be first!
    ...
]
```

### Logs not appearing

**Solution:** Configure Django's logging to use OrbitLogHandler:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'orbit': {
            'class': 'orbit.handlers.OrbitLogHandler',
        },
    },
    'root': {
        'handlers': ['orbit'],
        'level': 'DEBUG',
    },
}
```

### Dashboard CSS not loading

**Solution:** Run collectstatic:

```bash
python manage.py collectstatic
```

### "Failed to load details" error in dashboard

**Possible causes:**

1. **Custom URL prefix** - If you mounted Orbit URLs at a custom path (not `/orbit/`), make sure you're using the latest version of Django Orbit which uses dynamic URLs.

2. **CSRF issues in Docker/containerized environments** - Ensure your Django `CSRF_TRUSTED_ORIGINS` includes your container's hostname:

```python
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'http://your-container-name:8000',
]
```

3. **Database migrations not applied** - Run migrations inside your container:

```bash
docker-compose exec web python manage.py migrate
```

---

*Still stuck? [Open an issue](https://github.com/astro-stack/django-orbit/issues)!*
