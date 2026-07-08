import math

# Mean Earth radius in kilometers (IUGG). The great-circle distance below
# assumes a spherical Earth, which is accurate to well within the tolerance
# flight-distance enrichment needs.
EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometers between two lat/lon points.

    Uses the haversine formula on a spherical Earth. Arguments are decimal
    degrees; the result is always non-negative and is 0.0 for identical points.
    """
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))
