import logging

from django.apps import apps

# A shared, stateless formatter used only to render exc_info into text.
_EXC_FORMATTER = logging.Formatter()


class DatabaseLogHandler(logging.Handler):
    """Logging handler that persists records to the ``AppLogEntry`` table.

    Wired via ``LOGGING`` in settings and attached only to the ``airport`` and
    ``flight`` loggers. Because it is not attached to ``django.*``, the ORM
    writes it performs (which log under ``django.db.backends``) cannot feed back
    into it, so there is no logging recursion.

    Two hard rules:

    * ``emit`` never raises. Any failure (DB down, broken transaction) is routed
      to :meth:`logging.Handler.handleError`, so a logging call can never break
      a request or the import command — a lost log row is the worst case.
    * Nothing at module import time may touch models or the ORM. ``logging.config``
      imports and instantiates this class during ``django.setup()`` *before* the
      app registry is populated, so importing ``AppLogEntry``/``AppLogRepository``
      at the top would raise ``AppRegistryNotReady`` and break ``manage.py``.
      The repository is therefore imported lazily inside :meth:`emit`.
    """

    def __init__(self, level: int = logging.NOTSET, repository=None) -> None:
        super().__init__(level)
        # dictConfig instantiates with no arguments, so ``repository`` stays None
        # until the first emit; tests inject a fake here.
        self._repository = repository

    def emit(self, record: logging.LogRecord) -> None:
        try:
            # Records can arrive during startup, after logging is configured but
            # before the app registry is ready; drop those rather than crash.
            if not apps.ready:
                return

            if self._repository is None:
                # Deferred import — see the class docstring (R1). Do not hoist.
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
        # Reuse exc_text if a prior formatter already cached it.
        return record.exc_text or _EXC_FORMATTER.formatException(record.exc_info)
