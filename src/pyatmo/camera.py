import imghdr
import time
from pprint import pformat
from typing import Dict, Optional, Tuple

from requests.exceptions import ReadTimeout

from pyatmo.exceptions import ApiError, InvalidHome, NoDevice
from pyatmo.helpers import BASE_URL, LOG

_GETHOMEDATA_REQ = BASE_URL + "api/gethomedata"
_GETCAMERAPICTURE_REQ = BASE_URL + "api/getcamerapicture"
_GETEVENTSUNTIL_REQ = BASE_URL + "api/geteventsuntil"
_SETPERSONSAWAY_REQ = BASE_URL + "api/setpersonsaway"
_SETPERSONSHOME_REQ = BASE_URL + "api/setpersonshome"
_SETSTATE_REQ = BASE_URL + "api/setstate"


class CameraData:
    """
    List the Netatmo camera informations
        (Homes, cameras, smoke detectors, modules, events, persons)
    Args:
        auth_data (ClientAuth):
            Authentication information with a working access Token
    """

    def __init__(self, auth_data, size=15):
        self.auth_data = auth_data
        post_params = {"size": size}
        resp = self.auth_data.post_request(url=_GETHOMEDATA_REQ, params=post_params)
        if resp is None or "body" not in resp:
            raise NoDevice("No device data returned by Netatmo server")

        self.raw_data = resp["body"].get("homes")
        if not self.raw_data:
            raise NoDevice("No device data available")

        self.homes = {d["id"]: d for d in self.raw_data}
        if not self.homes:
            raise NoDevice("No device available")

        self.persons = {}
        self.events = {}
        self.outdoor_events = {}
        self.cameras = {}
        self.smokedetectors = {}
        self.modules = {}
        self.last_event = {}
        self.outdoor_last_event = {}
        self.types = {}
        self.default_home = None
        self.default_home_id = None
        self.default_camera = None
        self.default_smokedetector = None
        for item in self.raw_data:
            home_id = item.get("id")
            home_name = item.get("name")

            if not home_name:
                home_name = "Unknown"
                self.homes[home_id]["name"] = home_name
            if not home_id:
                LOG.error('No key ["id"] in %s', item.keys())
                continue

            if home_id not in self.cameras:
                self.cameras[home_id] = {}
            if home_id not in self.smokedetectors:
                self.smokedetectors[home_id] = {}
            if home_id not in self.types:
                self.types[home_id] = {}

            for person in item["persons"]:
                self.persons[person["id"]] = person

            if "events" in item:
                if not self.default_home and not self.default_home_id:
                    self.default_home = item["name"]
                    self.default_home_id = item["id"]

                for event in item["events"]:
                    if event["type"] == "outdoor":
                        if event["camera_id"] not in self.outdoor_events:
                            self.outdoor_events[event["camera_id"]] = {}
                        self.outdoor_events[event["camera_id"]][event["time"]] = event
                    elif event["type"] != "outdoor":
                        if event["camera_id"] not in self.events:
                            self.events[event["camera_id"]] = {}
                        self.events[event["camera_id"]][event["time"]] = event

            for camera in item["cameras"]:
                self.cameras[home_id][camera["id"]] = camera
                self.cameras[home_id][camera["id"]]["home"] = home_id
                if camera["type"] == "NACamera" and "modules" in camera:
                    for module in camera["modules"]:
                        self.modules[module["id"]] = module
                        self.modules[module["id"]]["cam_id"] = camera["id"]

            for smoke_detector in item["smokedetectors"]:
                self.smokedetectors[home_id][smoke_detector["id"]] = smoke_detector

            for camera_type in item["cameras"]:
                self.types[home_id][camera_type["type"]] = camera_type

            for camera_type in item["smokedetectors"]:
                self.types[home_id][camera_type["type"]] = camera_type

        for camera in self.events:
            self.last_event[camera] = self.events[camera][
                sorted(self.events[camera])[-1]
            ]
        for camera in self.outdoor_events:
            self.outdoor_last_event[camera] = self.outdoor_events[camera][
                sorted(self.outdoor_events[camera])[-1]
            ]
        if self.modules != {}:
            self.default_module = list(self.modules.values())[0]["name"]
        else:
            self.default_module = None
        if self.default_home is not None and self.cameras[self.default_home_id]:
            self.default_camera = list(self.cameras[self.default_home_id].values())[0]

    def home_by_id(self, hid):
        return None if hid not in self.homes else self.homes[hid]

    def home_by_name(self, home=None):
        if not home:
            return self.home_by_name(self.default_home)

        for key, value in self.homes.items():
            if value["name"] == home:
                return self.homes[key]
        raise InvalidHome()

    def get_home_name(self, home_id=None):
        if home_id is None:
            home_id = self.default_home_id
        for key, value in self.homes.items():
            if value["id"] == home_id:
                return self.homes[key]["name"]
        raise InvalidHome("Invalid Home ID %s" % home_id)

    def get_home_id(self, home=None):
        if not home:
            home = self.default_home
        for key, value in self.homes.items():
            if value["name"] == home:
                return self.homes[key]["id"]
        raise InvalidHome("Invalid Home %s" % home)

    def camera_by_id(self, cid):
        """Get camera data by ID."""
        return self.get_camera(cid)

    def get_camera(self, cid: str) -> Optional[Dict[str, str]]:
        """Get camera data."""
        for home_id, _ in self.cameras.items():
            if cid in self.cameras[home_id]:
                return self.cameras[home_id][cid]
        return None

    def camera_by_name(self, camera=None, home=None, home_id=None):
        """Get camera data by name."""
        if home_id is None:
            if home is None:
                hid = self.default_home_id

            else:
                try:
                    hid = self.home_by_name(home)["id"]
                except InvalidHome:
                    LOG.debug("Invalid home %s", home)
                    return None
        else:
            hid = home_id

        if camera is None and home is None and home_id is None:
            return self.default_camera

        if not (home_id or home) and camera:
            for h_id, cam_ids in self.cameras.items():
                for cam_id in cam_ids:
                    if self.cameras[h_id][cam_id]["name"] == camera:
                        return self.cameras[h_id][cam_id]

        elif hid and camera:
            if hid not in self.cameras:
                return None

            for cam_id in self.cameras[hid]:
                if self.cameras[hid][cam_id]["name"] == camera:
                    return self.cameras[hid][cam_id]
        else:
            return list(self.cameras[hid].values())[0]

    def module_by_id(self, mid):
        return None if mid not in self.modules else self.modules[mid]

    def module_by_name(self, module=None, camera=None, home=None):
        if not module:
            if self.default_module:
                return self.module_by_name(self.default_module)
            return None
        cam = None
        if camera or home:
            cam = self.camera_by_name(camera, home)
            if not cam:
                return None
        for key, value in self.modules.items():
            if value["name"] == module:
                if cam and value["cam_id"] != cam["id"]:
                    return None
                return self.modules[key]
        return None

    def smokedetector_by_id(self, sid):
        for home, _ in self.smokedetectors.items():
            if sid in self.smokedetectors[home]:
                return self.smokedetectors[home][sid]
        return None

    def smokedetector_by_name(self, smokedetector=None, home=None, home_id=None):
        if home_id is None:
            if home is None:
                hid = self.default_home_id
            else:
                try:
                    hid = self.home_by_name(home)["id"]
                except InvalidHome:
                    LOG.debug("Invalid home %s", home)
                    return None
        else:
            hid = home_id

        if smokedetector is None and home is None and home_id is None:
            return self.default_smokedetector

        if not (home_id or home) and smokedetector:
            for h_id, cam_ids in self.smokedetectors.items():
                for cam_id in cam_ids:
                    if self.smokedetectors[h_id][cam_id]["name"] == smokedetector:
                        return self.smokedetectors[h_id][cam_id]

        elif hid and smokedetector:
            hid = self.home_by_name(home)["id"]
            if hid not in self.smokedetectors:
                return None
            for cam_id in self.smokedetectors[hid]:
                if self.smokedetectors[hid][cam_id]["name"] == smokedetector:
                    return self.smokedetectors[hid][cam_id]
        else:
            return list(self.smokedetectors[hid].values())[0]

    def camera_type(self, camera=None, home=None, cid=None, home_id=None):
        """
        Return the type of a given camera.
        """
        cameratype = None
        if cid:
            camera_data = self.get_camera(cid)
        else:
            camera_data = self.camera_by_name(camera=camera, home=home, home_id=home_id)
        if camera_data:
            cameratype = camera_data["type"]
        return cameratype

    def camera_urls_by_name(
        self, camera: str = None, home: str = None, home_id: str = None
    ) -> Optional[Tuple[Optional[str], Optional[str]]]:
        """
        Return the vpn_url and the local_url (if available) of a given camera
        in order to access its live feed
        (old interface)
        """
        if home_id:
            cid = self.camera_by_name(camera=camera, home_id=home_id)["id"]
        else:
            cid = self.camera_by_name(camera=camera, home=home)["id"]

        return self.camera_urls(cid=cid) if cid is not None else None

    def camera_urls(self, cid: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Return the vpn_url and the local_url (if available) of a given camera
        in order to access its live feed
        """
        local_url = None
        vpn_url = None

        camera_data = self.get_camera(cid)

        if camera_data:
            vpn_url = camera_data.get("vpn_url")
            if camera_data.get("is_local"):

                def check_url(url: Optional[str]) -> Optional[str]:
                    if url is None:
                        return None
                    try:
                        resp = self.auth_data.post_request(url=f"{url}/command/ping")
                    except (ApiError, ReadTimeout):
                        LOG.debug("Timeout validation the camera url %s", url)
                        return None
                    else:
                        return resp.get("local_url")

                temp_local_url = check_url(vpn_url)
                local_url = check_url(temp_local_url)

        return vpn_url, local_url

    def get_light_state(self, cid: str) -> Optional[str]:
        """Return the current mode of the floodlight of a presence camera."""
        camera_data = self.get_camera(cid)
        if camera_data is None:
            raise ValueError("Invalid Camera ID")

        return camera_data.get("light_mode_status")

    def persons_at_home_by_name(self, home=None):
        """
        Return the list of known persons who are currently at home
        (old interface)
        """
        if not home:
            home_id = self.default_home_id
        else:
            home_id = self.home_by_name(home)["id"]
        return self.persons_at_home(home_id)

    def persons_at_home(self, home_id=None):
        """
        Return the list of known persons who are currently at home
        """
        home_data = self.home_by_id(home_id)
        at_home = []
        for person in home_data["persons"]:
            # Only check known personshome
            if "pseudo" in person:
                if not person["out_of_sight"]:
                    at_home.append(person["pseudo"])
        return at_home

    def set_persons_home(self, person_ids, home_id):
        """
        Mark persons as home.
        """
        post_params = {"home_id": home_id, "person_ids[]": person_ids}
        resp = self.auth_data.post_request(url=_SETPERSONSHOME_REQ, params=post_params)
        return resp

    def set_person_away(self, person_id, home_id):
        """Mark a person as away or set the whole home to being empty.

        Arguments:
            person_id {str} -- ID of a person
            home_id {str} -- ID of a home

        Returns:
            [type] -- [description]
        """
        post_params = {"home_id": home_id, "person_id": person_id}
        resp = self.auth_data.post_request(url=_SETPERSONSAWAY_REQ, params=post_params)
        return resp

    def get_person_id(self, name):
        """Retrieve the ID of a person

        Arguments:
            name {str} -- Name of a person

        Returns:
            str -- ID of a person
        """
        for pid, data in self.persons.items():
            if "pseudo" in data and name == data["pseudo"]:
                return pid
        return None

    def get_camera_picture(self, image_id, key):
        """
        Download a specific image (of an event or user face) from the camera
        """
        post_params = {"image_id": image_id, "key": key}
        resp = self.auth_data.post_request(
            url=_GETCAMERAPICTURE_REQ, params=post_params
        )
        image_type = imghdr.what("NONE.FILE", resp)
        return resp, image_type

    def get_profile_image(self, name):
        """
        Retrieve the face of a given person
        """
        for person in self.persons:
            if "pseudo" in self.persons[person]:
                if name == self.persons[person]["pseudo"]:
                    image_id = self.persons[person]["face"]["id"]
                    key = self.persons[person]["face"]["key"]
                    return self.get_camera_picture(image_id, key)
        return None, None

    def update_event(self, event=None, home=None, devicetype=None, home_id=None):
        """
        Update the list of events
        """
        if not home_id:
            try:
                if not home:
                    home = self.default_home
                home_id = self.get_home_id(home)
            except InvalidHome:
                LOG.debug("Invalid Home %s", home)
                return None

        if devicetype == "NACamera":
            # for the Welcome camera
            if not event:
                # If no event is provided we need to retrieve the oldest of
                # the last event seen by each camera
                event_set = {}
                for cam_id in self.last_event:
                    event_set[self.last_event[cam_id]["time"]] = self.last_event[cam_id]
                event = event_set[sorted(event_set)[0]]

        if devicetype == "NOC":
            # for the Presence camera
            if not event:
                # If no event is provided we need to retrieve the oldest of
                # the last event seen by each camera
                event_set = {}
                for cam_id in self.outdoor_last_event:
                    event_set[
                        self.outdoor_last_event[cam_id]["time"]
                    ] = self.outdoor_last_event[cam_id]
                event = event_set[sorted(event_set)[0]]

        if devicetype == "NSD":
            # for the smoke detector
            if not event:
                # If no event is provided we need to retrieve the oldest of
                # the last event by each smoke detector
                event_set = {}
                for sid in self.outdoor_last_event:
                    event_set[
                        self.outdoor_last_event[sid]["time"]
                    ] = self.outdoor_last_event[sid]
                event = event_set[sorted(event_set)[0]]

        post_params = {"home_id": home_id, "event_id": event["id"]}
        event_list = []
        resp = None
        try:
            resp = self.auth_data.post_request(
                url=_GETEVENTSUNTIL_REQ, params=post_params
            )
            event_list = resp["body"]["events_list"]
        except ApiError:
            pass
        except KeyError:
            LOG.debug("eventList response: %s", pformat(resp))
            LOG.debug("eventList body: %s", resp.get("body", "UNKNOWN"))

        for _event in event_list:
            if _event["type"] == "outdoor":
                if _event["camera_id"] not in self.outdoor_events:
                    self.outdoor_events[event["camera_id"]] = {}
                self.outdoor_events[_event["camera_id"]][_event["time"]] = _event

            elif _event["type"] != "outdoor":
                if _event["camera_id"] not in self.events:
                    self.events[_event["camera_id"]] = {}
                self.events[_event["camera_id"]][event["time"]] = _event

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

    def _known_persons_dict(self):
        known_persons = {}
        for person_id, person in self.persons.items():
            if "pseudo" in person:
                known_persons[person_id] = person
        return known_persons

    def known_persons(self):
        return {pid: p["pseudo"] for pid, p in self._known_persons_dict().items()}

    def known_persons_names(self):
        names = []
        for _, person in self._known_persons_dict().items():
            names.append(person["pseudo"])
        return names

    def someone_known_seen(self, cid, exclude=0):
        """
        Evaluate if someone known has been seen
        """
        if exclude:
            limit = time.time() - exclude
            array_time_event = sorted(self.events[cid], reverse=True)
            for time_ev in array_time_event:
                if time_ev < limit:
                    return False
                if self.events[cid][time_ev]["type"] == "person":
                    if (
                        self.events[cid][time_ev]["person_id"]
                        in self._known_persons_dict()
                    ):
                        return True
        # Check in the last event if someone known has been seen
        elif self.last_event[cid]["type"] == "person":
            if self.last_event[cid]["person_id"] in self._known_persons_dict():
                return True
        return False

    def someone_unknown_seen(self, cid, exclude=0):
        if exclude:
            limit = time.time() - exclude
            array_time_event = sorted(self.events[cid], reverse=True)
            for time_ev in array_time_event:
                if time_ev < limit:
                    return False
                if self.events[cid][time_ev]["type"] == "person":
                    if (
                        self.events[cid][time_ev]["person_id"]
                        not in self._known_persons_dict()
                    ):
                        return True
        # Check in the last event is someone known has been seen
        elif self.last_event[cid]["type"] == "person":
            if self.last_event[cid]["person_id"] not in self._known_persons_dict():
                return True
        return False

    def motion_detected(self, cid, exclude=0):
        """
        Evaluate if movement has been detected
        """
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

    def outdoor_motion_detected(self, cid, offset=0):
        """
        Evaluate if outdoor movement has been detected
        """
        if cid in self.last_event:
            if self.last_event[cid]["type"] == "movement":
                if self.last_event[cid][
                    "video_status"
                ] == "recording" and self.last_event[cid]["time"] + offset > int(
                    time.time()
                ):
                    return True
        return False

    def human_detected(self, cid, offset=0):
        """
        Evaluate if a human has been detected
        """
        if self.outdoor_last_event[cid]["video_status"] == "recording":
            for event in self.outdoor_last_event[cid]["event_list"]:
                if event["type"] == "human" and event["time"] + offset > int(
                    time.time()
                ):
                    return True
        return False

    def animal_detected(self, cid, offset=0):
        """
        Evaluate if an animal has been detected
        """
        if self.outdoor_last_event[cid]["video_status"] == "recording":
            for event in self.outdoor_last_event[cid]["event_list"]:
                if event["type"] == "animal" and event["time"] + offset > int(
                    time.time()
                ):
                    return True
        return False

    def car_detected(self, cid, offset=0):
        """
        Evaluate if a car has been detected
        """
        if self.outdoor_last_event[cid]["video_status"] == "recording":
            for event in self.outdoor_last_event[cid]["event_list"]:
                if event["type"] == "vehicle" and event["time"] + offset > int(
                    time.time()
                ):
                    return True
        return False

    def module_motion_detected(self, mid, cid, exclude=0):
        """
        Evaluate if movement has been detected
        """
        if exclude:
            limit = time.time() - exclude
            array_time_event = sorted(self.events[cid], reverse=True)
            for time_ev in array_time_event:
                if time_ev < limit:
                    return False
                if (
                    self.events[cid][time_ev]["type"] == "tag_big_move"
                    or self.events[cid][time_ev]["type"] == "tag_small_move"
                ) and self.events[cid][time_ev]["module_id"] == mid:
                    return True
        elif (
            self.last_event[cid]["type"] == "tag_big_move"
            or self.last_event[cid]["type"] == "tag_small_move"
        ) and self.last_event[cid]["module_id"] == mid:
            return True
        return False

    def is_module_opened(self, module=None, home=None, camera=None, exclude=0):
        """
        Evaluate if module status is open
        """
        try:
            mod = self.module_by_name(module, camera=camera, home=home)
            mid = mod["id"]
            cid = mod["cam_id"]
        except TypeError:
            LOG.error("is_module_opened: Camera name, or home, or module is unknown")
            return False
        return self._module_opened(mid=mid, cid=cid, exclude=exclude)

    def _module_opened(self, mid, cid, exclude=0):
        if exclude:
            limit = time.time() - exclude
            array_time_event = sorted(self.events[cid], reverse=True)
            for time_ev in array_time_event:
                if time_ev < limit:
                    return False
                if (
                    self.events[cid][time_ev]["type"] == "tag_open"
                    and self.events[cid][time_ev]["module_id"] == mid
                ):
                    return True
        elif (
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
            home_id = self.get_camera(camera_id)["home"]

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
            resp = self.auth_data.post_request(url=_SETSTATE_REQ, params=post_params)
        except ApiError as err_msg:
            LOG.error("%s", err_msg)
            return False

        if "error" in resp:
            LOG.debug("%s", resp)
            return False

        LOG.debug("%s", resp)
        return True
