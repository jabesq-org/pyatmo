"""Module to represent a Netatmo schedule."""
from __future__ import annotations

import logging
from dataclasses import dataclass

LOG = logging.getLogger(__name__)


@dataclass
class NetatmoSchedule:
    """Class to represent a Netatmo schedule."""

    entity_id: str
    name: str
    home_id: str
    selected: bool
    away_temp: float | None
    hg_temp: float | None

    def __init__(self, home_id: str, raw_data) -> None:
        self.entity_id = raw_data["id"]
        self.name = raw_data["name"]
        self.home_id = home_id
        self.selected = raw_data.get("selected", False)
        self.hg_temp = raw_data.get("hg_temp")
        self.away_temp = raw_data.get("away_temp")
