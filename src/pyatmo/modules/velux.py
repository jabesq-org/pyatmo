"""Module to represent VELUX ACTIVE modules."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pyatmo.modules.module import EntityBase, Module, Shutter, WifiMixin

if TYPE_CHECKING:
    from pyatmo.const import RawData
    from pyatmo.home import Home
    from pyatmo.modules.module import ModuleT


class VeluxGatewayMixin(EntityBase):
    """Mixin for VELUX gateway specific data."""

    def __init__(self, home: Home, module: ModuleT) -> None:
        """Initialize VELUX gateway data."""
        super().__init__(home, module)
        self.subtype: str | None = None
        self.firmware_revision_netatmo: int | None = None
        self.firmware_revision_thirdparty: int | None = None
        self.hardware_version: int | None = None
        self.last_seen: int | None = None
        self.last_reset_type: str | None = None
        self.busy: bool | None = None
        self.calibrating: bool | None = None
        self.is_raining: bool | None = None
        self.locked: bool | None = None
        self.locking: bool | None = None
        self.pairing: bool | None = None
        self.pincode_enabled: bool | None = None
        self.secure: bool | None = None


class VeluxOpenerMixin(EntityBase):
    """Mixin for VELUX cover specific data."""

    def __init__(self, home: Home, module: ModuleT) -> None:
        """Initialize VELUX cover data."""
        super().__init__(home, module)
        self.last_seen: int | None = None
        self.manufacturer: str | None = None
        self.mode: str | None = None
        self.silent: bool | None = None
        self.velux_type: str | None = None


class NXG(VeluxGatewayMixin, WifiMixin, Module):
    """Class to represent a VELUX ACTIVE gateway."""

    async def update(self, raw_data: RawData) -> None:
        """Update gateway state without cascading gateway data into bridged covers."""

        self.update_topology(raw_data)
        self.update_features()


class NXO(VeluxOpenerMixin, Shutter):
    """Class to represent a VELUX ACTIVE opener / cover."""
