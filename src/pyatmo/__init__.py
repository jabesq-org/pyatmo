"""Expose submodules."""

from pyatmo import const, modules
from pyatmo.account import AsyncAccount
from pyatmo.auth import AbstractAsyncAuth
from pyatmo.const import SIREN_BASE_URL
from pyatmo.exceptions import (
    ApiError,
    ApiHomeReachabilityError,
    ApiThrottlingError,
    InvalidHomeError,
    InvalidRoomError,
    InvalidScheduleError,
    NoDeviceError,
    NoScheduleError,
)
from pyatmo.home import Home
from pyatmo.modules import Module
from pyatmo.modules.device_types import DeviceType
from pyatmo.room import Room
from pyatmo.webhook import (
    LifecycleStatus,
    RefreshScope,
    WebhookEvent,
    WebhookKind,
    WebhookResult,
)
from pyatmo.webrtc import WebRTCStream

__all__: list[str] = [
    "SIREN_BASE_URL",
    "AbstractAsyncAuth",
    "ApiError",
    "ApiHomeReachabilityError",
    "ApiThrottlingError",
    "AsyncAccount",
    "DeviceType",
    "Home",
    "InvalidHomeError",
    "InvalidRoomError",
    "InvalidScheduleError",
    "LifecycleStatus",
    "Module",
    "NoDeviceError",
    "NoScheduleError",
    "RefreshScope",
    "Room",
    "WebRTCStream",
    "WebhookEvent",
    "WebhookKind",
    "WebhookResult",
    "const",
    "modules",
]
