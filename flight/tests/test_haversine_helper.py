import math

import pytest

from flight.helpers import EARTH_RADIUS_KM, haversine_km

# Real coordinates for Sao Paulo (GRU) and Rio de Janeiro (GIG); the great-circle
# distance between them is roughly 338 km.
GRU_LAT, GRU_LON = -23.435, -46.473
GIG_LAT, GIG_LON = -22.810, -43.251


def test_gru_to_gig_is_about_338_km():
    distance = haversine_km(GRU_LAT, GRU_LON, GIG_LAT, GIG_LON)

    assert distance == pytest.approx(338, rel=0.02)


def test_identical_points_have_zero_distance():
    assert haversine_km(GRU_LAT, GRU_LON, GRU_LAT, GRU_LON) == 0.0


def test_distance_is_symmetric():
    forward = haversine_km(GRU_LAT, GRU_LON, GIG_LAT, GIG_LON)
    backward = haversine_km(GIG_LAT, GIG_LON, GRU_LAT, GRU_LON)

    assert forward == pytest.approx(backward)


def test_antipodal_points_span_half_the_circumference():
    # A point and its antipode along the equator are half the globe apart.
    distance = haversine_km(0.0, 0.0, 0.0, 180.0)

    assert distance == pytest.approx(math.pi * EARTH_RADIUS_KM, rel=1e-9)
