"""Define tests for Thermostat module."""
import json
import pytest
import pyatmo
import smart_home.Thermostat as th


def test_HomeData(auth, homeData, requests_mock):
    assert homeData.default_home == "MYHOME"
    assert len(homeData.rooms[homeData.default_home]) == 2

    assert len(homeData.modules[homeData.default_home]) == 3

    expected_modules = {
        "12:34:56:00:fa:d0": {
            "id": "12:34:56:00:fa:d0",
            "type": "NAPlug",
            "name": "Raumthermostat",
            "setup_date": 1494963356,
            "modules_bridged": ["12:34:56:00:01:ae"],
        },
        "12:34:56:00:01:ae": {
            "id": "12:34:56:00:01:ae",
            "type": "NATherm1",
            "name": "Livingroom",
            "setup_date": 1494963356,
            "room_id": "2746182631",
            "bridge": "12:34:56:00:fa:d0",
        },
        "12:34:56:00:f1:62": {
            "id": "12:34:56:00:f1:62",
            "type": "NACamera",
            "name": "Hall",
            "setup_date": 1544828430,
            "room_id": "3688132631",
        },
    }
    assert homeData.modules[homeData.default_home] == expected_modules


def test_HomeData_homeById(auth, homeData, requests_mock):
    home_id = "91763b24c43d3e344f424e8b"
    assert homeData.homeById(home_id)["name"] == "MYHOME"


def test_HomeData_homeByName(auth, homeData, requests_mock):
    assert homeData.homeByName()["name"] == "MYHOME"


def test_HomeData_gethomeId(auth, homeData, requests_mock):
    assert homeData.gethomeId() == "91763b24c43d3e344f424e8b"


def test_HomeData_getSelectedschedule(auth, homeData, requests_mock):
    assert homeData.getSelectedschedule()["name"] == "Default"
