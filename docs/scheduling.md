# Scheduled Data Cleanup

To prevent the `OrbitEntry` table from growing indefinitely, you should schedule the `orbit_prune` management command to run periodically.

## 1. Using Crontab (Linux/macOS)

If you are running on a Linux server, the simplest method is to use `cron`.

Open your crontab:
```bash
crontab -e
```

Add the following line to run the cleanup daily at midnight:
```bash
# Prune Orbit data every day at 00:00, keeping last 24h
0 0 * * * /path/to/your/venv/bin/python /path/to/your/project/manage.py orbit_prune --hours 24
```

To keep 7 days of data but preserve errors indefinitely:
```bash
0 0 * * * /path/to/your/venv/bin/python /path/to/your/project/manage.py orbit_prune --hours 168 --keep-important
```

## 2. Using Celery Beat

If your project uses [Celery](https://docs.celeryq.dev/) and [django-celery-beat](https://django-celery-beat.readthedocs.io/), you can define a periodic task.

in `settings.py` or your celery config:

```python
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'orbit-prune-daily': {
        'task': 'orbit.tasks.prune_orbit_entries', # You might need to wrap the command in a task or use a generic command task
        'schedule': crontab(minute=0, hour=0),
        'args': (24,), 
    },
}
```

Since Orbit doesn't ship with a built-in Celery task (to avoid forcing a dependency), you can create a wrapper task in your project:

```python
# your_project/tasks.py
from celery import shared_task
from django.core.management import call_command

@shared_task
def prune_orbit_entries():
    call_command("orbit_prune", hours=24, keep_important=True)
```

## 3. Windows Task Scheduler

If you are developing or hosting on Windows:

1.  Open **Task Scheduler**.
2.  Create a **Basic Task** named "Orbit Prune".
3.  Trigger: **Daily**.
4.  Action: **Start a program**.
5.  Program/script: `path\to\python.exe`
6.  Add arguments: `manage.py orbit_prune --hours 24`
7.  Start in: `path\to\your\project\`

## Command Reference

| Argument | Default | Description |
| :--- | :--- | :--- |
| `--hours` | `24` | Number of hours of data to retain. |
| `--keep-important` | `False` | If flag is present, explicitly prevents deletion of Exceptions and Error Logs, regardless of age. |
