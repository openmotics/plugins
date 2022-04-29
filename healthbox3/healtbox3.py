import requests
import time
import json
from threading import Thread

class HealthBox3Exception(Exception):
    pass

class DataFrame:
    """" This will hold all the data for one variable in the Endura Delta device """
    def __init__(self,
    			 identifier,
                 name,
                 unit=None,
                 value=None,
                 description=None,
                 room=None,
                 ):
        # type: (str, str, str, int, str) -> None
		self.identifier  = identifier
		self.name        = name
		self.unit        = unit
		self.value       = value
		self.description = description
        self.room        = room

class HealtBox3Storage:
    def __init__(self):
        self.dataframes = {}  # type: Dict[str, DataFrame]

    def upsert_from_dataframe_list(self, dataframe_list):
        # type: (List[SingleDataFrame]) -> None
        """ receives a list of SingleDataFrames and creates a structure of dataframes """
        for dataframe in dataframe_list:
            if dataframe.identifier not in self.dataframes.keys():
                self.dataframes[dataframe.identifier] = dataframe
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

    def get_list_of_variables(self):
        # type: () -> List[str]
        """ returns a list of all the possible variables in the Endura Delta system """
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
        self._sync()
        self.sync_thread.start()

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
        if endpoint[0] == '/':
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
            if resp.status_code != 200:
                self.is_connected = False
            else:
                self.is_connected = True
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
        return self.hbs.get_value(name, index)

    def upsert_cached_variable(self, identifier, name=None, unit=None, value, description=None, room=None):
        # type: (str, str, Type, Any, str) -> bool
        """
        Will create/update a variable in the cache of the gateway
        """
        # check if we can update an existing value
        response = self.hbs.update_value(identifier=identifier, value=value)
        # if no existing value
        if not response:
            df = DataFrame(
                identifier = identifier,
                name=name,
                unit=unit,
                value=value,
                description=description,
                room=room,
            )

            self.hbs.add_single_dataframe(df)
            response = True
        return response

    def _extract_data(self, data):
        # boilerplate to be able to get the information out of the healthbox in a usable manner
        # type: (json response) -> list
        dataframe_list = []

        # get general (unnested) information
        for key, value in data.items():
            if not isinstance(value, list) and not isinstance(value, dict): # filtering out nested dicts and lists
                dataframe = DataFrame(
                    identifier=key, 
                    name=key, 
                    value=value
                )
                dataframe_list.append(dataframe)

        # get global information
        for key, value in data['global']['parameter'].items():
            dataframe = DataFrame(
                identifier=key, 
                name=key, 
                value=value['value']
            )
            dataframe_list.append(dataframe)

        # get global sensor information
        for sensor in data['sensor']:
            identifier = str(sensor['basic_id']) + ' - ' + str(sensor['name'])
            dataframe = DataFrame(
                identifier=identifier, 
                name=sensor['type'], 
                value=sensor['parameter']['index']['value'], 
                unit=sensor['parameter']['index']['unit'], 
                room=sensor['basic_id']
            )
            dataframe_list.append(dataframe)

        # get sensor information per room
        for key, roomnr in data['room'].items(): # loop over the available rooms
            for sensor in roomnr['sensor']: # dive into sensors per room
                identifier = str(sensor['basic_id']) + ' - ' + str(sensor['name'])

                # jump into parameter -> first dict in this dict -> get unit and value
                values_view = sensor['parameter'].values()
                value_iterator = iter(values_view)
                first_value = next(value_iterator)
                value = first_value['value']
                unit = first_value['unit']

                dataframe = DataFrame(
                    identifier=identifier, 
                    name=sensor['type'], 
                    value=value, 
                    unit=unit, 
                    room=sensor['basic_id']
                )
                dataframe_list.append(dataframe)
        return dataframe_list

    def _sync_variables(self):
        # Function to sync variables from HealthBox3 to gateway cache
        # Get values from healthbox
        resp = self._perform_get_request(EnduraDeltaDriver.Endpoints.DATA)
        if resp is None:
            return
        if resp.status_code != 200:
            return
        data_json = resp.json()

        # process values
        dataframe_list = self._extract_data(data_json)
        # upsert values
        self.dataframes.upsert_from_dataframe_list(dataframe_list)

    def _sync(self):
        """ General sync function to sync all data with the device """
        # TODO
        pass

    class Endpoints:
        def __init__(self):
            pass
        DATA = '/v2/api/data/current'
        