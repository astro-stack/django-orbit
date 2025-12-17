
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from orbit.models import OrbitEntry

class Command(BaseCommand):
    help = "Prune old Orbit entries (requests, queries, etc.)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--hours",
            type=int,
            default=24,
            help="Number of hours of data to keep (default: 24)",
        )
        parser.add_argument(
            "--keep-important",
            action="store_true",
            help="Keep exceptions and logs with level ERROR or higher",
        )

    def handle(self, *args, **options):
        hours = options["hours"]
        keep_important = options["keep_important"]
        
        cutoff = timezone.now() - timedelta(hours=hours)
        
        # Base query: older than cutoff
        qs = OrbitEntry.objects.filter(created_at__lt=cutoff)
        
        if keep_important:
            # Exclude exceptions
            qs = qs.exclude(type=OrbitEntry.TYPE_EXCEPTION)
            # Exclude error logs (payload__level="ERROR" or "CRITICAL")
            # Note: payload is JSON field, so we query it directly
            qs = qs.exclude(
                type=OrbitEntry.TYPE_LOG,
                payload__level__in=["ERROR", "CRITICAL"]
            )
            
        count, _ = qs.delete()
        
        self.stdout.write(
            self.style.SUCCESS(f"Successfully pruned {count} Orbit entries older than {hours} hours.")
        )
