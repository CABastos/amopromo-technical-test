from django.db import models


class AppLogEntry(models.Model):
    """A persisted application log record written by DatabaseLogHandler."""

    logger_name = models.CharField(max_length=255)
    level = models.PositiveSmallIntegerField()
    level_name = models.CharField(max_length=10)
    message = models.TextField()
    func_name = models.CharField(max_length=255, blank=True, default="")
    lineno = models.PositiveIntegerField(default=0)
    traceback = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["level"]),
            models.Index(fields=["logger_name"]),
        ]
        verbose_name_plural = "app log entries"

    def __str__(self) -> str:
        return f"[{self.level_name}] {self.logger_name}: {self.message[:80]}"
