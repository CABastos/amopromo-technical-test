from django.contrib import admin

from applog.models import AppLogEntry


@admin.register(AppLogEntry)
class AppLogEntryAdmin(admin.ModelAdmin):
    """Read-only admin for stored application logs."""

    list_display = ("created_at", "level_name", "logger_name", "short_message")
    list_filter = ("level_name", "logger_name")
    search_fields = ("message", "logger_name", "traceback")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_per_page = 50

    @admin.display(description="message")
    def short_message(self, obj: AppLogEntry) -> str:
        return obj.message[:120]

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False
