import pytest

from airport.dto import AirportDTO


def _raw(city="Sao Paulo", state="SP", lat=-23.4, lon=-46.4):
    return {"iata": "IGNORED", "city": city, "state": state, "lat": lat, "lon": lon}


def test_from_raw_builds_dto_from_valid_record():
    dto = AirportDTO.from_raw("GRU", _raw())

    assert dto == AirportDTO(iata="GRU", city="Sao Paulo", state="SP", lat=-23.4, lon=-46.4)


def test_from_raw_normalizes_values():
    dto = AirportDTO.from_raw(
        "gru", _raw(city="  Sao Paulo  ", state="sp", lat="-23.4", lon="-46.4")
    )

    assert dto.iata == "GRU"
    assert dto.state == "SP"
    assert dto.city == "Sao Paulo"
    assert dto.lat == -23.4
    assert dto.lon == -46.4
    assert isinstance(dto.lat, float)


def test_from_raw_accepts_range_boundaries():
    dto = AirportDTO.from_raw("AAA", _raw(lat=-90.0, lon=180.0))

    assert dto.lat == -90.0
    assert dto.lon == 180.0


@pytest.mark.parametrize(
    ("code", "raw"),
    [
        pytest.param("XX", _raw(), id="iata-too-short"),
        pytest.param("GRUX", _raw(), id="iata-too-long"),
        pytest.param("G1U", _raw(), id="iata-not-letters"),
        pytest.param("GRU", "not-a-dict", id="record-not-object"),
        pytest.param("GRU", {"city": "X", "state": "SP", "lon": 0.0}, id="missing-field"),
        pytest.param("GRU", _raw(city="   "), id="empty-city"),
        pytest.param("GRU", _raw(state="Sao Paulo"), id="state-too-long"),
        pytest.param("GRU", _raw(lat=91.0), id="lat-above-range"),
        pytest.param("GRU", _raw(lat=-90.1), id="lat-below-range"),
        pytest.param("GRU", _raw(lon=180.1), id="lon-above-range"),
        pytest.param("GRU", _raw(lon=-181.0), id="lon-below-range"),
        pytest.param("GRU", _raw(lat="north"), id="non-numeric-coord"),
    ],
)
def test_from_raw_rejects_invalid_records(code, raw):
    with pytest.raises(ValueError):
        AirportDTO.from_raw(code, raw)
