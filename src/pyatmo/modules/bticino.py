"""Module to represent BTicino modules."""

from __future__ import annotations

import logging

from pyatmo.modules.module import (
    DimmableMixin,
    Module,
    Shutter,
    ShutterMixin,
    Switch,
    SwitchMixin,
)

LOG: logging.Logger = logging.getLogger(__name__)

# target_position:step reported by an MHS1 actor that only understands
# open/close/stop, i.e. is not calibrated for exact positioning.
MHS1_STEP_NOT_POSITIONABLE = 100


class MyHomeShutterMixin(ShutterMixin):
    """Mixin for MyHome Server 1 (MHS1) BUS shutter actors.

    BNAS, BNAB and BNMS behave identically and do not tell exact-position
    actors apart from open/close/stop ones. Whether an individual actor
    supports exact positioning is signalled at runtime via
    `target_position:step`, so the capability properties below are
    evaluated per actor rather than fixed per class.
    """

    @property
    def can_set_target_position(self) -> bool:
        """Return whether this actor is calibrated for exact positioning.

        An actor reporting `target_position:step` == 100 only understands
        open/close/stop, and mirrors the last commanded target in
        `current_position` instead of a real one, 101 meaning never
        instructed. That much is confirmed on hardware. A step below 100
        is read as calibrated for exact positioning, following the field's
        documented meaning; no such actor was available to verify it.
        An unknown step is treated as not positionable.
        """

        return (
            self.target_position__step is not None
            and self.target_position__step < MHS1_STEP_NOT_POSITIONABLE
        )

    # Assumed to be the same signal: an actor calibrated for exact
    # positioning should also report a real position. Only the negative
    # case was observed, and nothing in the API distinguishes the two
    # capabilities, so they are derived from the same field.
    can_report_position = can_set_target_position

    @property
    def can_move_to_preferred_position(self) -> bool:
        """Return False: MHS1 hardware rejects this command with error code 5.

        Confirmed on an actor that only understands open/close/stop.
        Whether a calibrated actor would accept it is untested - no such
        actor was available, and nothing in the API says how its preset,
        if any, is reached - so the command is refused for all of them.
        """

        return False


class BNDL(Module):
    """BTicino door lock."""


class BNSL(Switch):
    """BTicino staircase light."""


class BNCX(Module):
    """BTicino internal panel = gateway."""


class BNEU(Module):
    """BTicino external unit."""


class BNCS(Switch):
    """Bticino module Controlled Socket."""


class BNXM(Module):
    """BTicino X meter."""


class BNMS(MyHomeShutterMixin, Shutter):
    """BTicino motorized shade."""


class BNAS(MyHomeShutterMixin, Module):
    """BTicino automatic shutter."""


class BNAB(MyHomeShutterMixin, Shutter):
    """BTicino automatic blind."""


class BNMH(Module):
    """BTicino MyHome server."""


class BNTH(Module):
    """BTicino thermostat."""


class BNFC(Module):
    """BTicino fan coil."""


class BNTR(Module):
    """BTicino radiator thermostat."""


class BNIL(SwitchMixin, Module):
    """BTicino intelligent light."""


class BNLD(DimmableMixin, SwitchMixin, Module):
    """BTicino dimmer light."""
