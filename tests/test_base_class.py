"""Tests for pyatmo.modules.base_class Place and reflection map."""

from pyatmo.modules.base_class import NETATMO_ATTRIBUTES_MAP, Location, Place


def test_place_none_assigns_all_fields() -> None:
    """Place(None) sets every declared field to None without raising."""
    place = Place(None)

    assert place.altitude is None
    assert place.city is None
    assert place.country is None
    assert place.timezone is None
    assert place.location is None


def test_place_none_equality_does_not_raise() -> None:
    """Comparing two Place(None) instances must not raise AttributeError."""
    assert Place(None) == Place(None)


def test_place_dict_without_location() -> None:
    """A dict lacking a valid location keeps other fields, location is None."""
    place = Place({"altitude": 100, "city": "X"})

    assert place.altitude == 100
    assert place.city == "X"
    assert place.country is None
    assert place.timezone is None
    assert place.location is None


def test_place_full_dict() -> None:
    """A fully valid dict populates all fields including a Location."""
    place = Place(
        {
            "altitude": 329,
            "city": "Somewhere",
            "country": "DE",
            "location": [6.1234567, 46.123456],
            "timezone": "Europe/Berlin",
        },
    )

    assert place.altitude == 329
    assert place.city == "Somewhere"
    assert place.country == "DE"
    assert place.timezone == "Europe/Berlin"
    assert place.location == Location(longitude=6.1234567, latitude=46.123456)


def test_place_malformed_location_length() -> None:
    """Wrong-length location leaves location None but keeps other fields."""
    place = Place({"altitude": 100, "city": "X", "location": [1.0]})

    assert place.altitude == 100
    assert place.city == "X"
    assert place.location is None


def test_place_malformed_location_type() -> None:
    """Non-iterable location leaves location None but keeps other fields."""
    place = Place({"altitude": 100, "city": "X", "location": 42})

    assert place.altitude == 100
    assert place.city == "X"
    assert place.location is None


def test_reflection_place_absent_keeps_previous() -> None:
    """When 'place' key is absent, the previous value is kept."""
    fn = NETATMO_ATTRIBUTES_MAP["place"]
    sentinel = object()

    assert fn({}, sentinel) is sentinel


def test_reflection_place_null_keeps_previous() -> None:
    """When 'place' is None, the previous value is kept."""
    fn = NETATMO_ATTRIBUTES_MAP["place"]
    sentinel = object()

    assert fn({"place": None}, sentinel) is sentinel


def test_reflection_place_present_builds_place() -> None:
    """When 'place' is a valid dict, a populated Place is built."""
    fn = NETATMO_ATTRIBUTES_MAP["place"]

    result = fn(
        {
            "place": {
                "altitude": 329,
                "city": "Somewhere",
                "country": "DE",
                "location": [6.1234567, 46.123456],
                "timezone": "Europe/Berlin",
            },
        },
        None,
    )

    assert isinstance(result, Place)
    assert result.altitude == 329
    assert result.location == Location(longitude=6.1234567, latitude=46.123456)


def test_reflection_place_present_invalid_location() -> None:
    """Present 'place' with invalid location builds Place, location None."""
    fn = NETATMO_ATTRIBUTES_MAP["place"]
    sentinel = object()

    result = fn(
        {
            "place": {
                "altitude": 329,
                "city": "Somewhere",
                "location": [1.0, 2.0, 3.0],
            },
        },
        sentinel,
    )

    assert isinstance(result, Place)
    assert result.altitude == 329
    assert result.city == "Somewhere"
    assert result.location is None
