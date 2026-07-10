from django.db import models


class Airport(models.Model):
    """A Brazilian airport cached from the external airports API."""

    iata = models.CharField(max_length=3, unique=True)
    city = models.CharField(max_length=120)
    state = models.CharField(max_length=2)
    lat = models.FloatField()
    lon = models.FloatField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["iata"]

    def __str__(self) -> str:
        return f"{self.iata} ({self.city}/{self.state})"
