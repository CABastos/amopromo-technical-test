from datetime import timedelta

from django.utils import timezone

from applog.models import AppLogEntry

# NOTE: this module deliberately has no ``logging.getLogger`` and never logs.
# It sits on the write path of the log handler, so any log call here could feed
# back into that handler and recurse. Keeping it silent is defense-in-depth on
# top of the handler only being attached to the ``airport``/``flight`` loggers.

_MAX_LOGGER_NAME = 255
_MAX_FUNC_NAME = 255
_MAX_LEVEL_NAME = 10


class AppLogRepository:
    """Persistence for AppLogEntry rows. This is the only layer that touches the
    ORM for stored log records; the handler above it passes plain values.
    """

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
        """Insert a single log entry.

        Char fields are truncated to their column limits so an oversized logger
        or function name degrades to a shorter value rather than raising a
        ``DataError`` that the handler would have to swallow (losing the row).
        """
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
        """Delete entries older than ``days`` days. Returns the number deleted."""
        cutoff = timezone.now() - timedelta(days=days)
        deleted, _ = AppLogEntry.objects.filter(created_at__lt=cutoff).delete()
        return deleted
