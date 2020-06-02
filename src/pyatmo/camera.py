import imghdr
import time
from typing import Dict, Optional, Tuple, Union

from requests.exceptions import ReadTimeout

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
    List of Netatmo camera informations
        (Homes, cameras, smoke detectors, modules, events, persons)
    Args:
        auth (ClientAuth):
            Authentication information with a valid access token
    """

    def __init__(self, auth, size=15):
        self.auth = auth

        post_params = {"size": size}
        resp = self.auth.post_request(url=_GETHOMEDATA_REQ, params=post_params)
        if resp is None or "body" not in resp:
            raise NoDevice("No device data returned by Netatmo server")

        self.raw_data = resp["body"].get("homes")
        if not self.raw_data:
            raise NoDevice("No device data available")

        self.homes = {d["id"]: d for d in self.raw_data}

        self.persons = {}
        self.events = {}
        self.outdoor_events = {}
        self.cameras = {}
        self.smokedetectors = {}
        self.modules = {}
        self.last_event = {}
        self.outdoor_last_event = {}
        self.types = {}

        for item in self.raw_data:
            home_id = item.get("id")
            home_name = item.get("name")
            if not home_name:
                home_name = "Unknown"
                self.homes[home_id]["name"] = home_name
            if home_id not in self.cameras:
                self.cameras[home_id] = {}
            if home_id not in self.smokedetectors:
                self.smokedetectors[home_id] = {}
            if home_id not in self.types:
                self.types[home_id] = {}
            for p in item["persons"]:
                self.persons[p["id"]] = p
            if "events" in item:
                for e in item["events"]:
                    if e["type"] == "outdoor":
                        if e["camera_id"] not in self.outdoor_events:
                            self.outdoor_events[e["camera_id"]] = {}
                        self.outdoor_events[e["camera_id"]][e["time"]] = e
                    elif e["type"] != "outdoor":
                        if e["camera_id"] not in self.events:
                            self.events[e["camera_id"]] = {}
                        self.events[e["camera_id"]][e["time"]] = e
            for c in item["cameras"]:
                self.cameras[home_id][c["id"]] = c
                self.cameras[home_id][c["id"]]["home_id"] = home_id
                if c["type"] == "NACamera" and "modules" in c:
                    for m in c["modules"]:
                        self.modules[m["id"]] = m
                        self.modules[m["id"]]["cam_id"] = c["id"]
            for s in item["smokedetectors"]:
                self.smokedetectors[home_id][s["id"]] = s
            for t in item["cameras"]:
                self.types[home_id][t["type"]] = t
            for t in item["smokedetectors"]:
                self.types[home_id][t["type"]] = t
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

    def get_camera(self, cid: str) -> Dict[str, str]:
        """Get camera data."""
        for home_id, _ in self.cameras.items():
            if cid in self.cameras[home_id]:
                return self.cameras[home_id][cid]
        return {}

    def get_module(self, mid: str):
        """Get module data."""
        return None if mid not in self.modules else self.modules[mid]

    def get_smokedetector(self, sid: str):
        """Get smoke detector."""
        for home, sd in self.smokedetectors.items():
            if sid in self.smokedetectors[home]:
                return self.smokedetectors[home][sid]
        return None

    def camera_urls(self, cid: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Return the vpn_url and the local_url (if available) of a given camera
        in order to access its live feed.
        """
        camera_data = self.get_camera(cid)
        return camera_data.get("vpn_url", None), camera_data.get("local_url", None)

    def update_camera_urls(self, cid: str) -> None:
        """Update and validate the camera urls."""
        camera_data = self.get_camera(cid)
        home_id = camera_data["home_id"]

        if camera_data:
            vpn_url = camera_data.get("vpn_url")
            if vpn_url and camera_data.get("is_local"):

                def check_url(url: str) -> Optional[str]:
                    try:
                        resp = self.auth.post_request(url=f"{url}/command/ping")
                    except (ApiError, ReadTimeout):
                        LOG.debug("Timeout validation of camera url %s", url)
                        return None
                    else:
                        return resp.get("local_url")

                temp_local_url = check_url(vpn_url)
                if temp_local_url:
                    self.cameras[home_id][cid]["local_url"] = check_url(temp_local_url)

    def get_light_state(self, cid: str) -> Optional[str]:
        """Return the current mode of the floodlight of a presence camera."""
        return self.get_camera(cid).get("light_mode_status")

    def persons_at_home(self, home_id=None):
        """Return a list of known persons who are currently at home."""
        home_data = self.homes.get(home_id)
        at_home = []
        for p in home_data["persons"]:
            # Only check known personshome
            if "pseudo" in p:
                if not p["out_of_sight"]:
                    at_home.append(p["pseudo"])
        return at_home

    def set_persons_home(self, person_ids, home_id):
        """Mark persons as home."""
        post_params = {
            "home_id": home_id,
            "person_ids[]": person_ids,
        }
        resp = self.auth.post_request(url=_SETPERSONSHOME_REQ, params=post_params)
        return resp

    def set_persons_away(self, person_id, home_id):
        """Mark a person as away or set the whole home to being empty.

        Arguments:
            person_id {str} -- ID of a person
            home_id {str} -- ID of a home

        Returns:
            [type] -- [description]
        """
        post_params = {
            "home_id": home_id,
            "person_id": person_id,
        }
        resp = self.auth.post_request(url=_SETPERSONSAWAY_REQ, params=post_params)
        return resp

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

    def get_camera_picture(self, image_id: str, key: str):
        """Download a specific image (of an event or user face) from the camera."""
        post_params = {
            "image_id": image_id,
            "key": key,
        }
        resp = self.auth.post_request(url=_GETCAMERAPICTURE_REQ, params=post_params)
        image_type = imghdr.what("NONE.FILE", resp)
        return resp, image_type

    def get_profile_image(self, name: str):
        """Retrieve the face of a given person."""
        for p in self.persons:
            if "pseudo" in self.persons[p]:
                if name == self.persons[p]["pseudo"]:
                    image_id = self.persons[p]["face"]["id"]
                    key = self.persons[p]["face"]["key"]
                    return self.get_camera_picture(image_id, key)

        return None, None

    def update_events(
        self, home_id: str, event_id: str = None, device_type: str = None
    ) -> None:
        """Update the list of events."""
        # Either event_id or device_type must be given
        if not event_id and not device_type:
            raise ApiError

        if device_type == "NACamera":
            # for the Welcome camera
            if not event_id:
                # If no event is provided we need to retrieve the oldest of
                # the last event seen by each camera
                event_list = {}
                for cam_id in self.last_event:
                    event_list[self.last_event[cam_id]["time"]] = self.last_event[
                        cam_id
                    ]
                event_id = event_list[sorted(event_list)[0]]["id"]

        if device_type == "NOC":
            # for the Presence camera
            if not event_id:
                # If no event is provided we need to retrieve the oldest of
                # the last event seen by each camera
                event_list = {}
                for cam_id in self.outdoor_last_event:
                    event_list[
                        self.outdoor_last_event[cam_id]["time"]
                    ] = self.outdoor_last_event[cam_id]
                event_id = event_list[sorted(event_list)[0]]["id"]

        if device_type == "NSD":
            # for the smoke detector
            if not event_id:
                # If no event is provided we need to retrieve the oldest of
                # the last event by each smoke detector
                event_list = {}
                for sid in self.outdoor_last_event:
                    event_list[
                        self.outdoor_last_event[sid]["time"]
                    ] = self.outdoor_last_event[sid]
                event_id = event_list[sorted(event_list)[0]]["id"]

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

        for e in event_list:
            if e["type"] == "outdoor":
                if e["camera_id"] not in self.outdoor_events:
                    self.outdoor_events[e["camera_id"]] = {}
                self.outdoor_events[e["camera_id"]][e["time"]] = e
            elif e["type"] != "outdoor":
                if e["camera_id"] not in self.events:
                    self.events[e["camera_id"]] = {}
                self.events[e["camera_id"]][e["time"]] = e
        for camera in self.events:
            self.last_event[camera] = self.events[camera][
                sorted(self.events[camera])[-1]
            ]
        for camera in self.outdoor_events:
            self.outdoor_last_event[camera] = self.outdoor_events[camera][
                sorted(self.outdoor_events[camera])[-1]
            ]

    def person_seen_by_camera(self, name, cid, exclude=0):
        """
        Evaluate if a specific person has been seen
        """
        # Check in the last event is someone known has been seen
        if exclude:
            limit = time.time() - exclude
            array_time_event = sorted(self.events[cid], reverse=True)
            for time_ev in array_time_event:
                if time_ev < limit:
                    return False
                if self.events[cid][time_ev]["type"] == "person":
                    person_id = self.events[cid][time_ev]["person_id"]
                    if "pseudo" in self.persons[person_id]:
                        if self.persons[person_id]["pseudo"] == name:
                            return True
        elif self.last_event[cid]["type"] == "person":
            person_id = self.last_event[cid]["person_id"]
            if "pseudo" in self.persons[person_id]:
                if self.persons[person_id]["pseudo"] == name:
                    return True
        return False

    def _known_persons(self):
        known_persons = {}
        for p_id, p in self.persons.items():
            if "pseudo" in p:
                known_persons[p_id] = p
        return known_persons

    def known_persons(self):
        return {pid: p["pseudo"] for pid, p in self._known_persons().items()}

    def known_persons_names(self):
        names = []
        for _, p in self._known_persons().items():
            names.append(p["pseudo"])
        return names

    def someone_known_seen(self, cid: str, exclude: int = 0) -> bool:
        """Evaluate if someone known has been seen."""
        if cid not in self.events:
            raise NoDevice
        if exclude:
            limit = time.time() - exclude
            array_time_event = sorted(self.events[cid], reverse=True)
            for time_ev in array_time_event:
                if time_ev < limit:
                    return False
                if self.events[cid][time_ev]["type"] == "person":
                    if self.events[cid][time_ev]["person_id"] in self._known_persons():
                        return True
        # Check in the last event if someone known has been seen
        elif self.last_event[cid]["type"] == "person":
            if self.last_event[cid]["person_id"] in self._known_persons():
                return True
        return False

    def someone_unknown_seen(self, cid: str, exclude: int = 0) -> bool:
        """Evaluate if someone known has been seen."""
        if cid not in self.events:
            raise NoDevice
        if exclude:
            limit = time.time() - exclude
            array_time_event = sorted(self.events[cid], reverse=True)
            for time_ev in array_time_event:
                if time_ev < limit:
                    return False
                if self.events[cid][time_ev]["type"] == "person":
                    if (
                        self.events[cid][time_ev]["person_id"]
                        not in self._known_persons()
                    ):
                        return True
        # Check in the last event is someone known has been seen
        elif self.last_event[cid]["type"] == "person":
            if self.last_event[cid]["person_id"] not in self._known_persons():
                return True
        return False

    def motion_detected(self, cid, exclude=0):
        """Evaluate if movement has been detected."""
        if cid not in self.events:
            raise NoDevice
        if exclude:
            limit = time.time() - exclude
            array_time_event = sorted(self.events[cid], reverse=True)
            for time_ev in array_time_event:
                if time_ev < limit:
                    return False
                if self.events[cid][time_ev]["type"] == "movement":
                    return True
        elif self.last_event[cid]["type"] == "movement":
            return True
        return False

    def outdoor_motion_detected(self, cid: str, offset: int = 0) -> bool:
        """Evaluate if outdoor movement has been detected."""
        if cid in self.last_event:
            if self.last_event[cid]["type"] == "movement":
                if self.last_event[cid][
                    "video_status"
                ] == "recording" and self.last_event[cid]["time"] + offset > int(
                    time.time()
                ):
                    return True
        return False

    def human_detected(self, cid: str, offset: int = 0) -> bool:
        """Evaluate if a human has been detected."""
        if self.outdoor_last_event[cid]["video_status"] == "recording":
            for e in self.outdoor_last_event[cid]["event_list"]:
                if e["type"] == "human" and e["time"] + offset > int(time.time()):
                    return True
        return False

    def animal_detected(self, cid: str, offset: int = 0) -> bool:
        """Evaluate if an animal has been detected."""
        if self.outdoor_last_event[cid]["video_status"] == "recording":
            for e in self.outdoor_last_event[cid]["event_list"]:
                if e["type"] == "animal" and e["time"] + offset > int(time.time()):
                    return True
        return False

    def car_detected(self, cid: str, offset: int = 0) -> bool:
        """Evaluate if a car has been detected."""
        if self.outdoor_last_event[cid]["video_status"] == "recording":
            for e in self.outdoor_last_event[cid]["event_list"]:
                if e["type"] == "vehicle" and e["time"] + offset > int(time.time()):
                    return True
        return False

    def module_motion_detected(self, mid: str, cid: str, exclude: int = 0) -> bool:
        """Evaluate if movement has been detected."""
        if exclude:
            limit = time.time() - exclude
            array_time_event = sorted(self.events.get(cid, []), reverse=True)
            for time_ev in array_time_event:
                if time_ev < limit:
                    return False
                if (
                    self.events[cid][time_ev]["type"] == "tag_big_move"
                    or self.events[cid][time_ev]["type"] == "tag_small_move"
                ) and self.events[cid][time_ev]["module_id"] == mid:
                    return True
        elif (
            cid in self.last_event
            and (
                self.last_event[cid]["type"] == "tag_big_move"
                or self.last_event[cid]["type"] == "tag_small_move"
            )
            and self.last_event[cid]["module_id"] == mid
        ):
            return True
        return False

    def module_opened(self, mid: str, cid: str, exclude: int = 0) -> bool:
        """Evaluate if module status is open."""
        if exclude:
            limit = time.time() - exclude
            array_time_event = sorted(self.events.get(cid, []), reverse=True)
            for time_ev in array_time_event:
                if time_ev < limit:
                    return False
                if (
                    self.events[cid][time_ev]["type"] == "tag_open"
                    and self.events[cid][time_ev]["module_id"] == mid
                ):
                    return True
        elif cid in self.last_event and (
            self.last_event[cid]["type"] == "tag_open"
            and self.last_event[cid]["module_id"] == mid
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
