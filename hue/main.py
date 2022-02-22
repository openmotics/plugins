"""
A Hue plugin, for controlling lights connected to your Hue Bridge
"""
import six
import logging
import time
import requests
import simplejson as json
from six.moves.queue import Queue, Empty
from threading import Thread, Lock
from plugins.base import om_expose, output_status, OMPluginBase, PluginConfigChecker, background_task
from .plugin_logs import PluginLogHandler





if False:  # MYPY
    from typing import Dict, List, Optional, Callable

logger = logging.getLogger('openmotics')


class Hue(OMPluginBase):

    name = 'Hue'
    version = '1.1.2'
    interfaces = [('config', '1.0')]

    config_description = [{'name': 'api_url',
                           'type': 'str',
                           'description': 'The API URL of the Hue Bridge device. E.g. http://192.168.1.2/api'},
                          {'name': 'username',
                           'type': 'str',
                           'description': 'Hue Bridge generated username.'},
                          {'name': 'poll_frequency',
                           'type': 'int',
                           'description': 'The frequency used to pull the status of all outputs from the Hue bridge in seconds (0 means never)'},
                          {'name': 'output_mapping',
                           'type': 'section',
                           'description': 'Mapping between OpenMotics Virtual Outputs/Dimmers and Hue Outputs',
                           'repeat': True, 'min': 0,
                           'content': [{'name': 'output_id', 'type': 'int'},
                                       {'name': 'hue_output_id', 'type': 'int'}]}]

    default_config = {'api_url': 'http://hue/api', 'username': '', 'poll_frequency': 60}

    def __init__(self, webinterface, gateway_logger):
        self.setup_logging(log_function=gateway_logger)
        super(Hue, self).__init__(webinterface, logger)
        logger.info('Starting Hue plugin %s ...', self.version)

        self.discover_hue_bridges()

        self._config = self.read_config(Hue.default_config)
        self._config_checker = PluginConfigChecker(Hue.config_description)

        self._read_config()

        self._io_lock = Lock()
        self._output_event_queue = Queue(maxsize=256)

        logger.info("Hue plugin started")

    @staticmethod
    def setup_logging(log_function):  # type: (Callable) -> None
        logger.setLevel(logging.INFO)
        log_handler = PluginLogHandler(log_function=log_function)
        # some elements like time and name are added by the plugin runtime already
        # formatter = logging.Formatter('%(asctime)s - %(name)s - %(threadName)s - %(levelname)s - %(message)s')
        formatter = logging.Formatter('%(threadName)s - %(levelname)s - %(message)s')
        log_handler.setFormatter(formatter)
        logger.addHandler(log_handler)

    def _read_config(self):
        self._api_url = self._config['api_url']
        self._output_mapping = self._config.get('output_mapping', [])
        self._output = self._create_output_object()
        self._hue = self._create_hue_object()
        self._username = self._config['username']
        self._poll_frequency = self._config['poll_frequency']

        self._endpoint = '{0}/{1}/{{0}}'.format(self._api_url, self._username)

        self._enabled = self._api_url != '' and self._username != ''
        logger.info('Hue is {0}'.format('enabled' if self._enabled else 'disabled'))

    def _create_output_object(self):
        # create an object with the OM output IDs as the keys and hue light IDs as the values
        output_object = {}
        for entry in self._output_mapping:
            output_object[entry['output_id']] = entry['hue_output_id']
        return output_object

    def _create_hue_object(self):
        # create an object with the hue light IDs as the keys and OM output IDs as the values
        hue_object = {}
        for entry in self._output_mapping:
            hue_object[entry['hue_output_id']] = entry['output_id']
        return hue_object

    @output_status(version=2)
    def output_status(self, output_event):
        if self._enabled is True:
            try:
                output_id = output_event['id']
                state = output_event['status'].get('on')
                dimmer_level = output_event['status'].get('value')
                hue_light_id = self._output.get(output_id)
                if hue_light_id is not None:
                    logger.info('Switching output %s (hue id: %s) %s (dimmer: %s)', output_id, hue_light_id, 'ON' if state else 'OFF', dimmer_level)
                    data = (hue_light_id, state, dimmer_level)
                    self._output_event_queue.put(data)
                else:
                    logger.debug('Ignoring output %s, because it is not Hue'.format(output_id))
            except Exception as ex:
                logger.exception('Error processing output_status event: {0}'.format(ex))

    def _send(self, hue_light_id, state, dimmer_level):
        try:
            state = {'on': state}
            if dimmer_level is not None:
                state.update({'bri': self._dimmerLevelToBrightness(dimmer_level)})
            self._setLightState(hue_light_id, state)
        except Exception as ex:
            logger.exception('Error sending command to output with hue id: %s', hue_light_id)

    def _getLightState(self, hue_light_id):
        try:
            start = time.time()
            response = requests.get(url=self._endpoint.format('lights/{0}').format(hue_light_id))
            if response.status_code is 200:
                hue_light = response.json()
                logger.info('Getting output state for hue id: %s took %ss', hue_light_id, round(time.time() - start, 2))
                return hue_light
            else:
                logger.warning('Failed to pull state for hue id: %s', hue_light_id)
                return False
        except Exception as ex:
            logger.exception('Error while getting output state for hue id: %s', hue_light_id)

    def _setLightState(self, hue_light_id, state):
        try:
            start = time.time()
            response = requests.put(url=self._endpoint.format('lights/{0}/state').format(hue_light_id), data=json.dumps(state))
            if response.status_code is 200:
                result = response.json()
                if result[0].get('success')is None:
                    logger.info('Setting output state for Hue output {0} returned unexpected result. Response: {1} ({2})'.format(hue_light_id, response.text, response.status_code))
                    return False
                logger.info('Setting output state for hue id: %s took %ss', hue_light_id, round(time.time() - start, 2))
                return True
            else:
                logger.error('Setting output state for hue id: %s failed. Response: %s (%s)', hue_light_id, response.text, response.status_code)
                return False
        except Exception as ex:
            logger.exception('Error while setting output state for hue id: %s to %s', hue_light_id, json.dumps(state))

    def import_remote_state(self):
        if not self._output_event_queue.empty():
            logger.info('Ignoring syncing remote state because we still need to process %s output events', self._output_event_queue.qsize())
        else:
            try:
                self._import_lights_state()
            except Exception as ex:
                logger.exception('Error while getting state for all Hue outputs')
            try:
                self._import_sensors_state()
            except Exception as ex:
                logger.exception('Error while getting state for all Hue sensors')

    def _import_lights_state(self):
        logger.debug('Syncing remote state for all outputs from the Hue bridge')
        hue_lights = self._getAllLightsState()
        for output in self._output_mapping:
            output_id = output['output_id']
            hue_light_id = str(output['hue_output_id'])
            hue_light_state = hue_lights.get(hue_light_id)
            if hue_light_state is not None:
                if hue_light_state.get('on', False):
                    result = json.loads(self.webinterface.set_output(None, str(output_id), 'true', str(hue_light_state['dimmer_level'])))
                else:
                    result = json.loads(self.webinterface.set_output(None, str(output_id), 'false'))
                if result['success'] is False:
                    logger.error('Error when updating output %s (hue id: %s): %s', output_id, hue_light_id, result['msg'])
            else:
                logger.warning('Output %s (hue id:  %s) not found on Hue bridge', output_id, hue_light_id)

    def _import_sensors_state(self):
        logger.debug('Syncing remote state for all sensors from the Hue bridge')
        known_sensors = self._get_known_sensors()
        hue_sensors = self._getAllSensorsState()

        for hue_sensor_id, sensor in hue_sensors.items():
            sensor_external_id = sensor['external_id']
            if sensor_external_id not in known_sensors.keys():
                name = 'Hue Sensor {}'.format(hue_sensor_id)
                om_sensor_id = self._register_sensor(name, sensor_external_id)
            else:
                om_sensor_id = known_sensors[sensor_external_id]
            value = float(sensor.get('value'))
            if om_sensor_id is not None:
                self._update_sensor(om_sensor_id, value)
            else:
                logger.error('Hue sensor %s (%s) not found', hue_sensor_id, sensor_external_id)

    def _get_known_sensors(self):
        response = self.webinterface.get_sensor_configurations()
        data = json.loads(response)
        return {x['external_id']: x['id'] for x in data['config'] if x.get('source', {}).get('name') == Hue.name and x['external_id'] not in [None, '']}

    def _getAllSensorsState(self):
        hue_sensors = {}
        response = requests.get(url=self._endpoint.format('sensors'))
        if response.status_code is 200:
            for hue_sensor_id, data in response.json().iteritems():
                if data.get('type') == 'ZLLTemperature':
                    hue_sensors[hue_sensor_id] = self._parseSensorObject(hue_sensor_id, data, sensor_type='temperature')
        else:
            logger.error('Failed to pull state for all sensors (HTTP %s)', response.status_code)
        return hue_sensors

    def _getAllLightsState(self):
        hue_lights = {}
        response = requests.get(url=self._endpoint.format('lights'))
        if response.status_code is 200:
            for hue_light_id, data in response.json().iteritems():
                hue_lights[hue_light_id] = self._parseLightObject(hue_light_id, data)
        else:
            logger.error('Failed to pull state for all outputs (HTTP %s)', response.status_code)
        return hue_lights

    def _parseLightObject(self, hue_light_id, hue_light_object):
        light = {'id': hue_light_id}
        try:
            light.update({'name': hue_light_object['name'],
                          'on': hue_light_object['state'].get('on', False),
                          'brightness': hue_light_object['state'].get('bri', 254)})
            light['dimmer_level'] = self._brightnessToDimmerLevel(light['brightness'])
        except Exception as ex:
            logger.exception('Error while parsing Hue light %s', hue_light_object)
        return light

    def _parseSensorObject(self, hue_sensor_id, hue_sensor_object, sensor_type='temperature'):
        sensor = {'id': hue_sensor_id}
        try:
            value = hue_sensor_object['state'][sensor_type]
            if sensor_type == 'temperature':
                value /= 100.0
            sensor.update({'external_id': hue_sensor_object['uniqueid'],
                           'name': hue_sensor_object['name'],
                           'type': hue_sensor_object['type'],
                           'value': value})

        except Exception as ex:
            logger.exception('Error while parsing Hue sensor %s', hue_sensor_object)
        return sensor

    def _brightnessToDimmerLevel(self, brightness):
        return int(round(brightness / 2.54))

    def _dimmerLevelToBrightness(self, dimmer_level):
        return int(round(dimmer_level * 2.54))

    @background_task
    def run(self):
        if self._enabled:
            event_processor = Thread(target=self.output_event_processor, name='output_event_processor')
            event_processor.start()
            self.log_remote_asset_list()
            self.start_state_poller()

    def log_remote_asset_list(self):
        hue_lights = self._getAllLightsState()
        for hue_id, hue_light in hue_lights.iteritems():
            logger.info('Discovered hue output %s (hue id: %s)', hue_light.get('name'), hue_id)
        hue_sensors = self._getAllSensorsState()
        for hue_id, hue_sensor in hue_sensors.iteritems():
            logger.info('Discovered hue sensor %s (hue id: %s)', hue_sensor.get('name'), hue_id)

    def start_state_poller(self):
        while self._poll_frequency > 0:
            start = time.time()
            self.import_remote_state()
            # This loop will run approx. every 'poll_frequency' seconds
            sleep = self._poll_frequency - (time.time() - start)
            if sleep < 0:
                sleep = 1
            self.sleep(sleep)

    @om_expose
    def get_config_description(self):
        return json.dumps(Hue.config_description)

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

    def output_event_processor(self):
        while self._enabled:
            try:
                _latest_value_buffer = {}
                while True:
                    try:
                        hue_light_id, status, dimmer = self._output_event_queue.get(block=True, timeout=1)
                        _latest_value_buffer[hue_light_id] = (status, dimmer)  # this will ensure only the latest value is taken
                    except Empty:
                        break
                for hue_light_id, (status, dimmer) in _latest_value_buffer.iteritems():
                    self._send(hue_light_id, status, dimmer)
                    self.sleep(0.1)  # "throttle" requests to the bridge to avoid overloading
            except Exception as ex:
                if 'maintenance_mode' in ex.message:
                    logger.warning('System in maintenance mode. Processing paused for 1 minute.')
                    self.sleep(60)
                else:
                    logger.exception('Unexpected error processing output events')
                    self.sleep(10)

    def sleep(self, timer):
        now = time.time()
        expired = time.time() - now > timer
        while self._enabled and not expired:
            time.sleep(min(timer, 0.5))
            expired = time.time() - now > timer

            def _getLightState(self, hue_light_id):
                try:
                    start = time.time()
                    response = requests.get(url=self._endpoint.format('lights/{0}').format(hue_light_id))
                    if response.status_code is 200:
                        hue_light = response.json()
                        logger.info('Getting output state for hue id: %s took %ss', hue_light_id,
                                    round(time.time() - start, 2))
                        return hue_light
                    else:
                        logger.warning('Failed to pull state for hue id: %s', hue_light_id)
                        return False
                except Exception as ex:
                    logger.exception('Error while getting output state for hue id: %s', hue_light_id)

    def discover_hue_bridges(self):
        try:
            response = requests.get(url='https://discovery.meethue.com/')
            if response.status_code is 200:
                hue_bridge_data = response.json()
                for hue_bridge in hue_bridge_data:
                    logger.info('Discovered hue bridge %s @ %s',
                                hue_bridge.get('id'),
                                hue_bridge.get('internalipaddress'))
            else:
                logger.warning('Failed to discover bridges on this network')
                return False
        except Exception as ex:
            logger.exception('Error while discovering hue bridges on this network')

    def _register_sensor(self, name, external_id):
        logger.debug('Registering sensor with name %s and external_id %s', name, external_id)
        data = {
            'external_id': external_id,
            'source': {'type': 'plugin', 'name': Hue.name},
            'name': name,
            'physical_quantity': 'temperature',
            'unit': 'celcius',
        }
        response = self.webinterface.set_sensor_configuration(config=json.dumps(data))
        data = json.loads(response)
        if data is None or not data.get('success', False):
            logger.error('Could not register new sensor, registration failed trough API')
            logger.error(data)
            return None
        response = self.webinterface.get_sensor_configurations()
        data = json.loads(response)
        sensor_id = next((x['id'] for x in data['config'] if x.get('external_id') == external_id and x.get('source', {}).get('name') == Hue.name), None)
        logger.info('Registered new sensor with name %s and external_id %s', name, external_id)
        return sensor_id

    def _update_sensor(self, sensor_id, value):
        logger.debug('Updating sensor %s with status %s', sensor_id, value)
        data = {'id': sensor_id, 'value': value}
        response = self.webinterface.set_sensor_status(status=json.dumps(data))
        data = json.loads(response)
        if data is None or not data.get('success', False):
            logger.warning('Could not set the updated sensor value')
