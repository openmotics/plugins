"""
An OpenWeatherMap plugin
"""

import six
import time
import requests
import simplejson as json
from plugins.base import om_expose, output_status, OMPluginBase, PluginConfigChecker, background_task
import logging

logger = logging.getLogger(__name__)

class OpenWeatherMap(OMPluginBase):
    """
    An OpenWeatherMap plugin
    """

    name = 'OpenWeatherMap'
    version = '1.0.2'
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
                          {'name': 'main_mapping',
                           'type': 'section',
                           'description': 'Mapping betweet OpenMotics Virtual Sensors and OpenWeatherMap forecasts. See README.',
                           'repeat': True,
                           'min': 0,
                           'content': [{'name': 'sensor_id', 'type': 'int'},
                                       {'name': 'time_offset', 'type': 'int'}]},
                          {'name': 'uv_sensor_id',
                           'type': 'int',
                           'description': 'Sensor ID for storing the UV index (the UV index will be set as temperature). -1 if not needed.'}]

    default_config = {'api_key': ''}

    def __init__(self, webinterface, connector):
        super(OpenWeatherMap, self).__init__(webinterface=webinterface,
                                                connector=connector)

        logger.info('Starting OpenWeatherMap plugin...')

        self._config = self.read_config(OpenWeatherMap.default_config)
        self._config_checker = PluginConfigChecker(OpenWeatherMap.config_description)

        self._read_config()

        self._previous_output_state = {}

        logger.info("Started OpenWeatherMap plugin")

    def _read_config(self):
        self._api_key = self._config.get('api_key', '')

        main_mapping = self._config.get('main_mapping', [])
        self._current_mapping = [entry for entry in main_mapping if entry['time_offset'] == 0]
        self._forecast_mapping = [entry for entry in main_mapping if entry['time_offset'] > 0]
        self._uv_sensor_id = int(self._config.get('uv_sensor_id', -1))

        self._uv_endpoint = 'http://api.openweathermap.org/v3/uvi/{lat},{lon}/{date}Z.json?appid={api_key}'
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
        while True:
            if self._enabled:
                start = time.time()
                sensor_values = {}
                calls = 0
                if len(self._forecast_mapping) > 0:
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
                            for sensor in self._forecast_mapping:
                                sensor_id = sensor['sensor_id']
                                wanted_time = start + (sensor['time_offset'] * 60)
                                selected_entry = None
                                for entry in result:
                                    if selected_entry is None or abs(entry['dt'] - wanted_time) < abs(selected_entry['dt'] - wanted_time):
                                        selected_entry = entry
                                if selected_entry is None:
                                    logger.error('Could not find forecast for virtual sensor {0}'.format(sensor_id))
                                    continue
                                sensor_values[sensor_id] = [selected_entry['main']['temp'], selected_entry['main']['humidity'], None]
                    except Exception as ex:
                        logger.exception('Error while fetching forecast temperatures: {0}'.format(ex))
                if len(self._current_mapping) > 0:
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
                            for sensor in self._current_mapping:
                                sensor_id = sensor['sensor_id']
                                sensor_values[sensor_id] = [result['main']['temp'], result['main']['humidity'], None]
                    except Exception as ex:
                        logger.exception('Error while fetching current temperatures: {0}'.format(ex))
                if 0 <= self._uv_sensor_id <= 31:
                    try:
                        execute = True
                        while execute is True:
                            calls += 1
                            lat, lon = round(self._latitude, accuracy), round(self._longitude, accuracy)
                            if accuracy == 0:
                                lat, lon = int(self._latitude), int(self._longitude)
                            response = requests.get(url=self._uv_endpoint.format(lat=lat, lon=lon,
                                                                                 date=time.strftime('%Y-%m-%d'),
                                                                                 api_key=self._api_key),
                                                    headers=self._headers)
                            result = response.json()
                            if response.status_code != 200:
                                logger.error('UV index call failed: {0}'.format(result['message']))
                                if result['message'] == 'not found':
                                    if accuracy > 0:
                                        accuracy = accuracy - 1
                                        execute = True
                                    else:
                                        execute = False
                                else:
                                    execute = False
                            else:
                                sensor_values[self._uv_sensor_id] = [result['data'], None, None]
                                execute = False
                    except Exception as ex:
                        logger.exception('Error while fetching UV index: {0}'.format(ex))
                # Push all sensor data
                try:
                    for sensor_id, values in sensor_values.items():
                        if values != previous_values.get(sensor_id, []):
                            logger.info('Updating sensor {0} to temp: {1}, humidity: {2}'.format(sensor_id,
                                                                                                 values[0] if values[0] is not None else '-',
                                                                                                 values[1] if values[1] is not None else '-'))
                        previous_values[sensor_id] = values
                        result = json.loads(self.webinterface.set_virtual_sensor(None, sensor_id, *values))
                        if result['success'] is False:
                            logger.error('Error when updating virtual sensor {0}: {1}'.format(sensor_id, result['msg']))
                except Exception as ex:
                    logger.exception('Error while setting virtual sensors: {0}'.format(ex))
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
