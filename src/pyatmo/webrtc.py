"""WebRTC-related definitions."""

from dataclasses import dataclass


@dataclass
class WebRTCStream:
    """A WebRTC stream."""

    session_id: str
    tag_id: str


@dataclass
class WebRTCAnswer:
    """A WebRTC answer from the Netatmo API."""

    stream: WebRTCStream
    sdp: str
