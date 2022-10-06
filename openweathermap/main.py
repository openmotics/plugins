"""
An OpenWeatherMap plugin
"""

import six
import time
import requests
import json
from plugins.base import om_expose, output_status, OMPluginBase, PluginConfigChecker, background_task
import logging

logger = logging.getLogger(__name__)

class OpenWeatherMap(OMPluginBase):
    """
    An OpenWeatherMap plugin
    """

    name = 'OpenWeatherMap'
    version = '2.0.1'
    interfaces = [('config', '1.0')]

    config_description = [{'name': 'api_key',
                           'type': 'str',
                           'description': 'The API key from OpenWeatherMap.'},
                          {'name': 'lat',
                           'type': 'str',
                           'description': 'A location latitude which will be passed to OpenWeatherMap.'},
                          {'name': 'lng',
                           'type': 'str',
                           'description': 'A location longitude which will be passed to OpenWeatherMap.'},
                           {'name': 'Virtual sensors and forecast time offset',
                           'type': 'section',
                           'description': 'Sensor registration and time_offset configuration (in minutes and only positive int values)',
                           'repeat': True,
                           'min': 0,
                           'content': [{'name': 'sensor_name', 'type': 'str'},
                                       {'name': 'time_offset', 'type': 'int'}]}]

    default_config = {'api_key': ''}

    def __init__(self, webinterface, connector):
        super(OpenWeatherMap, self).__init__(webinterface=webinterface,
                                                connector=connector)

        logger.info('Starting OpenWeatherMap plugin...')

        self._config = self.read_config(OpenWeatherMap.default_config)
        self._config_checker = PluginConfigChecker(OpenWeatherMap.config_description)

        self._read_config()

        self._registered = False
        self._sensor_dtos = {}

        self._previous_output_state = {}

        logger.info("Started OpenWeatherMap plugin")

    def _read_config(self):
        self._api_key = self._config.get('api_key', '')

        sensors_config = self._config.get('Virtual sensors and forecast time offset', [])
        self._sensor_time_dict = {}
        for i in range(len(sensors_config)):
            self._sensor_time_dict[sensors_config[i]['sensor_name']] = sensors_config[i]['time_offset']

        self._time_offsets = self._sensor_time_dict.values()
        self._sensors_names = self._sensor_time_dict.keys()
        logger.info(f"Time offsets: {self._time_offsets} and sensor_names: {self._sensors_names}")
        
        self._forecast_endpoint = 'http://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&units=metric&appid={api_key}'
        self._current_endpoint = 'http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&units=metric&appid={api_key}'

        self._headers = {'X-Requested-With': 'OpenMotics plugin: OpenWeatherMap'}

        self._enabled = False
        if (self._config.get('lat', '') != '') and (self._config.get('lng', '') != ''):
            self._latitude = self._config.get('lat')
            self._longitude = self._config.get('lng')
            logger.info('Latitude: {0} - Longitude: {1}'.format(self._latitude, self._longitude))
            self._enabled = True

        self._enabled = self._enabled and self._api_key != ''
        logger.info('OpenWeatherMap is {0}'.format('enabled' if self._enabled else 'disabled'))

    @background_task
    def run(self):
        previous_values = {}
        accuracy = 5
        if not self._registered:
            self._register_sensors()
        while True:
            if self._enabled and self._registered:
                start = time.time()
                sensor_values = {}
                calls = 0
                for s, t in self._sensor_time_dict.items():
                    if t > 0:
                        try:
                            calls += 1
                            response = requests.get(url=self._forecast_endpoint.format(lat=self._latitude,
                                                                                        lon=self._longitude,
                                                                                        api_key=self._api_key),
                                                    headers=self._headers)
                            if response.status_code != 200:
                                logger.error('Forecast call failed: {0}'.format(response.json()['message']))
                            else:
                                result = response.json()['list']
                                wanted_time = start + (t * 60)
                                selected_entry = None
                                for entry in result:
                                    if selected_entry is None or abs(entry['dt'] - wanted_time) < abs(selected_entry['dt'] - wanted_time):
                                        selected_entry = entry
                                if selected_entry is None:
                                    logger.error(f'Could not find forecast for virtual sensor {s}')
                                    continue
                                sensor_values[s] = [selected_entry['main']['temp'], selected_entry['main']['humidity'], None]
                        except Exception as ex:
                            logger.exception('Error while fetching forecast temperatures')
                    elif t == 0:
                        try:
                            calls += 1
                            response = requests.get(url=self._current_endpoint.format(lat=self._latitude,
                                                                                    lon=self._longitude,
                                                                                    api_key=self._api_key),
                                                    headers=self._headers)
                            if response.status_code != 200:
                                logger.error('Current weather call failed: {0}'.format(response.json()['message']))
                            else:
                                result = response.json()
                                sensor_values[s] = [result['main']['temp'], result['main']['humidity'], None]
                        except Exception as ex:
                            logger.exception('Error while fetching current temperatures')

                # Push all sensor data        
                for sname, values in sensor_values.items():
                    if values[0] != previous_values.get(0):
                        logger.info('Updating sensor {0} to temp: {1}'.format(sname,
                                                                                                values[0] if values[0] is not None else '-'))
                    previous_values[0] = values[0]  # Only temperature
                    try:
                        if self._registered:
                            logger.info(f"Setting virtual sensor {sname} to: {values[0]}")
                            self.connector.sensor.report_state(sensor=self._sensor_dtos[sname],
                                                            value=values[0])
                    except Exception:
                        logger.exception('Error while reporting sensor state')

                # Wait a given amount of seconds
                sleep = 60 * calls - (time.time() - start) + 1
                if sleep < 0:
                    sleep = 1
                time.sleep(sleep)
            else:
                time.sleep(5)

    @om_expose
    def get_config_description(self):
        return json.dumps(OpenWeatherMap.config_description)

    @om_expose
    def get_config(self):
        return json.dumps(self._config)

    @om_expose
    def set_config(self, config):
        config = json.loads(config)
        for key in config:
            if isinstance(config[key], six.string_types):
                config[key] = str(config[key])
        self._config_checker.check_config(config)
        self._config = config
        self._read_config()
        self.write_config(config)
        return json.dumps({'success': True})

    def _register_sensors(self):
        ext_id = 111111
        for s in self._sensors_names:
            logger.info(f'Registering Temperature sensor with name {s}')            
            try:
                sensor = self.connector.sensor.register_temperature_celcius(external_id=str(ext_id),
                                                                            name=s)
                logger.info(f'Registered {s} with id {ext_id}')
                self._sensor_dtos[s]=sensor
            except Exception:
                logger.exception('Error registering sensor')
                self._registered = False
            finally:
                ext_id += 1
        self._registered = True