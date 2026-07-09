import logging

import pytest

from applog.handlers import DatabaseLogHandler


class FakeAppLogRepository:
    """Records create_entry calls; optionally raises to simulate a DB failure."""

    def __init__(self, error=None):
        self.entries = []
        self._error = error

    def create_entry(self, **kwargs):
        if self._error is not None:
            raise self._error
        self.entries.append(kwargs)


@pytest.fixture
def make_logger():
    """Yield a factory for an isolated logger wired to a single handler.

    The logger has propagation off so records never reach the root console
    handler (or the real db_log handler), keeping each test self-contained.
    """
    created = []

    def _make(handler, name="airport.tests.handler"):
        logger = logging.getLogger(name)
        logger.handlers = [handler]
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        created.append(logger)
        return logger

    yield _make

    for logger in created:
        logger.handlers = []
        logger.propagate = True


def test_emit_persists_record_fields(make_logger):
    repo = FakeAppLogRepository()
    logger = make_logger(DatabaseLogHandler(repository=repo))

    logger.info("hello world")

    assert len(repo.entries) == 1
    entry = repo.entries[0]
    assert entry["logger_name"] == "airport.tests.handler"
    assert entry["level"] == logging.INFO
    assert entry["level_name"] == "INFO"
    assert entry["message"] == "hello world"
    assert entry["func_name"] == "test_emit_persists_record_fields"
    assert entry["lineno"] > 0
    assert entry["traceback"] == ""


def test_emit_interpolates_message_args(make_logger):
    repo = FakeAppLogRepository()
    logger = make_logger(DatabaseLogHandler(repository=repo))

    logger.warning("Skipping %s option %d: %s", "GRU", 3, "bad fare")

    assert repo.entries[0]["message"] == "Skipping GRU option 3: bad fare"
    assert repo.entries[0]["level_name"] == "WARNING"


def test_emit_captures_exception_traceback(make_logger):
    repo = FakeAppLogRepository()
    logger = make_logger(DatabaseLogHandler(repository=repo))

    try:
        raise ValueError("boom")
    except ValueError:
        logger.exception("provider failed")

    entry = repo.entries[0]
    assert entry["message"] == "provider failed"
    assert "Traceback" in entry["traceback"]
    assert "ValueError: boom" in entry["traceback"]


def test_emit_swallows_repository_errors(make_logger):
    repo = FakeAppLogRepository(error=RuntimeError("db down"))
    handler = DatabaseLogHandler(repository=repo)
    handled = []
    handler.handleError = lambda record: handled.append(record)
    logger = make_logger(handler)

    # A failing repository must never propagate out of the logging call.
    logger.error("this should not blow up")

    assert len(handled) == 1
    assert repo.entries == []


def test_handler_level_filters_below_threshold(make_logger):
    repo = FakeAppLogRepository()
    logger = make_logger(DatabaseLogHandler(level=logging.WARNING, repository=repo))

    logger.info("ignored")
    logger.warning("kept")

    assert [entry["message"] for entry in repo.entries] == ["kept"]
