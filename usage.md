## Python Netatmo API programmers guide

> 2013-01-21, philippelt@users.sourceforge.net

> 2014-01-13, Revision to include new modules additionnal information

> 2016-06-25 Update documentation for Netatmo Welcome

> 2016-12-09 Update documentation for all Netatmo cameras

No additional library other than standard Python 3 library is required.

More information about the Netatmo REST API can be obtained from http://dev.netatmo.com/doc/

This package support only user based authentication.

### 1 Set up your environment from Netatmo Web interface

Before being able to use the module you will need :

- A Netatmo user account having access to, at least, one station
- An application registered from the user account (see http://dev.netatmo.com/dev/createapp) to obtain application credentials.

In the netatmo philosophy, both the application itself and the user have to be registered thus have authentication credentials to be able to access any station. Registration is free for both.

### 2 Setup your library

Install `pyatmo` as described in the `README.md`.

If you provide your credentials, you can test if everything is working properly by simply running the package as a standalone program.

This will run a full access test to the account and stations and return 0 as return code if everything works well. If run interactively, it will also display an OK message.

```bash
$ export CLIENT_ID="<your client_id>"
$ export CLIENT_SECRET="<your client_secret>"
$ export USERNAME="<netatmo username>"
$ export PASSWORD="<netatmo user password>"
$ python3 pyatmo.py
pyatmo.py : OK
$ echo $?
0
```

### 3 Package guide

Most of the time, the sequence of operations will be :

1. Authenticate your program against Netatmo web server
2. Get the device list accessible to the user
3. Request data on one of these devices or directly access last data sent by the station

Example :

```python
import pyatmo

# 1 : Authenticate
CLIENT_ID = '123456789abcd1234'
CLIENT_SECRET = '123456789abcd1234'
USERNAME = 'your@account.com'
PASSWORD = 'abcdef-123456-ghijkl'
authorization = pyatmo.ClientAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    username=USERNAME,
    password=PASSWORD,
)

# 2 : Get devices list
weather_data = pyatmo.WeatherStationData(authorization)
weather_data.update()

# 3 : Access most fresh data directly
print(
    "Current temperature (inside/outside): %s / %s °C"
    % (
        weather_data.last_data()["indoor"]["Temperature"],
        weather_data.last_data()["outdoor"]["Temperature"],
    )
)
```

The user must have named the sensors indoor and outdoor through the Web interface (or any other name as long as the program is requesting the same name).

The Netatmo design is based on stations (usually the in-house module) and modules (radio sensors reporting to a station, usually an outdoor sensor).

Sensor design is not exactly the same for station and external modules, and they are not addressed the same way wether in the station or an external module. This is a design issue of the API that restrict the ability to write generic code that could work for station sensor the same way as other modules sensors. The station role (the reporting device) and module role (getting environmental data) should not have been mixed. The fact that a sensor is physically built in the station should not interfere with this two distincts objects.

The consequence is that, for the API, we will use terms of station data (for the sensors inside the station) and module data (for external(s) module). Lookup methods like module_by_name look for external modules and **NOT station
modules**.

Having two roles, the station has a 'station_name' property as well as a 'module_name' for its internal sensor.

> Exception : to reflect again the API structure, the last data uploaded by the station is indexed by module_name (wether it is a station module or an external module).

Sensors (stations and modules) are managed in the API using ID's (network hardware adresses). The Netatmo web account management gives you the capability to associate names to station sensor and module (and to the station itself). This is by far more comfortable and the interface provides service to locate a station or a module by name or by ID depending on your taste. Module lookup by name includes the optional station name in case
multiple stations would have similar module names (if you monitor multiple stations/locations, it would not be a surprise that each of them would have an 'outdoor' module). This is a benefit in the sense it gives you the ability to write generic code (for example, collect all 'outdoor' temperatures for all your stations).

The results are Python data structures, mostly dictionaries as they mirror easily the JSON returned data. All supplied classes provides simple properties to use as well as access to full data returned by the netatmo web services (rawData property for most classes).

### 4 Package classes and functions

#### 4-1 Global variables

`_DEFAULT_BASE_URL` and `_*_REQ`: Various URL to access Netatmo web services.
They are documented in https://dev.netatmo.com/doc/.
They should not be changed unless Netatmo API changes.

#### 4-2 ClientAuth class

Constructor

```python
authorization = pyatmo.ClientAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    username=USERNAME,
    password=PASSWORD,
    scope="read_station",
    base_url="https://example.com/api",  #optional
    user_prefix="xmpl",                  #optional
)
```

Requires : Application and User credentials to access Netatmo API.

Return : an authorization object that will supply the access token required by other web services. This class will handle the renewal of the access token if expiration is reached.

Properties, all properties are read-only unless specified :

- **accessToken** : Retrieve a valid access token (renewed if necessary)
- **refreshToken** : The token used to renew the access token (normally should not be used)
- **expiration** : The expiration time (epoch) of the current token
- **base_url** : If targeting a third-party Netatmo-compatible API, the custom base URL to reach it
- **user_prefix** : If targeting a third-part Netatmo-compatible API, the custom user prefix for this API
- **scope** : The scope of the required access token (what will it be used for) default to read_station to provide backward compatibility.

Possible values for scope are :

- read_station: to retrieve weather station data (Getstationsdata, Getmeasure)
- read_camera: to retrieve Welcome camera data (Gethomedata, Getcamerapicture)
- access_camera: to access the camera, the videos and the live stream.
- read_thermostat: to retrieve thermostat data (Getmeasure, Getthermostatsdata)
- write_thermostat: to set up the thermostat (Syncschedule, Setthermpoint)
- read_presence: to retrieve Presence data (Gethomedata, Getcamerapicture)
- access_presence: to access the camera, the videos and the live stream.

Several value can be used at the same time, ie: 'read_station read_camera'

#### 4-3 WeatherStationData class

Constructor

```python
weather_data = pyatmo.WeatherStationData(authorization)
```

Requires : an authorization object (ClientAuth instance)

Return : a WeatherStationData object. This object contains most administration properties of stations and modules accessible to the user and the last data pushed by the station to the Netatmo servers.

Raise a pyatmo.NoDevice exception if no weather station is available for the given account.

Properties, all properties are read-only unless specified:

- **rawData** : Full dictionary of the returned JSON DEVICELIST Netatmo API service
- **default_station** : Name of the first station returned by the web service (warning, this is mainly for the ease of use of peoples having only 1 station).
- **stations** : Dictionary of stations (indexed by ID) accessible to this user account
- **modules** : Dictionary of modules (indexed by ID) accessible to the user account (whatever station there are plugged in)

Methods :

- **station_by_name** (station=None) : Find a station by it is station name

  - Input : Station name to lookup (str)
  - Output : station dictionary or None

- **station_by_id** (sid) : Find a station by it is Netatmo ID (mac address)

  - Input : Station ID
  - Output : station dictionary or None

- **module_by_name** (module, station=None) : Find a module by it is module name

  - Input : module name and optional station name
  - Output : module dictionary or None

  The station name parameter, if provided, is used to check wether the module belongs to the appropriate station (in case multiple stations would have same module name).

- **module_by_id** (mid, sid=None) : Find a module by it is ID and belonging station's ID

  - Input : module ID and optional Station ID
  - Output : module dictionary or None

- **modules_names_list** (station=None) : Get the list of modules names, including the station module name. Each of them should have a corresponding entry in last_data. It is an equivalent (at lower cost) for last_data.keys()

- **last_data** (station=None, exclude=0) : Get the last data uploaded by the station, exclude sensors with measurement older than given value (default return all)

  - Input : station name OR id. If not provided default_station is used. Exclude is the delay in seconds from now to filter sensor readings.
  - Output : Sensors data dictionary (Key is sensor name)

  AT the time of this document, Available measures types are :

  - a full or subset of Temperature, Pressure, Noise, Co2, Humidity, Rain (mm of precipitation during the last 5 minutes, or since the previous data upload), When (measurement timestamp) for modules including station module
  - battery_vp : likely to be total battery voltage for external sensors (running on batteries) in mV (undocumented)
  - rf_status : likely to be the % of radio signal between the station and a module (undocumented)

  See Netatmo API documentation for units of regular measurements

  If you named the internal sensor 'indoor' and the outdoor one 'outdoor' (simple is'n it ?) for your station in the user Web account station properties, you will access the data by :

```python
# Last data access example

the_data = weather_data.last_data()
print('Available modules : ', the_data.keys())
print('In-house CO2 level : ', the_data['indoor']['Co2'])
print('Outside temperature : ', the_data['outdoor']['Temperature'])
print('External module battery : ', "OK" if int(the_data['outdoor']['battery_vp']) > 5000 \
                                         else "NEEDS TO BE REPLACED")
```

- **check_not_updated** (station=None, delay=3600) :

  - Input : optional station name (else default_station is used)
  - Output : list of modules name for which last data update is older than specified delay (default 1 hour). If the station itself is lost, the module_name of the station will be returned (the key item of last_data information).

  For example (following the previous one)

```python
# Ensure data sanity

for m in weather_data.check_not_updated("<optional station name>"):
    print("Warning, sensor %s information is obsolete" % m)
    if module_by_name(m) == None : # Sensor is not an external module
        print("The station is lost")
```

- **check_updated** (station=None, delay=3600) :

  - Input : optional station name (else default_station is used)
  - Output : list of modules name for which last data update is newer than specified delay (default 1 hour).

  Complement of the previous service

- **get_measure** (device_id, scale, mtype, module_id=None, date_begin=None, date_end=None, limit=None, optimize=False) :
  - Input : All parameters specified in the Netatmo API service GETMEASURE (type being a python reserved word as been replaced by mtype).
  - Output : A python dictionary reflecting the full service response. No transformation is applied.
- **min_max_th** (station=None, module=None, frame="last24") : Return min and max temperature and humidity for the given station/module in the given timeframe
  _ Input :
  _ An optional station Name or ID, default\*station is used if not supplied,

  - An optional module name or ID, default : station sensor data is used
    _ A time frame that can be :
    _ "last24" : For a shifting window of the last 24 hours
    _ "day" : For all available data in the current day
    _ Output :
    \_  4 values tuple (Temp mini, Temp maxi, Humid mini, Humid maxi)

         >Note : I have been obliged to determine the min and max manually, the built-in service in the API doesn't always provide the actual min and max. The double parameter (scale) and aggregation request (min, max) is not satisfying

  at all if you slip over two days as required in a shifting 24 hours window.

#### 4-4 CameraData class

Constructor

```python
camera_data = pyatmo.CameraData(authorization)
camera_data.update()
```

Requires : an authorization object (ClientAuth instance)

Return : a CameraData object. This object contains most administration properties of Netatmo cameras accessible to the user and the last data pushed by the cameras to the Netatmo servers.

Raise a pyatmo.NoDevice exception if no camera is available for the given account.

Properties, all properties are read-only unless specified:

- **rawData** : Full dictionary of the returned JSON DEVICELIST Netatmo API service
- **default_home** : Name of the first home returned by the web service (warning, this is mainly for the ease of use of peoples having cameras in only 1 house).
- **default_camera** : Data of the first camera in the default home returned by the web service (warning, this is mainly for the ease of use of peoples having only 1 camera).
- **homes** : Dictionary of homes (indexed by ID) accessible to this user account
- **cameras** : Dictionary of cameras (indexed by home name and cameraID) accessible to this user
- **persons** : Dictionary of persons (indexed by ID) accessible to the user account
- **events** : Dictionary of events (indexed by cameraID and timestamp) seen by cameras
- **outdoor_events** : Dictionary of Outdoor events (indexed by cameraID and timestamp) seen by cameras

Methods :

- **home_by_id** (hid) : Find a home by its Netatmo ID

  - Input : Home ID
  - Output : home dictionary or None

- **home_by_name** (home=None) : Find a home by its home name

  - Input : home name to lookup (str)
  - Output : home dictionary or None

- **camera_by_id** (hid) : Find a camera by its Netatmo ID

  - Input : camera ID
  - Output : camera dictionary or None

- **camera_by_name** (camera=None, home=None) : Find a camera by its camera name

  - Input : camera name and home name to lookup (str)
  - Output : camera dictionary or None

- **camera_type** (camera=None, home=None, cid=None) : Return the type of a given camera.

  - Input : camera name and home name or cameraID to lookup (str)
  - Output : Return the type of a given camera

- **camera_urls_by_name** (camera=None, home=None, cid=None) : return Urls to access camera live feed

  - Input : camera name and home name or cameraID to lookup (str)
  - Output : tuple with the vpn_url (for remote access) and local url to access the camera live feed

- **persons_at_home_by_name** (home=None) : return the list of known persons who are at home

  - Input : home name to lookup (str)
  - Output : list of persons seen

- **get_camera_picture** (image_id, key): Download a specific image (of an event or user face) from the camera

  - Input : image_id and key of an events or person face
  - Output: Tuple with image data (to be stored in a file) and image type (jpg, png...)

- **get_profile_image** (name) : Retrieve the face of a given person

  - Input : person name (str)
  - Output: **get_camera_picture** data

- **update_event** (event=None, home=None, cameratype=None): Update the list of events

  - Input: Id of the latest event, home name and cameratype to update event list

- **person_seen_by_camera** (name, home=None, camera=None): Return true is a specific person has been seen by the camera in the last event

- **someone_known_seen** (home=None, camera=None) : Return true is a known person has been in the last event

- **someone_unknown_seen** (home=None, camera=None) : Return true is an unknown person has been seen in the last event

- **motion_detected** (home=None, camera=None) : Return true is a movement has been detected in the last event

- **outdoormotion_detected** (home=None, camera=None) : Return true is a outdoor movement has been detected in the last event

- **humanDetected** (home=None, camera=None) : Return True if a human has been detected in the last outdoor events

- **animalDetected** (home=None, camera=None) : Return True if an animal has been detected in the last outdoor events

- **carDetected** (home=None, camera=None) : Return True if a car has been detected in the last outdoor events

#### 4-5 ThermostatData class

Constructor

```python
thermostat_data = pyatmo.ThermostatData(authorization)
thermostat_data.update()
```

Requires : an authorization object (ClientAuth instance)

Return : a ThermostatData object. This object contains most administration properties of Netatmo thermostats accessible to the user and the last data pushed by the thermostats to the Netatmo servers.

Raise a pyatmo.NoDevice exception if no thermostat is available for the given account.

Properties, all properties are read-only unless specified:

- **rawData** : Full dictionary of the returned JSON Netatmo API service
- **devList** : Full dictionary of the returned JSON DEVICELIST Netatmo API service
- **default_device** : Name of the first device returned by the web service (warning, this is mainly for the ease of use of peoples having multiple thermostats in only 1 house).
- **default_module** : Data of the first module in the default device returned by the web service (warning, this is mainly for the ease of use of peoples having only 1 thermostat).
- **devices** : Dictionary of devices (indexed by ID) accessible to this user account
- **modules** : Dictionary of modules (indexed by device name and moduleID) accessible to this user
- **therm_program_list** : Dictionary of therm programs (indexed by ID) accessible to the user account
- **zones** : Dictionary of zones (indexed by ID)
- **timetable** : Dictionary of timetable (indexed by m_offset)

Methods :

- **deviceById** (hid) : Find a device by its Netatmo ID

  - Input : Device ID
  - Output : device dictionary or None

- **deviceByName** (device=None) : Find a device by it's device name

  - Input : device name to lookup (str)
  - Output : device dictionary or None

- **module_by_id** (hid) : Find a module by its Netatmo ID

  - Input : module ID
  - Output : module dictionary or None

- **module_by_name** (module=None, device=None) : Find a module by its module name

  - Input : module name and device name to lookup (str)
  - Output : module dictionary or None

- **setthermpoint** (mode, temp, endTimeOffsetmode, temp, endTimeOffset) : set thermpoint
  - Input : device_id and module_id and setpoint_mode

#### 4-6 Utilities functions

- **to_time_string** (timestamp) : Convert a Netatmo time stamp to a readable date/time format.
- **to_epoch**( dateString) : Convert a date string (form YYYY-MM-DD_HH:MM:SS) to timestamp
- **today_stamps**() : Return a couple of epoch time (start, end) for the current day
