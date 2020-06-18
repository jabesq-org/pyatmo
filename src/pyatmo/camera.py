import imghdr
import time
from typing import Dict, List, Optional, Tuple

from requests.exceptions import ReadTimeout

from .auth import NetatmoOAuth2
from .exceptions import ApiError, NoDevice
from .helpers import _BASE_URL, LOG

_GETHOMEDATA_REQ = _BASE_URL + "api/gethomedata"
_GETCAMERAPICTURE_REQ = _BASE_URL + "api/getcamerapicture"
_GETEVENTSUNTIL_REQ = _BASE_URL + "api/geteventsuntil"
_SETPERSONSAWAY_REQ = _BASE_URL + "api/setpersonsaway"
_SETPERSONSHOME_REQ = _BASE_URL + "api/setpersonshome"
_SETSTATE_REQ = _BASE_URL + "api/setstate"


class CameraData:
    """
    Class of Netatmo camera informations
        (Homes, cameras, smoke detectors, modules, events, persons)
    """

    def __init__(self, auth: NetatmoOAuth2, size: int = 30) -> None:
        """Initialize self.

        Arguments:
            auth {NetatmoOAuth2} -- Authentication information with a valid access token

        Keyword Arguments:
            size {int} -- Number of events to retrieve. (default: {30})

        Raises:
            NoDevice: No devices found.
        """
        self.auth = auth

        post_params = {"size": size}
        resp = self.auth.post_request(url=_GETHOMEDATA_REQ, params=post_params)
        if resp is None or "body" not in resp:
            raise NoDevice("No device data returned by Netatmo server")

        self.raw_data = resp["body"].get("homes")
        if not self.raw_data:
            raise NoDevice("No device data available")

        self.homes: Dict = {d["id"]: d for d in self.raw_data}

        self.persons: Dict = {}
        self.events: Dict = {}
        self.outdoor_events: Dict = {}
        self.cameras: Dict = {}
        self.smokedetectors: Dict = {}
        self.modules: Dict = {}
        self.last_event: Dict = {}
        self.outdoor_last_event: Dict = {}
        self.types: Dict = {}

        for item in self.raw_data:
            home_id: str = item.get("id")
            home_name: str = item.get("name")

            if not home_name:
                home_name = "Unknown"
                self.homes[home_id]["name"] = home_name

            if home_id not in self.cameras:
                self.cameras[home_id] = {}

            if home_id not in self.smokedetectors:
                self.smokedetectors[home_id] = {}

            if home_id not in self.types:
                self.types[home_id] = {}

            for person in item["persons"]:
                self.persons[person["id"]] = person

            if "events" in item:
                for event in item["events"]:
                    if event["type"] == "outdoor":
                        if event["camera_id"] not in self.outdoor_events:
                            self.outdoor_events[event["camera_id"]] = {}
                        self.outdoor_events[event["camera_id"]][event["time"]] = event

                    else:
                        if event["camera_id"] not in self.events:
                            self.events[event["camera_id"]] = {}
                        self.events[event["camera_id"]][event["time"]] = event

            for camera in item["cameras"]:
                self.cameras[home_id][camera["id"]] = camera
                self.cameras[home_id][camera["id"]]["home_id"] = home_id

                if camera["type"] == "NACamera" and "modules" in camera:
                    for module in camera["modules"]:
                        self.modules[module["id"]] = module
                        self.modules[module["id"]]["cam_id"] = camera["id"]

            for smoke in item["smokedetectors"]:
                self.smokedetectors[home_id][smoke["id"]] = smoke

            for camera_type in item["cameras"]:
                self.types[home_id][camera_type["type"]] = camera_type

            for smoke_type in item["smokedetectors"]:
                self.types[home_id][smoke_type["type"]] = smoke_type

        for camera in self.events:
            self.last_event[camera] = self.events[camera][
                sorted(self.events[camera])[-1]
            ]

        for camera in self.outdoor_events:
            self.outdoor_last_event[camera] = self.outdoor_events[camera][
                sorted(self.outdoor_events[camera])[-1]
            ]

        for home_id in self.homes:
            for camera_id in self.cameras[home_id]:
                self.update_camera_urls(camera_id)

    def get_camera(self, camera_id: str) -> Dict[str, str]:
        """Get camera data."""
        for home_id, _ in self.cameras.items():
            if camera_id in self.cameras[home_id]:
                return self.cameras[home_id][camera_id]

        return {}

    def get_module(self, module_id: str) -> Optional[dict]:
        """Get module data."""
        return None if module_id not in self.modules else self.modules[module_id]

    def get_smokedetector(self, smoke_id: str) -> Optional[dict]:
        """Get smoke detector."""
        for home_id, _ in self.smokedetectors.items():
            if smoke_id in self.smokedetectors[home_id]:
                return self.smokedetectors[home_id][smoke_id]

        return None

    def camera_urls(self, camera_id: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Return the vpn_url and the local_url (if available) of a given camera
        in order to access its live feed.
        """
        camera_data = self.get_camera(camera_id)
        return camera_data.get("vpn_url", None), camera_data.get("local_url", None)

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
                else:
                    return resp.get("local_url")

            temp_local_url = check_url(vpn_url)
            if temp_local_url:
                self.cameras[home_id][camera_id]["local_url"] = check_url(
                    temp_local_url
                )

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

    def set_persons_home(self, person_ids: List[str], home_id: str):
        """Mark persons as home.

        Arguments:
            person_ids {list} -- IDs of persons
            home_id {str} -- ID of a home
        """
        post_params = {
            "home_id": home_id,
            "person_ids[]": person_ids,
        }
        return self.auth.post_request(url=_SETPERSONSHOME_REQ, params=post_params)

    def set_persons_away(self, person_id: str, home_id: str):
        """Mark a person as away or set the whole home to being empty.

        Arguments:
            person_id {str} -- ID of a person
            home_id {str} -- ID of a home
        """
        post_params = {
            "home_id": home_id,
            "person_id": person_id,
        }
        return self.auth.post_request(url=_SETPERSONSAWAY_REQ, params=post_params)

    def get_person_id(self, name: str) -> Optional[str]:
        """Retrieve the ID of a person.

        Arguments:
            name {str} -- Name of a person

        Returns:
            str -- ID of a person
        """
        for pid, data in self.persons.items():
            if "pseudo" in data and name == data["pseudo"]:
                return pid

        return None

    def get_camera_picture(
        self, image_id: str, key: str
    ) -> Tuple[bytes, Optional[str]]:
        """Download a specific image (of an event or user face) from the camera."""
        post_params = {
            "image_id": image_id,
            "key": key,
        }
        resp = self.auth.post_request(url=_GETCAMERAPICTURE_REQ, params=post_params)
        image_type = imghdr.what("NONE.FILE", resp)
        return resp, image_type

    def get_profile_image(self, name: str) -> Tuple[Optional[bytes], Optional[str]]:
        """Retrieve the face of a given person."""
        for person in self.persons:
            if (
                "pseudo" in self.persons[person]
                and name == self.persons[person]["pseudo"]
            ):
                image_id = self.persons[person]["face"]["id"]
                key = self.persons[person]["face"]["key"]
                return self.get_camera_picture(image_id, key)

        return None, None

    def update_events(
        self, home_id: str, event_id: str = None, device_type: str = None
    ) -> None:
        """Update the list of events."""
        # Either event_id or device_type must be given
        if not (event_id or device_type):
            raise ApiError

        def get_event_id(data: Dict):
            events = {e["time"]: e for e in data.values()}
            return min(events.items())[1].get("id")

        if device_type == "NACamera":
            # for the Welcome camera
            if not event_id:
                # If no event is provided we need to retrieve the oldest of
                # the last event seen by each camera
                event_id = get_event_id(self.last_event)

        elif device_type == "NOC":
            # for the Presence camera
            if not event_id:
                # If no event is provided we need to retrieve the oldest of
                # the last event seen by each camera
                event_id = get_event_id(self.outdoor_last_event)

        elif device_type == "NSD":
            # for the smoke detector
            if not event_id:
                # If no event is provided we need to retrieve the oldest of
                # the last event by each smoke detector
                event_id = get_event_id(self.outdoor_last_event)

        post_params = {
            "home_id": home_id,
            "event_id": event_id,
        }

        try:
            resp = self.auth.post_request(url=_GETEVENTSUNTIL_REQ, params=post_params)
            event_list = resp["body"]["events_list"]
        except ApiError:
            pass
        except KeyError:
            LOG.debug("event_list response: %s", resp)
            LOG.debug("event_list body: %s", resp["body"])

        for event in event_list:
            if event["type"] == "outdoor":
                if event["camera_id"] not in self.outdoor_events:
                    self.outdoor_events[event["camera_id"]] = {}
                self.outdoor_events[event["camera_id"]][event["time"]] = event

            else:
                if event["camera_id"] not in self.events:
                    self.events[event["camera_id"]] = {}
                self.events[event["camera_id"]][event["time"]] = event

        for camera in self.events:
            self.last_event[camera] = self.events[camera][
                sorted(self.events[camera])[-1]
            ]

        for camera in self.outdoor_events:
            self.outdoor_last_event[camera] = self.outdoor_events[camera][
                sorted(self.outdoor_events[camera])[-1]
            ]

    def person_seen_by_camera(
        self, name: str, camera_id: str, exclude: int = 0
    ) -> bool:
        """Evaluate if a specific person has been seen."""
        # Check in the last event is someone known has been seen
        if exclude:
            limit = time.time() - exclude
            array_time_event = sorted(self.events[camera_id], reverse=True)

            for time_ev in array_time_event:
                if time_ev < limit:
                    return False

                if self.events[camera_id][time_ev]["type"] == "person":
                    person_id = self.events[camera_id][time_ev]["person_id"]

                    if (
                        "pseudo" in self.persons[person_id]
                        and self.persons[person_id]["pseudo"] == name
                    ):
                        return True

        elif self.last_event[camera_id]["type"] == "person":
            person_id = self.last_event[camera_id]["person_id"]

            if (
                "pseudo" in self.persons[person_id]
                and self.persons[person_id]["pseudo"] == name
            ):
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

                if self.events[camera_id][time_ev]["type"] == "person":
                    if (
                        self.events[camera_id][time_ev]["person_id"]
                        in self._known_persons()
                    ):
                        return True

        # Check in the last event if someone known has been seen
        elif self.last_event[camera_id]["type"] == "person":

            if self.last_event[camera_id]["person_id"] in self._known_persons():
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

                if self.events[camera_id][time_ev]["type"] == "person":

                    if (
                        self.events[camera_id][time_ev]["person_id"]
                        not in self._known_persons()
                    ):
                        return True

        # Check in the last event is noone known has been seen
        elif self.last_event[camera_id]["type"] == "person":

            if self.last_event[camera_id]["person_id"] not in self._known_persons():
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
        return (
            camera_id in self.last_event
            and self.last_event[camera_id]["type"] == "movement"
            and self.last_event[camera_id]["video_status"] == "recording"
            and self.last_event[camera_id]["time"] + offset > int(time.time())
        )

    def human_detected(self, camera_id: str, offset: int = 0) -> bool:
        """Evaluate if a human has been detected."""
        if self.outdoor_last_event[camera_id]["video_status"] == "recording":
            for event in self.outdoor_last_event[camera_id]["event_list"]:
                if event["type"] == "human" and event["time"] + offset > int(
                    time.time()
                ):
                    return True

        return False

    def animal_detected(self, camera_id: str, offset: int = 0) -> bool:
        """Evaluate if an animal has been detected."""
        if self.outdoor_last_event[camera_id]["video_status"] == "recording":
            for event in self.outdoor_last_event[camera_id]["event_list"]:
                if event["type"] == "animal" and event["time"] + offset > int(
                    time.time()
                ):
                    return True

        return False

    def car_detected(self, camera_id: str, offset: int = 0) -> bool:
        """Evaluate if a car has been detected."""
        if self.outdoor_last_event[camera_id]["video_status"] == "recording":
            for event in self.outdoor_last_event[camera_id]["event_list"]:
                if event["type"] == "vehicle" and event["time"] + offset > int(
                    time.time()
                ):
                    return True

        return False

    def module_motion_detected(
        self, module_id: str, camera_id: str, exclude: int = 0
    ) -> bool:
        """Evaluate if movement has been detected."""
        if exclude:
            limit = time.time() - exclude
            array_time_event = sorted(self.events.get(camera_id, []), reverse=True)

            for time_ev in array_time_event:
                if time_ev < limit:
                    return False

                if (
                    self.events[camera_id][time_ev]["type"]
                    in ["tag_big_move", "tag_small_move"]
                    and self.events[camera_id][time_ev]["module_id"] == module_id
                ):
                    return True

        elif (
            camera_id in self.last_event
            and self.last_event[camera_id]["type"] in ["tag_big_move", "tag_small_move"]
            and self.last_event[camera_id]["module_id"] == module_id
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

                if (
                    self.events[camera_id][time_ev]["type"] == "tag_open"
                    and self.events[camera_id][time_ev]["module_id"] == module_id
                ):
                    return True

        elif camera_id in self.last_event and (
            self.last_event[camera_id]["type"] == "tag_open"
            and self.last_event[camera_id]["module_id"] == module_id
        ):
            return True

        return False

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
        if home_id is None:
            home_id = self.get_camera(camera_id)["home_id"]

        module = {"id": camera_id}

        if floodlight:
            param, val = "floodlight", floodlight.lower()
            if val not in ["on", "off", "auto"]:
                LOG.error("Invalid value for floodlight")
            else:
                module[param] = val

        if monitoring:
            param, val = "monitoring", monitoring.lower()
            if val not in ["on", "off"]:
                LOG.error("Invalid value für monitoring")
            else:
                module[param] = val

        post_params = {
            "json": {"home": {"id": home_id, "modules": [module]}},
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
