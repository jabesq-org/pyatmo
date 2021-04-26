"""Support for Netatmo security devices (cameras, smoke detectors, sirens, window sensors, events and persons)."""
import imghdr
import time
from abc import ABC
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from requests.exceptions import ReadTimeout

from .auth import AbstractAsyncAuth, NetatmoOAuth2
from .exceptions import ApiError, NoDevice
from .helpers import _BASE_URL, LOG

_GETHOMEDATA_REQ = _BASE_URL + "api/gethomedata"
_GETCAMERAPICTURE_REQ = _BASE_URL + "api/getcamerapicture"
_GETEVENTSUNTIL_REQ = _BASE_URL + "api/geteventsuntil"
_SETPERSONSAWAY_REQ = _BASE_URL + "api/setpersonsaway"
_SETPERSONSHOME_REQ = _BASE_URL + "api/setpersonshome"
_SETSTATE_REQ = _BASE_URL + "api/setstate"


class AbstractCameraData(ABC):
    """Abstract class of Netatmo camera data."""

    raw_data: Dict = defaultdict(dict)
    homes: Dict = defaultdict(dict)
    persons: Dict = {}
    events: Dict = defaultdict(dict)
    outdoor_events: Dict = defaultdict(dict)
    cameras: Dict = defaultdict(dict)
    smoke_detectors: Dict = defaultdict(dict)
    modules: Dict = {}
    last_event: Dict = {}
    outdoor_last_event: Dict = {}
    types: Dict = defaultdict(dict)

    def process(self) -> None:
        """Process data from API."""
        self.homes = {d["id"]: d for d in self.raw_data}

        for item in self.raw_data:
            home_id: str = item.get("id", "")

            if not item.get("name"):
                self.homes[home_id]["name"] = "Unknown"

            for person in item.get("persons", []):
                self.persons[person["id"]] = person

            for event in item.get("events", []):
                self._store_events(event)

            for camera in item.get("cameras", []):
                self.cameras[home_id][camera["id"]] = camera
                self.types[home_id][camera["type"]] = camera

                self.cameras[home_id][camera["id"]]["home_id"] = home_id
                if camera["type"] == "NACamera":
                    for module in camera.get("modules", []):
                        self.modules[module["id"]] = module
                        self.modules[module["id"]]["cam_id"] = camera["id"]

            for smoke in item.get("smokedetectors", []):
                self.smoke_detectors[home_id][smoke["id"]] = smoke
                self.types[home_id][smoke["type"]] = smoke

    def _store_events(self, event):
        if event["type"] == "outdoor":
            self.outdoor_events[event["camera_id"]][event["time"]] = event

        else:
            self.events[event["camera_id"]][event["time"]] = event

    def _store_last_event(self):
        for camera in self.events:
            self.last_event[camera] = self.events[camera][
                sorted(self.events[camera])[-1]
            ]

        for camera in self.outdoor_events:
            self.outdoor_last_event[camera] = self.outdoor_events[camera][
                sorted(self.outdoor_events[camera])[-1]
            ]

    def get_camera(self, camera_id: str) -> Dict[str, str]:
        """Get camera data."""
        for home_id in self.cameras:
            if camera_id in self.cameras[home_id]:
                return self.cameras[home_id][camera_id]

        return {}

    def get_module(self, module_id: str) -> Optional[dict]:
        """Get module data."""
        return None if module_id not in self.modules else self.modules[module_id]

    def get_smokedetector(self, smoke_id: str) -> Optional[dict]:
        """Get smoke detector."""
        for home_id in self.smoke_detectors:
            if smoke_id in self.smoke_detectors[home_id]:
                return self.smoke_detectors[home_id][smoke_id]

        return None

    def camera_urls(self, camera_id: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Return the vpn_url and the local_url (if available) of a given camera
        in order to access its live feed.
        """
        camera_data = self.get_camera(camera_id)
        return camera_data.get("vpn_url", None), camera_data.get("local_url", None)

    def get_light_state(self, camera_id: str) -> Optional[str]:
        """Return the current mode of the floodlight of a presence camera."""
        camera_data = self.get_camera(camera_id)
        if camera_data is None:
            raise ValueError("Invalid Camera ID")

        return camera_data.get("light_mode_status")

    def persons_at_home(self, home_id: str = None) -> List:
        """Return a list of known persons who are currently at home."""
        home_data = self.homes.get(home_id, {})
        return [
            person["pseudo"]
            for person in home_data.get("persons")
            if "pseudo" in person and not person["out_of_sight"]
        ]

    def get_person_id(self, name: str) -> Optional[str]:
        """Retrieve the ID of a person."""
        for pid, data in self.persons.items():
            if name == data.get("pseudo"):
                return pid

        return None

    def build_event_id(self, event_id: Optional[str], device_type: Optional[str]):
        """Build event id."""

        def get_event_id(data: Dict):
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
        # Check in the last event is someone known has been seen
        def _person_in_event(curr_event, person_name):
            if curr_event["type"] == "person":
                person_id = curr_event["person_id"]

                if self.persons[person_id].get("pseudo") == person_name:
                    return True
            return None

        if exclude:
            limit = time.time() - exclude
            array_time_event = sorted(self.events[camera_id], reverse=True)

            for time_ev in array_time_event:
                if time_ev < limit:
                    return False

                current_event = self.events[camera_id][time_ev]
                if _person_in_event(current_event, name) is True:
                    return True

            return False

        current_event = self.last_event[camera_id]
        if _person_in_event(current_event, name) is True:
            return True

        return False

    def _known_persons(self) -> Dict[str, Dict]:
        """Return all known persons."""
        return {pid: p for pid, p in self.persons.items() if "pseudo" in p}

    def known_persons(self) -> Dict[str, str]:
        """Return a dictionary of known person names."""
        return {pid: p["pseudo"] for pid, p in self._known_persons().items()}

    def known_persons_names(self) -> List[str]:
        """Return a list of known person names."""
        return [person["pseudo"] for person in self._known_persons().values()]

    def someone_known_seen(self, camera_id: str, exclude: int = 0) -> bool:
        """Evaluate if someone known has been seen."""
        if camera_id not in self.events:
            raise NoDevice

        if exclude:
            limit = time.time() - exclude
            array_time_event = sorted(self.events[camera_id], reverse=True)

            for time_ev in array_time_event:
                if time_ev < limit:
                    return False

                curr_event = self.events[camera_id][time_ev]
                if curr_event["type"] == "person":
                    if curr_event["person_id"] in self._known_persons():
                        return True

        # Check in the last event if someone known has been seen
        else:
            curr_event = self.last_event[camera_id]
            if curr_event["type"] == "person":
                if curr_event["person_id"] in self._known_persons():
                    return True

        return False

    def someone_unknown_seen(self, camera_id: str, exclude: int = 0) -> bool:
        """Evaluate if someone known has been seen."""
        if camera_id not in self.events:
            raise NoDevice

        if exclude:
            limit = time.time() - exclude
            array_time_event = sorted(self.events[camera_id], reverse=True)

            for time_ev in array_time_event:
                if time_ev < limit:
                    return False

                curr_event = self.events[camera_id][time_ev]
                if curr_event["type"] == "person":
                    if curr_event["person_id"] not in self._known_persons():
                        return True

        # Check in the last event is noone known has been seen
        else:
            curr_event = self.last_event[camera_id]
            if curr_event["type"] == "person":
                if curr_event["person_id"] not in self._known_persons():
                    return True

        return False

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
        """Evaluate if a human has been detected."""
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
        home_id: Optional[str],
        floodlight: Optional[str],
        monitoring: Optional[str],
    ):
        """."""
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
            auth {NetatmoOAuth2} -- Authentication information with a valid access token
        """
        self.auth = auth

    def update(self, events: int = 30) -> None:
        """Fetch and process data from API."""
        resp = self.auth.post_request(url=_GETHOMEDATA_REQ, params={"size": events})
        if resp is None or "body" not in resp:
            raise NoDevice("No device data returned by Netatmo server")

        self.raw_data = resp["body"].get("homes")
        if not self.raw_data:
            raise NoDevice("No device data available")

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

        vpn_url = camera_data.get("vpn_url")
        if vpn_url and camera_data.get("is_local"):

            def check_url(url: str) -> Optional[str]:
                try:
                    resp = self.auth.post_request(url=f"{url}/command/ping")
                except ReadTimeout:
                    LOG.debug("Timeout validation of camera url %s", url)
                    return None
                except ApiError:
                    LOG.debug("Api error for camera url %s", url)
                    return None

                return resp.get("local_url") if resp else None

            temp_local_url = check_url(vpn_url)
            if temp_local_url:
                self.cameras[home_id][camera_id]["local_url"] = check_url(
                    temp_local_url,
                )

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
            resp = self.auth.post_request(url=_SETSTATE_REQ, params=post_params)
        except ApiError as err_msg:
            LOG.error("%s", err_msg)
            return False

        if "error" in resp:
            LOG.debug("%s", resp)
            return False

        LOG.debug("%s", resp)
        return True

    def set_persons_home(self, person_ids: List[str], home_id: str):
        """Mark persons as home."""
        post_params = {"home_id": home_id, "person_ids[]": person_ids}
        return self.auth.post_request(url=_SETPERSONSHOME_REQ, params=post_params)

    def set_persons_away(self, person_id: str, home_id: str):
        """Mark a person as away or set the whole home to being empty."""
        post_params = {"home_id": home_id, "person_id": person_id}
        return self.auth.post_request(url=_SETPERSONSAWAY_REQ, params=post_params)

    def get_camera_picture(
        self,
        image_id: str,
        key: str,
    ) -> Tuple[bytes, Optional[str]]:
        """Download a specific image (of an event or user face) from the camera."""
        post_params = {"image_id": image_id, "key": key}
        resp = self.auth.post_request(url=_GETCAMERAPICTURE_REQ, params=post_params)
        image_type = imghdr.what("NONE.FILE", resp)
        return resp, image_type

    def get_profile_image(self, name: str) -> Tuple[Optional[bytes], Optional[str]]:
        """Retrieve the face of a given person."""
        for person in self.persons:
            if name == self.persons[person].get("pseudo"):
                image_id = self.persons[person]["face"]["id"]
                key = self.persons[person]["face"]["key"]
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

        event_list: List = []
        resp: Optional[Dict[str, Any]] = None
        try:
            resp = self.auth.post_request(url=_GETEVENTSUNTIL_REQ, params=post_params)
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

        for event in event_list:
            self._store_events(event)

        self._store_last_event()


class AsyncCameraData(AbstractCameraData):
    """Class of Netatmo camera data."""

    def __init__(self, auth: AbstractAsyncAuth) -> None:
        """Initialize the Netatmo camera data.

        Arguments:
            auth {AbstractAsyncAuth} -- Authentication information with a valid access token
        """
        self.auth = auth

    async def async_update(self, events: int = 30) -> None:
        """Fetch and process data from API."""
        resp = await self.auth.async_post_request(
            url=_GETHOMEDATA_REQ,
            params={"size": events},
        )
        if resp is None or "body" not in resp:
            raise NoDevice("No device data returned by Netatmo server")

        self.raw_data = resp["body"].get("homes")
        if not self.raw_data:
            raise NoDevice("No device data available")

        self.process()
        await self._async_update_all_camera_urls()
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
            resp = await self.auth.async_post_request(
                url=_SETSTATE_REQ,
                params=post_params,
            )
        except ApiError as err_msg:
            LOG.error("%s", err_msg)
            return False

        if "error" in resp:
            LOG.debug("%s", resp)
            return False

        LOG.debug("%s", resp)
        return True

    async def async_update_camera_urls(self, camera_id: str) -> None:
        """Update and validate the camera urls."""
        camera_data = self.get_camera(camera_id)
        home_id = camera_data["home_id"]

        if not camera_data or camera_data.get("status") == "disconnected":
            self.cameras[home_id][camera_id]["local_url"] = None
            self.cameras[home_id][camera_id]["vpn_url"] = None
            return

        vpn_url = camera_data.get("vpn_url")
        if vpn_url and camera_data.get("is_local"):

            async def async_check_url(url: str) -> Optional[str]:
                try:
                    resp = await self.auth.async_post_request(url=f"{url}/command/ping")
                except ReadTimeout:
                    LOG.debug("Timeout validation of camera url %s", url)
                    return None
                except ApiError:
                    LOG.debug("Api error for camera url %s", url)
                    return None

                return resp.get("local_url") if resp else None

            temp_local_url = await async_check_url(vpn_url)
            if temp_local_url:
                self.cameras[home_id][camera_id]["local_url"] = await async_check_url(
                    temp_local_url,
                )

    async def async_set_persons_home(self, person_ids: List[str], home_id: str):
        """Mark persons as home."""
        post_params = {"home_id": home_id, "person_ids[]": person_ids}
        return await self.auth.async_post_request(
            url=_SETPERSONSHOME_REQ,
            params=post_params,
        )

    async def async_set_persons_away(self, person_id: str, home_id: str):
        """Mark a person as away or set the whole home to being empty."""
        post_params = {"home_id": home_id, "person_id": person_id}
        return await self.auth.async_post_request(
            url=_SETPERSONSAWAY_REQ,
            params=post_params,
        )

    async def async_get_live_snapshot(self, camera_id: str):
        """Retrieve live snapshot from camera."""
        local, vpn = self.camera_urls(camera_id)
        if not local and not vpn:
            return None
        return await self.auth.async_post_request(
            url=f"{(local or vpn)}/live/snapshot_720.jpg",
            timeout=10,
        )

    async def async_get_camera_picture(
        self,
        image_id: str,
        key: str,
    ) -> Tuple[bytes, Optional[str]]:
        """Download a specific image (of an event or user face) from the camera."""
        post_params = {"image_id": image_id, "key": key}
        resp = await self.auth.async_post_request(
            url=_GETCAMERAPICTURE_REQ,
            params=post_params,
        )
        image_type = imghdr.what("NONE.FILE", resp)
        return resp, image_type

    async def async_get_profile_image(
        self,
        name: str,
    ) -> Tuple[Optional[bytes], Optional[str]]:
        """Retrieve the face of a given person."""
        for person in self.persons:
            if name == self.persons[person].get("pseudo"):
                image_id = self.persons[person]["face"]["id"]
                key = self.persons[person]["face"]["key"]
                return await self.async_get_camera_picture(image_id, key)

        return None, None
