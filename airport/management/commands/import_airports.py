from django.core.management.base import BaseCommand, CommandError

from airport.services import DomesticApiError
from airport.usecases import NoValidAirportsError, UpsertAirportsUseCase


class Command(BaseCommand):
    """Import airports from the external API into the local database.

    Thin wrapper around UpsertAirportsUseCase: it owns no business logic, only
    translating the use case's outcome into console output and a process exit
    code (CommandError -> non-zero exit) so the command is cron-friendly.
    """

    help = "Import airports from the external API into the local database."

    def handle(self, *args, **options):
        try:
            summary = UpsertAirportsUseCase().execute()
        except (DomesticApiError, NoValidAirportsError) as exc:
            raise CommandError(f"Airport import failed: {exc}") from exc

        self.stdout.write(
            self.style.SUCCESS(
                "Airport import complete: "
                f"{summary.created} created, {summary.updated} updated, "
                f"{summary.deactivated} deactivated, {summary.skipped} skipped"
            )
        )
