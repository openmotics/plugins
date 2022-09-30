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
    version = '2.0.0'
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
                          {'name': 'time_offset',
                           'type': 'int',
                           'description': 'Time offset for forecast in minutes (only positive int values)'
                           },
                            # Not implemented yet, set to -1 in the meanwhile
                          {'name': 'uv_sensor_id',
                           'type': 'int',
                           'description': 'Not yet implemented, set to -1\nSensor ID for storing the UV index (the UV index will be set as temperature). -1 if not needed.'}]

    default_config = {'api_key': ''}

    def __init__(self, webinterface, connector):
        super(OpenWeatherMap, self).__init__(webinterface=webinterface,
                                                connector=connector)

        logger.info('Starting OpenWeatherMap plugin...')

        self._config = self.read_config(OpenWeatherMap.default_config)
        self._config_checker = PluginConfigChecker(OpenWeatherMap.config_description)

        self._read_config()

        self._previous_output_state = {}

        self._sensor_dto = None

        logger.info("Started OpenWeatherMap plugin")

    def _read_config(self):
        self._api_key = self._config.get('api_key', '')

        self._time_offset = self._config.get('time_offset')
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
        logger.info("Statring background task")
        if self._sensor_dto == None:
            logger.info("Registering the sensor - you should only see this log line once\n except for a race condition.")
            self._register_sensor()
        while True:
            if self._enabled:
                start = time.time()
                sensor_values = {}
                calls = 0
                if self._time_offset > 0:
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
                            wanted_time = start + (self._time_offset * 60)
                            selected_entry = None
                            for entry in result:
                                if selected_entry is None or abs(entry['dt'] - wanted_time) < abs(selected_entry['dt'] - wanted_time):
                                    selected_entry = entry
                            if selected_entry is None:
                                logger.error('Could not find forecast for virtual sensor {0}'.format(sensor_id))
                                continue
                            sensor_values[0] = [selected_entry['main']['temp'], selected_entry['main']['humidity'], None]
                    except Exception as ex:
                        logger.exception('Error while fetching forecast temperatures')
                elif self._time_offset == 0:
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
                            sensor_values[0] = [result['main']['temp'], result['main']['humidity'], None]
                    except Exception as ex:
                        logger.exception('Error while fetching current temperatures')
                # Currently there is no register_brightness_... in the sensor connector
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
                        logger.exception('Error while fetching UV index')

                # Push all sensor data                
                for _, values in sensor_values.items():
                    if values[0] != previous_values.get(0):
                        logger.info('Updating sensor {0} to temp: {1}'.format(self._sensor_dto.name,
                                                                                                values[0] if values[0] is not None else '-'))
                    previous_values[0] = values[0]  # Only temperature
                    try:
                        if self._sensor_dto:
                            logger.info(f"Setting virtual sensor to: {values[0]}")
                            self.connector.sensor.report_state(sensor=self._sensor_dto,
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

    def _register_sensor(self):
        logger.info('Registering Temperature sensor...')
        try:
            sensor = self.connector.sensor.register_temperature_celcius(external_id='222222',
                                                                        name='OWM-temp-sensor')
            logger.info('Registered %s' % sensor)
            self._sensor_dto = sensor
        except Exception:
            logger.exception('Error registering sensor')
            self._sensor_dto = None

    # TODO: also register a humidity sensor and set it's value
        # logger.info('Registering Humidity sensor...')
        # try:
        #     sensor = self.connector.sensor.register_humidity_percent(external_id='333333',
        #                                                                 name='OWM-humidity-sensor')
        #     logger.info('Registered %s' % sensor)
        #     self._sensor_dto = sensor
        # except Exception:
        #     logger.exception('Error registering sensor')
        #     self._sensor_dto = None