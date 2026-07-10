import logging
from decimal import Decimal

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from airport.dto import AirportDTO
from flight.dto import FlightOptionDTO, RoundTripOptionDTO
from flight.services import MockAirlinesApiError
from flight.usecases import FlightSearchResult, SearchRoundTripUseCase, UnknownAirportError

from .flight_search_query_serializer import FlightSearchQuerySerializer
from .static_token_authentication import StaticTokenAuthentication

logger = logging.getLogger(__name__)


class SearchFlightsView(APIView):
    """``GET /api/flights/search/`` — round-trip flight search.

    Thin delivery layer: it authenticates the request, validates the query into
    a DTO, runs :class:`SearchRoundTripUseCase`, and presents the result. It
    owns no business logic — only HTTP concerns (status codes, response shape).

    ``use_case_factory`` is a class attribute so tests can inject a fake with
    ``SearchFlightsView.as_view(use_case_factory=...)``.
    """

    authentication_classes = [StaticTokenAuthentication]
    permission_classes = [IsAuthenticated]
    use_case_factory = SearchRoundTripUseCase

    def get(self, request):
        serializer = FlightSearchQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)  # -> 400 on invalid input
        query = serializer.validated_data["query"]

        try:
            result = self.use_case_factory().execute(query)
        except UnknownAirportError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except MockAirlinesApiError:
            logger.exception("Flight provider call failed")
            return Response(
                {"detail": "Flight provider is unavailable."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(_serialize_result(result), status=status.HTTP_200_OK)


# --- Presenters ------------------------------------------------------------
# Map DTOs onto the JSON response. Per-flight blocks keep the provider's
# contract names (``fees``, ``range``); the top-level ``price`` is our
# round-trip aggregation.


def _serialize_airport(airport: AirportDTO) -> dict:
    return {
        "iata": airport.iata,
        "city": airport.city,
        "state": airport.state,
        "lat": airport.lat,
        "lon": airport.lon,
    }


def _serialize_price(fare: Decimal, fee: Decimal, total: Decimal) -> dict:
    return {"fare": fare, "fees": fee, "total": total}


def _serialize_flight(option: FlightOptionDTO) -> dict:
    return {
        "departure_time": option.departure_time.isoformat(),
        "arrival_time": option.arrival_time.isoformat(),
        "aircraft": {
            "model": option.aircraft_model,
            "manufacturer": option.aircraft_manufacturer,
        },
        "price": _serialize_price(option.fare, option.fee, option.total),
        "meta": {
            "range": option.range_km,
            "cruise_speed_kmh": option.cruise_speed_kmh,
            "cost_per_km": option.cost_per_km,
        },
    }


def _serialize_round_trip(round_trip: RoundTripOptionDTO) -> dict:
    return {
        "price": _serialize_price(round_trip.fare, round_trip.fee, round_trip.total),
        "outbound": _serialize_flight(round_trip.outbound),
        "inbound": _serialize_flight(round_trip.inbound),
    }


def _serialize_result(result: FlightSearchResult) -> dict:
    return {
        "summary": {
            "from": _serialize_airport(result.origin),
            "to": _serialize_airport(result.destination),
            "departure_date": result.departure_date.isoformat(),
            "return_date": result.return_date.isoformat(),
            "currency": result.currency,
            "range_km": result.range_km,
        },
        "count": len(result.options),
        "options": [_serialize_round_trip(option) for option in result.options],
    }
