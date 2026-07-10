from django.core.management.base import BaseCommand, CommandError

from applog.repositories import AppLogRepository


class Command(BaseCommand):
    """Delete stored application log entries older than N days."""

    help = "Delete stored application log entries older than N days."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Delete entries older than this many days (default: 30).",
        )

    def handle(self, *args, **options):
        days = options["days"]
        if days < 1:
            raise CommandError("--days must be a positive integer")

        deleted = AppLogRepository().purge_older_than(days)
        self.stdout.write(
            self.style.SUCCESS(f"Purged {deleted} log entries older than {days} days")
        )
