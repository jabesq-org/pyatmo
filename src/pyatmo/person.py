"""Module to represent a Netatmo person."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pyatmo.const import RawData
from pyatmo.modules.base_class import NetatmoBase

if TYPE_CHECKING:
    from .home import Home

LOG = logging.getLogger(__name__)


@dataclass
class Person(NetatmoBase):
    """Class to represent a Netatmo person."""

    pseudo: str | None
    url: str | None

    def __init__(self, home: Home, raw_data: RawData) -> None:
        super().__init__(raw_data)
        self.home = home
        self.pseudo = raw_data.get("pseudo")
        self.url = raw_data.get("url")
