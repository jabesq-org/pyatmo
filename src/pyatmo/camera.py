"""Support for Netatmo security devices (cameras, smoke detectors, sirens, window sensors, events and persons)."""
from __future__ import annotations

import imghdr
import time
from abc import ABC
from collections import defaultdict
from typing import Any
from warnings import warn

import aiohttp
from requests.exceptions import ReadTimeout

from pyatmo.auth import AbstractAsyncAuth, NetatmoOAuth2
from pyatmo.const import (
    GETCAMERAPICTURE_ENDPOINT,
    GETEVENTSUNTIL_ENDPOINT,
    GETHOMEDATA_ENDPOINT,
    SETPERSONSAWAY_ENDPOINT,
    SETPERSONSHOME_ENDPOINT,
    SETSTATE_ENDPOINT,
)
from pyatmo.exceptions import ApiError, NoDevice
from pyatmo.helpers import LOG, extract_raw_data

warn(f"The module {__name__} is deprecated.", DeprecationWarning, stacklevel=2)


class AbstractCameraData(ABC):
    """Abstract class of Netatmo camera data."""

    raw_data: dict = defaultdict(dict)
    homes: dict = defaultdict(dict)
    persons: dict = defaultdict(dict)
    events: dict = defaultdict(dict)
    outdoor_events: dict = defaultdict(dict)
    cameras: dict = defaultdict(dict)
    smoke_detectors: dict = defaultdict(dict)
    modules: dict = {}
    last_event: dict = {}
    outdoor_last_event: dict = {}
    types: dict = defaultdict(dict)

    def process(self) -> None:
        """Process data from API."""
        self.homes = {d["id"]: d for d in self.raw_data}

        for item in self.raw_data:
            home_id: str = item.get("id", "")

            if not item.get("name"):
                self.homes[home_id]["name"] = "Unknown"

            self._store_events(events=item.get("events", []))
            self._store_cameras(cameras=item.get("cameras", []), home_id=home_id)
            self._store_smoke_detectors(
                smoke_detectors=item.get("smokedetectors", []),
                home_id=home_id,
            )
            for person in item.get("persons", []):
                self.persons[home_id][person["id"]] = person

    def _store_persons(self, persons: list) -> None:
        for person in persons:
            self.persons[person["id"]] = person

    def _store_smoke_detectors(self, smoke_detectors: list, home_id: str) -> None:
        for smoke_detector in smoke_detectors:
            self.smoke_detectors[home_id][smoke_detector["id"]] = smoke_detector
            self.types[home_id][smoke_detector["type"]] = smoke_detector

    def _store_cameras(self, cameras: list, home_id: str) -> None:
        for camera in cameras:
            self.cameras[home_id][camera["id"]] = camera
            self.types[home_id][camera["type"]] = camera

            if camera.get("name") is None:
                self.cameras[home_id][camera["id"]]["name"] = camera["type"]

            self.cameras[home_id][camera["id"]]["home_id"] = home_id
            if camera["type"] == "NACamera":
                for module in camera.get("modules", []):
                    self.modules[module["id"]] = module
                    self.modules[module["id"]]["cam_id"] = camera["id"]

    def _store_events(self, events: list) -> None:
        """Store all events."""
        for event in events:
            if event["type"] == "outdoor":
                self.outdoor_events[event["camera_id"]][event["time"]] = event

            else:
                self.events[event["camera_id"]][event["time"]] = event

    def _store_last_event(self) -> None:
        """Store last event for fast access."""
        for camera in self.events:
            self.last_event[camera] = self.events[camera][
                sorted(self.events[camera])[-1]
            ]

        for camera in self.outdoor_events:
            self.outdoor_last_event[camera] = self.outdoor_events[camera][
                sorted(self.outdoor_events[camera])[-1]
            ]

    def get_camera(self, camera_id: str) -> dict[str, str]:
        """Get camera data."""
        return next(
            (
                self.cameras[home_id][camera_id]
                for home_id in self.cameras
                if camera_id in self.cameras[home_id]
            ),
            {},
        )

    def get_camera_home_id(self, camera_id: str) -> str | None:
        """Get camera data."""
        return next(
            (home_id for home_id in self.cameras if camera_id in self.cameras[home_id]),
            None,
        )

    def get_module(self, module_id: str) -> dict | None:
        """Get module data."""
        return None if module_id not in self.modules else self.modules[module_id]

    def get_smokedetector(self, smoke_id: str) -> dict | None:
        """Get smoke detector."""
        return next(
            (
                self.smoke_detectors[home_id][smoke_id]
                for home_id in self.smoke_detectors
                if smoke_id in self.smoke_detectors[home_id]
            ),
            None,
        )

    def camera_urls(self, camera_id: str) -> tuple[str | None, str | None]:
        """
        Return the vpn_url and the local_url (if available) of a given camera
        in order to access its live feed.
        """
        camera_data = self.get_camera(camera_id)
        return camera_data.get("vpn_url", None), camera_data.get("local_url", None)

    def get_light_state(self, camera_id: str) -> str | None:
        """Return the current mode of the floodlight of a presence camera."""
        camera_data = self.get_camera(camera_id)
        if camera_data is None:
            raise ValueError("Invalid Camera ID")

        return camera_data.get("light_mode_status")

    def persons_at_home(self, home_id: str = None) -> list:
        """Return a list of known persons who are currently at home."""
        home_data = self.homes.get(home_id, {})
        return [
            person["pseudo"]
            for person in home_data.get("persons", [])
            if "pseudo" in person and not person["out_of_sight"]
        ]

    def get_person_id(self, name: str, home_id: str) -> str | None:
        """Retrieve the ID of a person."""
        return next(
            (
                pid
                for pid, data in self.persons[home_id].items()
                if name == data.get("pseudo")
            ),
            None,
        )

    def build_event_id(self, event_id: str | None, device_type: str | None):
        """Build event id."""

        def get_event_id(data: dict):
            events = {e["time"]: e for e in data.values()}
            return min(events.items())[1].get("id")

        if not event_id:
            # If no event is provided we need to retrieve the oldest of
            # the last event seen by each camera
            if device_type == "NACamera":
                # for the Welcome camera
                event_id = get_event_id(self.last_event)

            elif device_type in {"NOC", "NSD"}:
                # for the Presence camera and for the smoke detector
                event_id = get_event_id(self.outdoor_last_event)

        return event_id

    def person_seen_by_camera(
        self,
        name: str,
        camera_id: str,
        exclude: int = 0,
    ) -> bool:
        """Evaluate if a specific person has been seen."""
        home_id = self.get_camera_home_id(camera_id)

        if home_id is None:
            raise NoDevice

        def _person_in_event(home_id: str, curr_event: dict, person_name: str) -> bool:
            person_id = curr_event.get("person_id")
            return (
                curr_event["type"] == "person"
                and self.persons[home_id][person_id].get("pseudo") == person_name
            )

        if exclude:
            limit = time.time() - exclude
            array_time_event = sorted(self.events[camera_id], reverse=True)

            for time_ev in array_time_event:
                if time_ev < limit:
                    return False

                current_event = self.events[camera_id][time_ev]
                if _person_in_event(home_id, current_event, name):
                    return True

            return False

        current_event = self.last_event[camera_id]
        return _person_in_event(home_id, current_event, name)

    def _known_persons(self, home_id: str) -> dict[str, dict]:
        """Return all known persons."""
        return {pid: p for pid, p in self.persons[home_id].items() if "pseudo" in p}

    def known_persons(self, home_id: str) -> dict[str, str]:
        """Return a dictionary of known person names."""
        return {pid: p["pseudo"] for pid, p in self._known_persons(home_id).items()}

    def known_persons_names(self, home_id: str) -> list[str]:
        """Return a list of known person names."""
        return [person["pseudo"] for person in self._known_persons(home_id).values()]

    def someone_known_seen(self, camera_id: str, exclude: int = 0) -> bool:
        """Evaluate if someone known has been seen."""
        if camera_id not in self.events:
            raise NoDevice

        if (home_id := self.get_camera_home_id(camera_id)) is None:
            raise NoDevice

        def _someone_known_seen(event: dict, home_id: str) -> bool:
            return event["type"] == "person" and event[
                "person_id"
            ] in self._known_persons(home_id)

        if exclude:
            limit = time.time() - exclude
            array_time_event = sorted(self.events[camera_id], reverse=True)
            seen = False

            for time_ev in array_time_event:
                if time_ev < limit:
                    continue
                if seen := _someone_known_seen(
                    self.events[camera_id][time_ev],
                    home_id,
                ):
                    break

            return seen

        return _someone_known_seen(self.last_event[camera_id], home_id)

    def someone_unknown_seen(self, camera_id: str, exclude: int = 0) -> bool:
        """Evaluate if someone known has been seen."""
        if camera_id not in self.events:
            raise NoDevice

        if (home_id := self.get_camera_home_id(camera_id)) is None:
            raise NoDevice

        def _someone_unknown_seen(event: dict, home_id: str) -> bool:
            return event["type"] == "person" and event[
                "person_id"
            ] not in self._known_persons(home_id)

        if exclude:
            limit = time.time() - exclude
            array_time_event = sorted(self.events[camera_id], reverse=True)
            seen = False

            for time_ev in array_time_event:
                if time_ev < limit:
                    continue

                if seen := _someone_unknown_seen(
                    self.events[camera_id][time_ev],
                    home_id,
                ):
                    break

            return seen

        return _someone_unknown_seen(self.last_event[camera_id], home_id)

    def motion_detected(self, camera_id: str, exclude: int = 0) -> bool:
        """Evaluate if movement has been detected."""
        if camera_id not in self.events:
            raise NoDevice

        if exclude:
            limit = time.time() - exclude
            array_time_event = sorted(self.events[camera_id], reverse=True)

            for time_ev in array_time_event:
                if time_ev < limit:
                    return False

                if self.events[camera_id][time_ev]["type"] == "movement":
                    return True

        elif self.last_event[camera_id]["type"] == "movement":
            return True

        return False

    def outdoor_motion_detected(self, camera_id: str, offset: int = 0) -> bool:
        """Evaluate if outdoor movement has been detected."""
        if camera_id not in self.last_event:
            return False

        last_event = self.last_event[camera_id]
        return (
            last_event["type"] == "movement"
            and last_event["video_status"] == "recording"
            and last_event["time"] + offset > int(time.time())
        )

    def _object_detected(self, object_name: str, camera_id: str, offset: int) -> bool:
        """Evaluate if an object has been detected."""
        if self.outdoor_last_event[camera_id]["video_status"] == "recording":
            for event in self.outdoor_last_event[camera_id]["event_list"]:
                if event["type"] == object_name and (
                    event["time"] + offset > int(time.time())
                ):
                    return True

        return False

    def human_detected(self, camera_id: str, offset: int = 0) -> bool:
        """Evaluate if a human has been detected."""
        return self._object_detected("human", camera_id, offset)

    def animal_detected(self, camera_id: str, offset: int = 0) -> bool:
        """Evaluate if an animal has been detected."""
        return self._object_detected("animal", camera_id, offset)

    def car_detected(self, camera_id: str, offset: int = 0) -> bool:
        """Evaluate if a car has been detected."""
        return self._object_detected("vehicle", camera_id, offset)

    def module_motion_detected(
        self,
        module_id: str,
        camera_id: str,
        exclude: int = 0,
    ) -> bool:
        """Evaluate if movement has been detected."""
        if exclude:
            limit = time.time() - exclude
            array_time_event = sorted(self.events.get(camera_id, []), reverse=True)

            for time_ev in array_time_event:
                if time_ev < limit:
                    return False

                curr_event = self.events[camera_id][time_ev]
                if (
                    curr_event["type"] in {"tag_big_move", "tag_small_move"}
                    and curr_event["module_id"] == module_id
                ):
                    return True

        else:
            if camera_id not in self.last_event:
                return False

            curr_event = self.last_event[camera_id]
            if (
                curr_event["type"] in {"tag_big_move", "tag_small_move"}
                and curr_event["module_id"] == module_id
            ):
                return True

        return False

    def module_opened(self, module_id: str, camera_id: str, exclude: int = 0) -> bool:
        """Evaluate if module status is open."""
        if exclude:
            limit = time.time() - exclude
            array_time_event = sorted(self.events.get(camera_id, []), reverse=True)

            for time_ev in array_time_event:
                if time_ev < limit:
                    return False

                curr_event = self.events[camera_id][time_ev]
                if (
                    curr_event["type"] == "tag_open"
                    and curr_event["module_id"] == module_id
                ):
                    return True

        else:
            if camera_id not in self.last_event:
                return False

            curr_event = self.last_event[camera_id]
            if (
                curr_event["type"] == "tag_open"
                and curr_event["module_id"] == module_id
            ):
                return True

        return False

    def build_state_params(
        self,
        camera_id: str,
        home_id: str | None,
        floodlight: str | None,
        monitoring: str | None,
    ):
        """Build camera state parameters."""
        if home_id is None:
            home_id = self.get_camera(camera_id)["home_id"]

        module = {"id": camera_id}

        if floodlight:
            param, val = "floodlight", floodlight.lower()
            if val not in {"on", "off", "auto"}:
                LOG.error("Invalid value for floodlight")
            else:
                module[param] = val

        if monitoring:
            param, val = "monitoring", monitoring.lower()
            if val not in {"on", "off"}:
                LOG.error("Invalid value for monitoring")
            else:
                module[param] = val

        return {"id": home_id, "modules": [module]}


class CameraData(AbstractCameraData):
    """Class of Netatmo camera data."""

    def __init__(self, auth: NetatmoOAuth2) -> None:
        """Initialize the Netatmo camera data.

        Arguments:
            auth {NetatmoOAuth2} -- Authentication information with valid access token
        """
        self.auth = auth

    def update(self, events: int = 30) -> None:
        """Fetch and process data from API."""
        resp = self.auth.post_api_request(
            endpoint=GETHOMEDATA_ENDPOINT,
            params={"size": events},
        )

        self.raw_data = extract_raw_data(resp.json(), "homes")
        self.process()
        self._update_all_camera_urls()
        self._store_last_event()

    def _update_all_camera_urls(self) -> None:
        """Update all camera urls."""
        for home_id in self.homes:
            for camera_id in self.cameras[home_id]:
                self.update_camera_urls(camera_id)

    def update_camera_urls(self, camera_id: str) -> None:
        """Update and validate the camera urls."""
        camera_data = self.get_camera(camera_id)
        home_id = camera_data["home_id"]

        if not camera_data or camera_data.get("status") == "disconnected":
            self.cameras[home_id][camera_id]["local_url"] = None
            self.cameras[home_id][camera_id]["vpn_url"] = None
            return

        if (vpn_url := camera_data.get("vpn_url")) and camera_data.get("is_local"):
            if temp_local_url := self._check_url(vpn_url):
                self.cameras[home_id][camera_id]["local_url"] = self._check_url(
                    temp_local_url,
                )

    def _check_url(self, url: str) -> str | None:
        try:
            resp = self.auth.post_request(url=f"{url}/command/ping").json()
        except ReadTimeout:
            LOG.debug("Timeout validation of camera url %s", url)
            return None
        except ApiError:
            LOG.debug("Api error for camera url %s", url)
            return None

        return resp.get("local_url") if resp else None

    def set_state(
        self,
        camera_id: str,
        home_id: str = None,
        floodlight: str = None,
        monitoring: str = None,
    ) -> bool:
        """Turn camera (light) on/off.

        Arguments:
            camera_id {str} -- ID of a camera
            home_id {str} -- ID of a home
            floodlight {str} -- Mode for floodlight (on/off/auto)
            monitoring {str} -- Mode for monitoring (on/off)

        Returns:
            Boolean -- Success of the request
        """
        post_params = {
            "json": {
                "home": self.build_state_params(
                    camera_id,
                    home_id,
                    floodlight,
                    monitoring,
                ),
            },
        }

        try:
            resp = self.auth.post_api_request(
                endpoint=SETSTATE_ENDPOINT,
                params=post_params,
            ).json()
        except ApiError as err_msg:
            LOG.error("%s", err_msg)
            return False

        if "error" in resp:
            LOG.debug("%s", resp)
            return False

        LOG.debug("%s", resp)
        return True

    def set_persons_home(self, home_id: str, person_ids: list[str] = None):
        """Mark persons as home."""
        post_params: dict[str, str | list] = {"home_id": home_id}
        if person_ids:
            post_params["person_ids[]"] = person_ids
        return self.auth.post_api_request(
            endpoint=SETPERSONSHOME_ENDPOINT,
            params=post_params,
        ).json()

    def set_persons_away(self, home_id: str, person_id: str | None = None):
        """Mark a person as away or set the whole home to being empty."""
        post_params = {"home_id": home_id, "person_id": person_id}
        return self.auth.post_api_request(
            endpoint=SETPERSONSAWAY_ENDPOINT,
            params=post_params,
        ).json()

    def get_camera_picture(
        self,
        image_id: str,
        key: str,
    ) -> tuple[bytes, str | None]:
        """Download a specific image (of an event or user face) from the camera."""
        post_params = {"image_id": image_id, "key": key}
        resp = self.auth.post_api_request(
            endpoint=GETCAMERAPICTURE_ENDPOINT,
            params=post_params,
        ).content
        image_type = imghdr.what("NONE.FILE", resp)
        return resp, image_type

    def get_profile_image(
        self,
        name: str,
        home_id: str,
    ) -> tuple[bytes | None, str | None]:
        """Retrieve the face of a given person."""
        for person in self.persons[home_id].values():
            if name == person.get("pseudo"):
                image_id = person["face"]["id"]
                key = person["face"]["key"]
                return self.get_camera_picture(image_id, key)

        return None, None

    def update_events(
        self,
        home_id: str,
        event_id: str = None,
        device_type: str = None,
    ) -> None:
        """Update the list of events."""
        if not (event_id or device_type):
            raise ApiError

        post_params = {
            "home_id": home_id,
            "event_id": self.build_event_id(event_id, device_type),
        }

        event_list: list = []
        resp: dict[str, Any] | None = None
        try:
            resp = self.auth.post_api_request(
                endpoint=GETEVENTSUNTIL_ENDPOINT,
                params=post_params,
            ).json()
            if resp is not None:
                event_list = resp["body"]["events_list"]
        except ApiError:
            pass
        except KeyError:
            if resp is not None:
                LOG.debug("event_list response: %s", resp)
                LOG.debug("event_list body: %s", dict(resp)["body"])
            else:
                LOG.debug("No resp received")

        self._store_events(event_list)
        self._store_last_event()


class AsyncCameraData(AbstractCameraData):
    """Class of Netatmo camera data."""

    def __init__(self, auth: AbstractAsyncAuth) -> None:
        """Initialize the Netatmo camera data.

        Arguments:
            auth {AbstractAsyncAuth} -- Authentication information with valid access token
        """
        self.auth = auth

    async def async_update(self, events: int = 30) -> None:
        """Fetch and process data from API."""
        resp = await self.auth.async_post_api_request(
            endpoint=GETHOMEDATA_ENDPOINT,
            params={"size": events},
        )

        assert not isinstance(resp, bytes)
        self.raw_data = extract_raw_data(await resp.json(), "homes")
        self.process()

        try:
            await self._async_update_all_camera_urls()
        except (aiohttp.ContentTypeError, aiohttp.ClientConnectorError) as err:
            LOG.debug("One or more camera could not be reached. (%s)", err)

        self._store_last_event()

    async def _async_update_all_camera_urls(self) -> None:
        """Update all camera urls."""
        for home_id in self.homes:
            for camera_id in self.cameras[home_id]:
                await self.async_update_camera_urls(camera_id)

    async def async_set_state(
        self,
        camera_id: str,
        home_id: str = None,
        floodlight: str = None,
        monitoring: str = None,
    ) -> bool:
        """Turn camera (light) on/off.

        Arguments:
            camera_id {str} -- ID of a camera
            home_id {str} -- ID of a home
            floodlight {str} -- Mode for floodlight (on/off/auto)
            monitoring {str} -- Mode for monitoring (on/off)

        Returns:
            Boolean -- Success of the request
        """
        post_params = {
            "json": {
                "home": self.build_state_params(
                    camera_id,
                    home_id,
                    floodlight,
                    monitoring,
                ),
            },
        }

        try:
            resp = await self.auth.async_post_api_request(
                endpoint=SETSTATE_ENDPOINT,
                params=post_params,
            )
        except ApiError as err_msg:
            LOG.error("%s", err_msg)
            return False

        assert not isinstance(resp, bytes)
        resp_data = await resp.json()

        if "error" in resp_data:
            LOG.debug("%s", resp_data)
            return False

        LOG.debug("%s", resp_data)
        return True

    async def async_update_camera_urls(self, camera_id: str) -> None:
        """Update and validate the camera urls."""
        camera_data = self.get_camera(camera_id)
        home_id = camera_data["home_id"]

        if not camera_data or camera_data.get("status") == "disconnected":
            self.cameras[home_id][camera_id]["local_url"] = None
            self.cameras[home_id][camera_id]["vpn_url"] = None
            return

        if (vpn_url := camera_data.get("vpn_url")) and camera_data.get("is_local"):
            temp_local_url = await self._async_check_url(vpn_url)
            if temp_local_url:
                self.cameras[home_id][camera_id][
                    "local_url"
                ] = await self._async_check_url(
                    temp_local_url,
                )

    async def _async_check_url(self, url: str) -> str | None:
        """Validate camera url."""
        try:
            resp = await self.auth.async_post_request(url=f"{url}/command/ping")
        except ReadTimeout:
            LOG.debug("Timeout validation of camera url %s", url)
            return None
        except ApiError:
            LOG.debug("Api error for camera url %s", url)
            return None

        assert not isinstance(resp, bytes)
        resp_data = await resp.json()
        return resp_data.get("local_url") if resp_data else None

    async def async_set_persons_home(
        self,
        home_id: str,
        person_ids: list[str] = None,
    ):
        """Mark persons as home."""
        post_params: dict[str, str | list] = {"home_id": home_id}
        if person_ids:
            post_params["person_ids[]"] = person_ids
        return await self.auth.async_post_api_request(
            endpoint=SETPERSONSHOME_ENDPOINT,
            params=post_params,
        )

    async def async_set_persons_away(self, home_id: str, person_id: str | None = None):
        """Mark a person as away or set the whole home to being empty."""
        post_params = {"home_id": home_id}
        if person_id:
            post_params["person_id"] = person_id
        return await self.auth.async_post_api_request(
            endpoint=SETPERSONSAWAY_ENDPOINT,
            params=post_params,
        )

    async def async_get_live_snapshot(self, camera_id: str) -> bytes | None:
        """Retrieve live snapshot from camera."""
        local, vpn = self.camera_urls(camera_id)
        if not local and not vpn:
            return None
        resp = await self.auth.async_get_image(
            endpoint=f"{(local or vpn)}/live/snapshot_720.jpg",
            timeout=10,
        )

        return resp if isinstance(resp, bytes) else None

    async def async_get_camera_picture(
        self,
        image_id: str,
        key: str,
    ) -> tuple[bytes, str | None]:
        """Download a specific image (of an event or user face) from the camera."""
        post_params = {"image_id": image_id, "key": key}
        resp = await self.auth.async_get_image(
            endpoint=GETCAMERAPICTURE_ENDPOINT,
            params=post_params,
        )

        return (
            (resp, imghdr.what("NONE.FILE", resp))
            if isinstance(resp, bytes)
            else (b"", None)
        )

    async def async_get_profile_image(
        self,
        name: str,
        home_id: str,
    ) -> tuple[bytes | None, str | None]:
        """Retrieve the face of a given person."""
        for person in self.persons[home_id].values():
            if name == person.get("pseudo"):
                image_id = person["face"]["id"]
                key = person["face"]["key"]
                return await self.async_get_camera_picture(image_id, key)

        return None, None
