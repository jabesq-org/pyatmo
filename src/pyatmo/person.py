"""Module to represent a Netatmo person."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pyatmo.modules.base_class import NetatmoBase

if TYPE_CHECKING:
    from .home import NetatmoHome

LOG = logging.getLogger(__name__)


@dataclass
class NetatmoPerson(NetatmoBase):
    """Class to represent a Netatmo person."""

    pseudo: str | None
    url: str | None

    def __init__(self, home: NetatmoHome, raw_data) -> None:
        super().__init__(raw_data)
        self.home = home
        self.pseudo = raw_data.get("pseudo")
        self.url = raw_data.get("url")
