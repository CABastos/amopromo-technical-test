from rest_framework import serializers

from flight.dto import FlightSearchQuery


class FlightSearchQuerySerializer(serializers.Serializer):
    """Validates the round-trip search query string.

    Owns request *shape* — the four required parameters and their primitive
    types — then delegates request *meaning* (valid IATA codes, distinct
    endpoints, non-past departure, return on or after departure) to
    :meth:`FlightSearchQuery.from_raw`, the single source of those rules. The
    built DTO is exposed as ``validated_data["query"]`` for the view, so the
    domain rules are never duplicated in the HTTP layer.
    """

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
