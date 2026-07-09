from django.contrib import admin

from applog.admin import AppLogEntryAdmin
from applog.models import AppLogEntry


def test_app_log_entry_is_registered():
    assert AppLogEntry in admin.site._registry
    assert isinstance(admin.site._registry[AppLogEntry], AppLogEntryAdmin)


def test_admin_is_read_only():
    model_admin = admin.site._registry[AppLogEntry]

    assert model_admin.has_add_permission(None) is False
    assert model_admin.has_change_permission(None) is False
    assert model_admin.has_delete_permission(None) is False


def test_admin_list_configuration():
    model_admin = admin.site._registry[AppLogEntry]

    assert model_admin.list_display == (
        "created_at",
        "level_name",
        "logger_name",
        "short_message",
    )
    assert model_admin.list_filter == ("level_name", "logger_name")
    assert model_admin.search_fields == ("message", "logger_name", "traceback")
    assert model_admin.date_hierarchy == "created_at"


def test_short_message_truncates_to_120_chars():
    model_admin = admin.site._registry[AppLogEntry]
    # No DB write needed — the display method reads the in-memory instance.
    entry = AppLogEntry(message="x" * 200)

    assert model_admin.short_message(entry) == "x" * 120
