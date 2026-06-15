"""
Backfill the new ``fingerprint`` column for exception entries created before B3.

Done in batches with ``iterator()`` + ``bulk_update`` so it stays memory-bounded on
large tables. The hash logic is inlined (not imported from orbit.utils) so the migration
stays stable even if the helper changes later.
"""

import hashlib

from django.db import migrations


def _fingerprint(payload):
    payload = payload or {}
    exc_type = payload.get("exception_type", "") or ""
    frames = payload.get("traceback") or []
    top = frames[-1] if frames else {}
    location = "{}:{}".format(top.get("filename", ""), top.get("name", ""))
    raw = "{}|{}".format(exc_type, location)
    return hashlib.md5(raw.encode("utf-8", "replace")).hexdigest()[:16]


def backfill(apps, schema_editor):
    OrbitEntry = apps.get_model("orbit", "OrbitEntry")
    qs = OrbitEntry.objects.filter(type="exception", fingerprint="").only("id", "payload")

    batch = []
    for entry in qs.iterator(chunk_size=500):
        entry.fingerprint = _fingerprint(entry.payload)
        batch.append(entry)
        if len(batch) >= 500:
            OrbitEntry.objects.bulk_update(batch, ["fingerprint"])
            batch = []
    if batch:
        OrbitEntry.objects.bulk_update(batch, ["fingerprint"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("orbit", "0005_orbitentry_fingerprint_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill, noop),
    ]
