import logging

from django.apps import apps

_EXC_FORMATTER = logging.Formatter()


class DatabaseLogHandler(logging.Handler):
    """Logging handler that persists records to the AppLogEntry table."""

    def __init__(self, level: int = logging.NOTSET, repository=None) -> None:
        super().__init__(level)
        self._repository = repository

    def emit(self, record: logging.LogRecord) -> None:
        try:
            if not apps.ready:
                return

            if self._repository is None:
                from applog.repositories import AppLogRepository

                self._repository = AppLogRepository()

            self._repository.create_entry(
                logger_name=record.name,
                level=record.levelno,
                level_name=record.levelname,
                message=record.getMessage(),
                func_name=record.funcName or "",
                lineno=record.lineno or 0,
                traceback=self._format_traceback(record),
            )
        except Exception:
            self.handleError(record)

    @staticmethod
    def _format_traceback(record: logging.LogRecord) -> str:
        """Render the record's exception info to text, or "" when there is none."""
        if not record.exc_info:
            return ""
        return record.exc_text or _EXC_FORMATTER.formatException(record.exc_info)
