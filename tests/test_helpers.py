"""Define tests for the helpers module."""

from __future__ import annotations

import logging

import pytest

from pyatmo.exceptions import NoDeviceError
from pyatmo.helpers import (
    dict_entries,
    extract_raw_data,
    fix_id,
    number_or_none,
    str_or_none,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ([], []),
        ([{"id": "a"}], [{"id": "a"}]),
        ([{"id": "a"}, {"id": "b"}], [{"id": "a"}, {"id": "b"}]),
        ([{"id": "a"}, "junk", 1, None, ["nested"]], [{"id": "a"}]),
        (["junk"], []),
        (None, []),
        ("junk", []),
        (1, []),
        ({"id": "a"}, []),
    ],
)
def test_dict_entries(value, expected):
    """Only dict entries of a list survive; non-lists collapse to empty."""
    assert dict_entries(value) == expected


def test_dict_entries_preserves_identity():
    """Entries are the original dicts, so in-place mutation propagates."""
    entry = {"id": "a"}
    raw = [entry, "junk"]

    result = dict_entries(raw)

    assert result[0] is entry
    result[0]["id"] = "b"
    assert entry["id"] == "b"


def test_fix_id_strips_spaces_from_station_and_module_ids():
    """Superfluous spaces are stripped from station and module ids."""
    raw_data = [{"_id": "aa bb", "modules": [{"_id": "cc dd"}]}]

    assert fix_id(raw_data) == [{"_id": "aabb", "modules": [{"_id": "ccdd"}]}]


def test_fix_id_mutates_in_place():
    """The input list is mutated and returned, not copied."""
    station = {"_id": "aa bb"}
    raw_data = [station]

    assert fix_id(raw_data) is raw_data
    assert station["_id"] == "aabb"


@pytest.mark.parametrize(
    "raw_data",
    [
        [],
        None,
        ["only", "strings"],
        [{"no_id": 1}],
        [{"_id": None}],
        [{"_id": "x", "modules": []}],
    ],
)
def test_fix_id_tolerates_entries_without_ids(raw_data):
    """Non-dict entries and stations without an `_id` are passed through."""
    before = repr(raw_data)

    assert fix_id(raw_data) == raw_data
    assert repr(raw_data) == before  # unchanged


def test_fix_id_skips_non_dict_entries_but_fixes_the_rest():
    """A mixed list still gets its dict entries fixed."""
    raw_data = [{"_id": "aa bb"}, "junk", {"no_id": 1}]

    assert fix_id(raw_data) == [{"_id": "aabb"}, "junk", {"no_id": 1}]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("abc", "abc"),
        ("", ""),
        (None, None),
        (7, None),
        (0, None),
        (True, None),
        (1.5, None),
        (b"abc", None),
        ([1], None),
        ({"a": 1}, None),
    ],
)
def test_str_or_none(value, expected):
    """Strings pass through untouched; every other type collapses to None."""
    assert str_or_none(value) == expected


def test_str_or_none_logs_discarded_value(caplog):
    """A wrongly-typed value is reported, so a bad payload is not invisible."""
    with caplog.at_level(logging.DEBUG, logger="pyatmo.helpers"):
        assert str_or_none({"a": 1}) is None

    assert "{'a': 1}" in caplog.text


def test_str_or_none_stays_quiet_for_absent_value(caplog):
    """`None` means absent, which is normal and must not be logged."""
    with caplog.at_level(logging.DEBUG, logger="pyatmo.helpers"):
        assert str_or_none(None) is None

    assert caplog.text == ""


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (21, 21),
        (21.5, 21.5),
        (0, 0),
        (-5, -5),
        (None, None),
        (True, None),
        (False, None),
        ("21", None),
        ("hot", None),
        ([1], None),
        ({"a": 1}, None),
    ],
)
def test_number_or_none(value, expected):
    """Real numbers pass through; bool and every other type collapse to None."""
    assert number_or_none(value) == expected


def test_number_or_none_rejects_bool_despite_int_subclass():
    """`bool` is an `int` subclass but never a real measurement."""
    assert number_or_none(True) is None
    assert number_or_none(False) is None


def test_number_or_none_keeps_falsy_zero():
    """`0` is a valid measurement and must survive a truthiness-free check."""
    assert number_or_none(0) == 0
    assert number_or_none(0.0) == 0.0


def test_number_or_none_logs_discarded_value(caplog):
    """A wrongly-typed value is reported, so a bad payload is not invisible."""
    with caplog.at_level(logging.DEBUG, logger="pyatmo.helpers"):
        assert number_or_none("hot") is None

    assert "'hot'" in caplog.text


def test_number_or_none_stays_quiet_for_absent_value(caplog):
    """`None` means absent, which is normal and must not be logged."""
    with caplog.at_level(logging.DEBUG, logger="pyatmo.helpers"):
        assert number_or_none(None) is None

    assert caplog.text == ""


HOME_ID = "5ed02c730474377f3443794a"

# A real /homestatus 200 that answered without a `body` - the production case.
NO_BODY_RESPONSE = {"status": "ok", "time_server": 1786656837}


def test_extract_raw_data_absent_body_names_the_home(caplog):
    """A body-less 200 names the home in both the log line and the exception.

    This is the production case: /homestatus answers 200 with no `body`, and
    without the home id two homes on the same account are indistinguishable.
    """
    with (
        caplog.at_level(logging.DEBUG, logger="pyatmo.helpers"),
        pytest.raises(NoDeviceError) as exc_info,
    ):
        extract_raw_data(NO_BODY_RESPONSE, "home", home_id=HOME_ID)

    assert (
        str(exc_info.value) == f"No device found, errors in response for home {HOME_ID}"
    )
    assert f"for home {HOME_ID}" in caplog.text


def test_extract_raw_data_absent_body_unchanged_without_home_id(caplog):
    """With no home id the log line and message are byte-identical to before."""
    with (
        caplog.at_level(logging.DEBUG, logger="pyatmo.helpers"),
        pytest.raises(NoDeviceError) as exc_info,
    ):
        extract_raw_data(NO_BODY_RESPONSE, "home")

    assert str(exc_info.value) == "No device found, errors in response"
    assert caplog.messages == [
        f"Server response (tag: home): {NO_BODY_RESPONSE}",
    ]


def test_extract_raw_data_empty_tag_data_names_the_home(caplog):
    """An empty payload for the requested tag names the home too."""
    resp = {"body": {"home": []}}

    with (
        caplog.at_level(logging.DEBUG, logger="pyatmo.helpers"),
        pytest.raises(NoDeviceError) as exc_info,
    ):
        extract_raw_data(resp, "home", home_id=HOME_ID)

    assert str(exc_info.value) == f"No device data available for home {HOME_ID}"
    assert f"for home {HOME_ID}" in caplog.text


def test_extract_raw_data_empty_tag_data_unchanged_without_home_id(caplog):
    """The same branch is untouched when no home id is known."""
    resp = {"body": {"home": []}}

    with (
        caplog.at_level(logging.DEBUG, logger="pyatmo.helpers"),
        pytest.raises(NoDeviceError) as exc_info,
    ):
        extract_raw_data(resp, "home")

    assert str(exc_info.value) == "No device data available"
    assert caplog.messages == [f"Server response (tag: home): {resp}"]


def test_extract_raw_data_empty_homes_unchanged_without_home_id(caplog):
    """/homesdata is account-wide, so its message keeps its exact old wording."""
    resp = {"body": {"homes": []}}

    with (
        caplog.at_level(logging.DEBUG, logger="pyatmo.helpers"),
        pytest.raises(NoDeviceError) as exc_info,
    ):
        extract_raw_data(resp, "homes")

    assert str(exc_info.value) == "No homes found"
    assert caplog.messages == [f"Server response (tag: homes): {resp}"]


def test_extract_raw_data_home_id_is_keyword_only_and_last():
    """Existing positional calls keep working unchanged."""
    resp = {"body": {"home": [{"id": "a"}]}}

    assert extract_raw_data(resp, "home") == {"home": [{"id": "a"}], "errors": []}


def test_extract_raw_data_falsy_home_id_adds_no_noise():
    """An empty home id renders like no home id at all, not `for home `."""
    with pytest.raises(NoDeviceError) as exc_info:
        extract_raw_data(NO_BODY_RESPONSE, "home", home_id="")

    assert str(exc_info.value) == "No device found, errors in response"
