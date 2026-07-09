from datetime import timedelta

import pytest
from django.utils import timezone

from applog.models import AppLogEntry
from applog.repositories import AppLogRepository


@pytest.mark.django_db
def test_create_entry_persists_all_fields():
    AppLogRepository().create_entry(
        logger_name="flight.services.mock",
        level=40,
        level_name="ERROR",
        message="provider failed",
        func_name="search_flights",
        lineno=71,
        traceback="Traceback ...",
    )

    entry = AppLogEntry.objects.get()
    assert entry.logger_name == "flight.services.mock"
    assert entry.level == 40
    assert entry.level_name == "ERROR"
    assert entry.message == "provider failed"
    assert entry.func_name == "search_flights"
    assert entry.lineno == 71
    assert entry.traceback == "Traceback ..."
    assert entry.created_at is not None


@pytest.mark.django_db
def test_create_entry_truncates_oversized_char_fields():
    AppLogRepository().create_entry(
        logger_name="x" * 300,
        level=20,
        level_name="INFORMATION_OVERFLOW",
        message="ok",
        func_name="y" * 300,
    )

    entry = AppLogEntry.objects.get()
    assert len(entry.logger_name) == 255
    assert len(entry.func_name) == 255
    assert entry.level_name == "INFORMATIO"  # truncated to the 10-char column


@pytest.mark.django_db
def test_purge_older_than_deletes_only_old_rows():
    repo = AppLogRepository()
    repo.create_entry(logger_name="a", level=20, level_name="INFO", message="old")
    repo.create_entry(logger_name="b", level=20, level_name="INFO", message="new")

    # auto_now_add ignores constructor values, so backdate the column directly
    # to push the first row beyond the retention cutoff.
    old = AppLogEntry.objects.get(message="old")
    AppLogEntry.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=40))

    deleted = repo.purge_older_than(30)

    assert deleted == 1
    assert list(AppLogEntry.objects.values_list("message", flat=True)) == ["new"]
