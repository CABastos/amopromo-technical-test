from rest_framework import serializers

from flight.dto import FlightSearchQuery


class FlightSearchQuerySerializer(serializers.Serializer):
    """Validates the round-trip search query string."""

    origin = serializers.CharField()
    destination = serializers.CharField()
    departure_date = serializers.DateField()
    return_date = serializers.DateField()

    def validate(self, attrs):
        try:
            attrs["query"] = FlightSearchQuery.from_raw(
                attrs["origin"],
                attrs["destination"],
                attrs["departure_date"],
                attrs["return_date"],
            )
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc
        return attrs
