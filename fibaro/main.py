"""
A Fibaro plugin, for controlling devices in your Fibaro Home Center (lite)
"""
import six
import time
import requests
import simplejson as json
from threading import Thread
from plugins.base import om_expose, output_status, OMPluginBase, PluginConfigChecker, background_task, om_metric_data


class Fibaro(OMPluginBase):
    """
    A Fibaro plugin, for controlling devices in your Fibaro Home Center (lite)
    """

    name = 'Fibaro'
    version = '2.0.18'
    interfaces = [('config', '1.0'),
                  ('metrics', '1.0')]

    config_description = [{'name': 'ip',
                           'type': 'str',
                           'description': 'The IP of the Fibaro Home Center (lite) device. E.g. 1.2.3.4'},
                          {'name': 'username',
                           'type': 'str',
                           'description': 'Username of a user with the required access.'},
                          {'name': 'password',
                           'type': 'str',
                           'description': 'Password of the user.'},
                          {'name': 'output_mapping',
                           'type': 'section',
                           'description': 'Mapping betweet OpenMotics (Virtual) Outputs and Fibaro Outputs',
                           'repeat': True,
                           'min': 0,
                           'content': [{'name': 'output_id', 'type': 'int'},
                                       {'name': 'fibaro_output_id', 'type': 'int'}]},
                          {'name': 'sensor_mapping',
                           'type': 'section',
                           'description': 'Mapping betweet OpenMotics Virtual Sensors and Fibaro Sensors',
                           'repeat': True,
                           'min': 0,
                           'content': [{'name': 'sensor_id', 'type': 'int'},
                                       {'name': 'fibaro_temperature_id', 'type': 'int'},
                                       {'name': 'fibaro_brightness_id', 'type': 'int'},
                                       {'name': 'fibaro_brightness_max', 'type': 'int'}]}]
    metric_definitions = [{'type': 'energy',
                           'tags': ['name', 'id', 'type'],
                           'metrics': [{'name': 'power',
                                        'description': 'Current power consumption',
                                        'type': 'gauge',
                                        'unit': 'W'},
                                       {'name': 'counter',
                                        'description': 'Total energy consumed',
                                        'type': 'counter',
                                        'unit': 'Wh'}]}]

    default_config = {'ip': '', 'username': '', 'password': ''}

    def __init__(self, webinterface, logger):
        super(Fibaro, self).__init__(webinterface, logger)
        self.logger('Starting Fibaro plugin...')

        self._config = self.read_config(Fibaro.default_config)
        self._config_checker = PluginConfigChecker(Fibaro.config_description)

        self._read_config()

        self._previous_output_state = {}

        self.logger("Started Fibaro plugin")

    def _read_config(self):
        self._ip = self._config['ip']
        self._output_mapping = self._config.get('output_mapping', [])
        self._sensor_mapping = self._config.get('sensor_mapping', [])
        self._username = self._config['username']
        self._password = self._config['password']

        self._endpoint = 'http://{0}/api/{{0}}'.format(self._ip)
        self._headers = {'X-Requested-With': 'OpenMotics plugin: Fibaro',
                         'X-Fibaro-Version': '2'}

        self._enabled = self._ip != '' and self._username != '' and self._password != ''
        self.logger('Fibaro is {0}'.format('enabled' if self._enabled else 'disabled'))

    @output_status
    def output_status(self, status):
        if self._enabled is True:
            try:
                active_outputs = []
                for entry in status:
                    active_outputs.append(entry[0])
                for entry in self._output_mapping:
                    output_id = entry['output_id']
                    fibaro_output_id = entry['fibaro_output_id']
                    is_on = output_id in active_outputs
                    key = '{0}_{1}'.format(output_id, fibaro_output_id)
                    if key in self._previous_output_state:
                        if is_on != self._previous_output_state[key]:
                            thread = Thread(target=self._send,
                                            args=('callAction', {'deviceID': fibaro_output_id,
                                                                 'name': 'turnOn' if is_on else 'turnOff'}))
                            thread.start()
                    else:
                        thread = Thread(target=self._send,
                                        args=('callAction', {'deviceID': fibaro_output_id,
                                                             'name': 'turnOn' if is_on else 'turnOff'}))
                        thread.start()
                    self._previous_output_state[key] = is_on
            except Exception as ex:
                self.logger('Error processing output_status event: {0}'.format(ex))

    def _send(self, action, data):
        try:
            url = self._endpoint.format(action)
            params = '&'.join(['{0}={1}'.format(key, value) for key, value in data.iteritems()])
            self.logger('Calling {0}?{1}'.format(url, params))
            response = requests.get(url=url,
                                    params=data,
                                    headers=self._headers,
                                    auth=(self._username, self._password))
            if response.status_code != 202:
                self.logger('Call failed, received: {0} ({1})'.format(response.text, response.status_code))
                return
            result = response.json()
            if result['result']['result'] not in [0, 1]:
                self.logger('Call failed, received: {0} ({1})'.format(response.text, response.status_code))
                return
        except Exception as ex:
            self.logger('Error during call: {0}'.format(ex))

    @background_task
    def run(self):
        while True:
            if self._enabled:
                start = time.time()
                try:
                    response = requests.get(url='http://{0}/api/devices'.format(self._ip),
                                            headers=self._headers,
                                            auth=(self._username, self._password))
                    if response.status_code != 200:
                        self.logger('Failed to load power devices')
                    else:
                        sensor_values = {}
                        result = response.json()
                        for device in result:
                            if 'properties' in device:
                                for sensor in self._sensor_mapping:
                                    sensor_id = sensor['sensor_id']
                                    if sensor.get('fibaro_temperature_id', -1) == device['id'] and 'value' in device['properties']:
                                        if sensor_id not in sensor_values:
                                            sensor_values[sensor_id] = [None, None, None]
                                        sensor_values[sensor_id][0] = max(-32.0, min(95.0, float(device['properties']['value'])))
                                    if sensor.get('fibaro_brightness_id', -1) == device['id'] and 'value' in device['properties']:
                                        if sensor_id not in sensor_values:
                                            sensor_values[sensor_id] = [None, None, None]
                                        limit = float(sensor.get('fibaro_brightness_max', 500))
                                        value = float(device['properties']['value'])
                                        sensor_values[sensor_id][2] = max(0.0, min(100.0, value / limit * 100))
                        for sensor_id, values in sensor_values.iteritems():
                            result = json.loads(self.webinterface.set_virtual_sensor(None, sensor_id, *values))
                            if result['success'] is False:
                                self.logger('Error when updating virtual sensor {0}: {1}'.format(sensor_id, result['msg']))
                except Exception as ex:
                    self.logger('Error while setting virtual sensors: {0}'.format(ex))
                # This loop should run approx. every 5 seconds
                sleep = 5 - (time.time() - start)
                if sleep < 0:
                    sleep = 1
                time.sleep(sleep)
            else:
                time.sleep(5)

    @om_metric_data(interval=15)
    def get_metric_data(self):
        if self._enabled:
            now = time.time()
            response = requests.get(url='http://{0}/api/devices'.format(self._ip),
                                    headers=self._headers,
                                    auth=(self._username, self._password))
            if response.status_code != 200:
                self.logger('Failed to load power devices')
                return
            result = response.json()
            for device in result:
                if 'properties' in device and 'power' in device['properties']:
                    yield {'type': 'energy',
                           'timestamp': now,
                           'tags': {'type': 'fibaro',
                                    'name': device['name'],
                                    'id': str(device['id'])},
                           'values': {'power': float(device['properties']['power']),
                                      'counter': float(device['properties']['energy']) * 1000}}

    @om_expose
    def get_config_description(self):
        return json.dumps(Fibaro.config_description)

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
