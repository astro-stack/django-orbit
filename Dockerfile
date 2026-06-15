# Preview image for the Django Orbit demo dashboard.
# Not used for packaging/publishing — it boots example_project with seeded sample data.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=example_project.settings

WORKDIR /app

# Install dependencies first (better layer caching)
COPY pyproject.toml README.md ./
COPY orbit ./orbit
RUN pip install --no-cache-dir -e ".[dev]"

# App + demo project
COPY . .

EXPOSE 8000

# Fresh DB + seeded demo entries on every boot, then serve.
CMD ["sh", "-c", "python manage.py makemigrations demo && python manage.py migrate --noinput && python demo.py setup && python manage.py runserver 0.0.0.0:8000"]
