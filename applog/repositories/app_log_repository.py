from datetime import timedelta

from django.utils import timezone

from applog.models import AppLogEntry

_MAX_LOGGER_NAME = 255
_MAX_FUNC_NAME = 255
_MAX_LEVEL_NAME = 10


class AppLogRepository:
    """Persistence for AppLogEntry rows."""

    def create_entry(
        self,
        *,
        logger_name: str,
        level: int,
        level_name: str,
        message: str,
        func_name: str = "",
        lineno: int = 0,
        traceback: str = "",
    ) -> None:
        """Insert a single log entry."""
        AppLogEntry.objects.create(
            logger_name=logger_name[:_MAX_LOGGER_NAME],
            level=level,
            level_name=level_name[:_MAX_LEVEL_NAME],
            message=message,
            func_name=func_name[:_MAX_FUNC_NAME],
            lineno=lineno,
            traceback=traceback,
        )

    def purge_older_than(self, days: int) -> int:
        """Delete entries older than the given number of days."""
        cutoff = timezone.now() - timedelta(days=days)
        deleted, _ = AppLogEntry.objects.filter(created_at__lt=cutoff).delete()
        return deleted
