import requests
import time
import socket
import json
from threading import Thread

"""
DataFrame holds all the information concerning one variable/sensor (objects)
Storage holds all the individual DataFrames in a dictionary (object with dict of objects)
Driver is the API handler and interface with the device, also holds the Storage
Manager Handles discovery and keeps track of the discovered devices
"""

if False:  # MYPY
    from typing import Any


class HealthBox3Exception(Exception):
    pass

class DataFrame:
    """" This will hold all the data for one variable in the HealthBox3 """
    def __init__(self,
                 identifier,
                 name,
                 unit=None,
                 value=None,
                 description=None,
                 room=None,
                 gateway_sensor=None,
                 ):
        # type: (str, str, str, str, str, str, Any) -> None
        self.identifier  = identifier
        self.name        = name
        self.unit        = unit
        self.value       = value
        self.description = description
        self.room        = room
        self.gateway_sensor = gateway_sensor

class HealtBox3Storage:
    def __init__(self):
        self.dataframes = {}  # type: Dict[str, DataFrame]
        self.available_rooms = [] # type: list

    def upsert_from_dataframe_list(self, dataframe_list):
        # type: (List[SingleDataFrame]) -> None
        """ receives a list of SingleDataFrames and creates a structure of dataframes """
        for dataframe in dataframe_list:
            if dataframe.identifier not in self.dataframes.keys():
                self.add_single_dataframe(dataframe)
            else:
                self.update_value(dataframe.identifier, dataframe.value)
        return

    def add_single_dataframe(self, dataframe):
        # type: (SingleDataFrame) -> None
        if dataframe.identifier not in self.dataframes.keys():
            self.dataframes[dataframe.identifier] = dataframe
            return True
        return False

    def get_value(self, identifier):
        # type (identifier) -> int
        if identifier in self.dataframes.keys():
            return self.dataframes[identifier].value
        return None

    def update_value(self, identifier, value):
        # type: (identifier, Any) -> bool
        if identifier not in self.dataframes.keys():
            return False
        self.dataframes[identifier].value = value
        return True

    def get_gateway_sensor(self, identifier):
        # type (identifier) -> int
        if identifier in self.dataframes.keys():
            return self.dataframes[identifier].gateway_sensor
        return None

    def update_gateway_sensor(self, identifier, gateway_sensor):
        # type: (identifier, int) -> bool
        if identifier not in self.dataframes.keys():
            return False
        self.dataframes[identifier].gateway_sensor = gateway_sensor
        return True

    def get_list_of_variables(self):
        # type: () -> List[str]
        """ returns a list of all the possible variables in the HealthBox3 system """
        return list(self.dataframes.keys())

    def __len__(self):
        return len(self.dataframes)

class HealthBox3Driver:
    """
    Class that is a wrapper around the HealthBox3 api.
     - Contains all the possible actions on the device
     - Holds a cached state of the variables in the system and automatically syncs back with the device
    """

    def __init__(self, ip=None, sync_delay=2.0):
        # Type: (str, float) -> None
        # === Properties ===
        # general
        self.ip = ip
        self.is_connected = False
        self.hbs = HealtBox3Storage()
        self.is_running = True

        # syncing
        self.sync_delay = sync_delay

        # setup thread to sync the data with the HealthBox by means of polling
        self.sync_thread = Thread(target=self._sync_periodically)
        self.sync_thread.daemon = True

        # start the connection if an ip is provided
        if self.ip is not None:
            self.start_connection()

    def start_connection(self):
        self._sync_variables()
        self.sync_thread.start()

    def stop(self):
        # type: () -> None
        """ Stop the sync thread to cleanly close of the HealthBox3 object"""

        # then stopping the syncing
        self.is_running = False

    def stop_connection(self):
        # type: () -> None
        """ Stop the sync thread to cleanly close of the HealthBox3 object"""

        # then stopping the syncing
        self.is_running = False
        if hasattr(self, 'sync_thread') and self.sync_thread.is_alive():
            self.sync_thread.join(timeout=5)

    def _format_url(self, endpoint, options=None):
        # type: (str, Optional[Dict[str, str]]) -> str
        # first create the options string
        if options is not None:
            option_strings = []
            for option in options:
                option_strings.append('{}={}'.format(option, options[option]))
            # Sort the values alphabetically to make sure that the api receives the options in order -> Highly needed...
            option_strings.sort()
            options_str = '?' + '&'.join(option_strings)
        else:
            options_str = ''

        # Prepare the url string
        url = 'http://'
        if endpoint.startswith('/'):
            url += self.ip + endpoint + options_str
        else:
            url += self.ip + '/' + endpoint + options_str
        return url

    def test_connection(self):
        # type () -> None
        """ Test if the device is online, best practice is to test before the first request is send"""
        if self.ip is None:
            self.is_connected = False
        try:
            resp = requests.get(self._format_url(HealthBox3Driver.Endpoints.DATA))
            self.is_connected = resp.status_code == 200
        except:
            self.is_connected = False

    def _perform_get_request(self, endpoint, options=None):
        # type: (str, Optional[Dict[str, str]]) -> Optional[requests.models.Response]
        """ Executes a get request. First checks if the device is in reach or not"""
        if not self.is_connected:
            self.test_connection()
        if not self.is_connected:
            raise HealthBox3Exception('Could not reach device, is the device online?')
        else:
            resp = None
            try:
                resp = requests.get(self._format_url(endpoint, options=options))
            except Exception:
                self.is_connected = False
            return resp

    def _perform_post_request(self, endpoint, body=None, options=None):
        # type: (str, str, Optional[Dict[str, str]]) -> Optional[requests.models.Response]
        """ Executes a post request. First checks if the device is in reach or not"""
        if not self.is_connected:
            self.test_connection()
        if not self.is_connected:
            raise HealthBox3Exception('Could not reach device, is the device online?')
        else:
            resp = None
            try:
                resp = requests.post(self._format_url(endpoint, options=options), json=body)
            except Exception:
                self.is_connected = False
            return resp

    def get_list_of_variables(self):
        # type: () -> List[str]
        """ Returns a list of variables in the system """
        return self.hbs.get_list_of_variables()

    def get_variable(self, name):
        # type: (str, Index) -> Optional[Any]
        """ Retrieves a variable from the cache """
        if name not in self.get_list_of_variables():
            return None
        return self.hbs.get_value(name)

    def upsert_cached_variable(self, identifier, value, name=None, unit=None, description=None, room=None):
        # type: (str, str, Type, Any, str) -> bool
        """
        Will create/update a variable in the cache of the gateway
        """
        # check if we can update an existing value
        response = self.hbs.update_value(identifier=identifier, value=value)
        # if no existing value
        if not response:
            df = DataFrame(
                identifier  =identifier,
                name        =name,
                unit        =unit,
                value       =value,
                description =description,
                room        =room,
            )

            self.hbs.add_single_dataframe(df)
            response = True
        return response

    def get_available_rooms(self):
        # type: () -> list
        return self.hbs.available_rooms

    def get_gateway_sensor(self, name):
        # type: (str, Index) -> Optional[Any]
        """ Retrieves a variable from the cache """
        if name not in self.get_list_of_variables():
            return None
        return self.hbs.get_gateway_sensor(name)

    def set_gateway_sensor(self, identifier, gateway_sensor):
        # type: (str, Any, Index) -> str
        """
        Will update a variable on the HealthBox3 device
        """
        # set the cached state also up to date
        response = self.hbs.update_gateway_sensor(identifier=identifier, gateway_sensor=gateway_sensor)
        return response

    def _extract_data(self, data):
        # boilerplate to be able to get the information out of the healthbox in a usable manner
        # input the json response from the healthbox and output a list of sensors and a list of roomnumbers
        # type: (dict) -> list
        dataframe_list = []
        room_list      = []

        # get general (unnested) information
        for key, value in data.items():
            if not isinstance(value, list) and not isinstance(value, dict): # filtering out nested dicts and lists
                dataframe = DataFrame(
                    identifier = key,
                    name       = key,
                    value      = value
                )
                dataframe_list.append(dataframe)

        # get global information
        for key, value in data['global']['parameter'].items():
            dataframe = DataFrame(
                identifier = key,
                name       = key,
                value      = value['value']
            )
            dataframe_list.append(dataframe)

        # get global sensor information
        for sensor in data['sensor']:
            identifier = str(sensor['basic_id']) + ' - ' + str(sensor['name'])
            dataframe = DataFrame(
                identifier = identifier,
                name       = sensor['type'],
                value      = sensor['parameter']['index']['value'],
                unit       = sensor['parameter']['index']['unit'],
                room       = sensor['basic_id']
            )
            dataframe_list.append(dataframe)

        # get sensor per room information
        for key, roomnr in data['room'].items(): # loop over the available rooms
            room_list.append(key)
            for sensor in roomnr['sensor']: # dive into sensors per room
                # jump into parameter -> first dict in this dict -> get unit and value
                for key, value in sensor['parameter'].items():
                    sub_key    = key
                    sub_value  = value['value']
                    sub_unit   = value['unit']
                    identifier = str(sensor['basic_id']) + ' - ' +  str(sensor['name'] + ' - ' + str(sub_key))

                    dataframe = DataFrame(
                        identifier = identifier,
                        name       = sensor['type'],
                        value      = sub_value,
                        unit       = sub_unit,
                        room       = sensor['basic_id']
                    )
                    dataframe_list.append(dataframe)
        return dataframe_list, room_list

    def _sync_variables(self):
        # Function to sync variables from HealthBox3 to gateway cache
        # Get values from healthbox
        resp = self._perform_get_request(HealthBox3Driver.Endpoints.DATA)
        if resp is None:
            return
        if resp.status_code != 200:
            return
        data_json = resp.json()

        # process values
        dataframe_list, room_list = self._extract_data(data_json)
        # upsert values
        self.hbs.upsert_from_dataframe_list(dataframe_list)
        self.hbs.available_rooms = room_list

    def _sync_periodically(self):
        """ General sync function to sync all data with the device """
        while self.is_running:
            try:
                time.sleep(self.sync_delay)
                self._sync_variables()
            except KeyboardInterrupt:
                self.stop()

    class Endpoints:
        def __init__(self):
            pass
        DATA = '/v2/api/data/current'

class HealthBox3Manager:
    LISTEN_PORT = 49152  # The port to listen on to receive the reply packages back
    DISCOVER_PORT = 49152  # The port to send the discover package to
    DISCOVER_IP = '255.255.255.255'
    DISCOVER_MESSAGE = 'RENSON_DEVICE/JSON?'
    DEVICE_TYPE = 'HEALTHBOX3'

    def __init__(self):
        # discovery elements
        self.is_discovering = False
        self.discovered_devices = [] # List of ip's
        self.discover_socket = None
        self.discover_callback = None

        self.send_discovery_packet_thread = Thread(target=self._send_discovery_packet)
        self.send_discovery_packet_thread.daemon = True

    def _send_discovery_packet(self):
        while self.is_discovering:
            self.discover_socket.sendto(
                HealthBox3Manager.DISCOVER_MESSAGE,
                ('<broadcast>', HealthBox3Manager.DISCOVER_PORT)
            )
            receiving = True
            while receiving:
                try:
                    received = self.discover_socket.recvfrom(1024)
                    response_check = HealthBox3Manager._check_received_packet_for_discovery(received)
                    if response_check is not None:
                        if response_check not in self.discovered_devices:
                            self.discovered_devices.append(response_check)
                            if self.discover_callback is not None:
                                self.discover_callback(response_check)
                except KeyboardInterrupt:
                    receiving = False
                    self.is_discovering = False
                except Exception:
                    time.sleep(2)
                    receiving = False

    @staticmethod
    def _check_received_packet_for_discovery(packet):
        # type: (Tuple[str, Tuple[str, int]]) -> Optional[str]
        if not isinstance(packet, tuple):
            return None
        content = packet[0]
        try:
            content_json = json.loads(content)
            if 'Device' in content_json and 'IP' in content_json:
                device_type = content_json['Device']
                device_ip = content_json['IP']
                if device_type == HealthBox3Manager.DEVICE_TYPE:
                    return device_ip
        except:
            return None
        return None

    def set_discovery_callback(self, callback):
        if not callable(callback):
            raise HealthBox3Exception("Could not set callback: {}, not a callable type".format(callback))
        self.discover_callback = callback

    def get_serial(self, ip):
        hbd = HealthBox3Driver(ip=ip)
        serial = hbd.get_variable('serial')
        return serial

    def start_discovery(self):
        if self.discover_socket is None:
            self.discover_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # creating a new UDP socket
            self.discover_socket.bind(('', HealthBox3Manager.LISTEN_PORT))  # listen on socket on discover port
            self.discover_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # enable broadcast on socket
            self.discover_socket.settimeout(2.0)
        self.is_discovering = True
        if not self.send_discovery_packet_thread.is_alive():
            self.send_discovery_packet_thread.start()

    def stop_discovery(self):
        self.is_discovering = False
        if self.send_discovery_packet_thread.is_alive():
            self.send_discovery_packet_thread.join(timeout=5)
        if self.discover_socket is not None:
            self.discover_socket.close()
            self.discover_socket = None


    def test(self):
        # testing the code
        # searching the healthboxes
        hbm = HealthBox3Manager()
        hbm.is_discovering = True
        hbm.discover_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # creating a new UDP socket
        hbm.discover_socket.bind(('', HealthBox3Manager.LISTEN_PORT))  # listen on socket on discover port
        hbm.discover_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # enable broadcast on socket
        hbm.discover_socket.settimeout(2.0)
        hbm._send_discovery_packet()
        ip = hbm.discovered_devices[0]
        print(ip)
        # pull info from the first healthbox
        healthbox = HealthBox3Driver(ip = ip)
        healthbox._sync_variables()
        print(healthbox.get_list_of_variables())
        print(healthbox.get_variable('serial'))
        print(healthbox.get_variable('2 - indoor air quality[2]_HealthBox 3[Healthbox3] - co2'))
