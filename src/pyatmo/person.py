"""Module to represent a Netatmo person."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import TYPE_CHECKING

from pyatmo.modules.base_class import NetatmoBase

if TYPE_CHECKING:
    from pyatmo.const import RawData

    from .home import Home

LOG = logging.getLogger(__name__)


@dataclass
class Person(NetatmoBase):
    """Class to represent a Netatmo person."""

    pseudo: str | None
    url: str | None
    out_of_sight: bool | None = None
    last_seen: int | None = None

    def __init__(self, home: Home, raw_data: RawData) -> None:
        """Initialize a Netatmo person instance."""

        super().__init__(raw_data)
        self.home = home
        self.pseudo = raw_data.get("pseudo")
        self.url = raw_data.get("url")

    def update(self, raw_data: RawData) -> None:
        """Update person data."""
        self.out_of_sight = raw_data.get("out_of_sight")
        self.last_seen = raw_data.get("last_seen")
