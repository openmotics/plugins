"""
A plugin to let two Gateways work together
"""

import six
import time
import requests
import json
from threading import Thread
from plugins.base import om_expose, output_status, OMPluginBase, PluginConfigChecker, background_task
import logging

logger = logging.getLogger(__name__)


class Syncer(OMPluginBase):
    """
    A syncer plugin to let two Gateways work together
    """

    name = 'Syncer'
    version = '0.0.5'
    interfaces = [('config', '1.0')]

    config_description = [{'name': 'gateway_ip',
                           'type': 'str',
                           'description': 'The IP address of the other Gateway'},
                          {'name': 'username',
                           'type': 'str',
                           'description': 'The (local) username for the other Gateway'},
                          {'name': 'password',
                           'type': 'str',
                           'description': 'The (local) password for the other Gateway'},
                          {'name': 'sensors',
                           'type': 'section',
                           'description': 'Mapping betweet local (virtual) sensors and remote (physical or virtual) sensors. Direction: from remote to local',
                           'repeat': True,
                           'min': 0,
                           'content': [{'name': 'local_sensor_id', 'type': 'int'},
                                       {'name': 'remote_sensor_id', 'type': 'int'}]},
                          {'name': 'outputs',
                           'type': 'section',
                           'description': 'Mapping betweet local (virtual) outputs and remote (physical or virtual) outputs. Direction: from local to remote',
                           'repeat': True,
                           'min': 0,
                           'content': [{'name': 'local_output_id', 'type': 'int'},
                                       {'name': 'remote_output_id', 'type': 'int'}]}]

    default_config = {}

    def __init__(self, webinterface, connector):
        super(Syncer, self).__init__(webinterface=webinterface,
                                    connector=connector)

        logger.info('Starting Syncer plugin...')

        self._config = self.read_config(Syncer.default_config)
        self._config_checker = PluginConfigChecker(Syncer.config_description)

        self._token = None
        self._enabled = False
        self._previous_outputs = set()
        self._read_config()

        logger.info("Started Syncer plugin")

    def _read_config(self):
        self._ip = self._config.get('gateway_ip', '')
        self._username = self._config.get('username', '')
        self._password = self._config.get('password', '')

        self._sensor_mapping = {}
        for entry in self._config.get('sensors', []):
            try:
                self._sensor_mapping[int(entry['local_sensor_id'])] = int(entry['remote_sensor_id'])
            except Exception as ex:
                logger.exception('Could not load temperature mapping')

        self._output_mapping = {}
        for entry in self._config.get('outputs', []):
            try:
                self._output_mapping[int(entry['local_output_id'])] = int(entry['remote_output_id'])
            except Exception as ex:
                logger.exception('Could not load output mapping')

        self._headers = {'X-Requested-With': 'OpenMotics plugin: Syncer'}
        self._endpoint = 'https://{0}/{{0}}'.format(self._ip)

        self._enabled = self._ip != '' and self._username != '' and self._password != ''

        logger.info('Syncer is {0}'.format('enabled' if self._enabled else 'disabled'))

    @background_task
    def run(self):
        previous_values = {}
        while True:
            if not self._enabled:
                time.sleep(30)
                continue
            try:
                # Sync sensor values:
                data_humidities = json.loads(self.webinterface.get_sensor_humidity_status(None))
                data_temperatures = json.loads(self.webinterface.get_sensor_temperature_status(None))
                if data_humidities['success'] is True and data_temperatures['success'] is True:
                    for sensor_id in range(len(data_temperatures['status'])):
                        if sensor_id not in self._sensor_mapping:
                            continue
                        data = {'sensor_id': sensor_id}
                        humidity = data_humidities['status'][sensor_id]
                        if humidity != 255:
                            data['humidity'] = humidity
                        temperature = data_temperatures['status'][sensor_id]
                        if temperature != 95.5:
                            data['temperature'] = temperature
                        previous = previous_values.setdefault(sensor_id, {})
                        if previous.get('temperature') != data.get('temperature') or \
                                previous.get('humidity') != data.get('humidity'):
                            previous_values[sensor_id] = data
                            self._call_remote('set_virtual_sensor', params=data)
            except Exception as ex:
                logger.exception('Error while syncing sensors')
            time.sleep(60)

    @output_status
    def output_status(self, status):
        if self._enabled is True:
            try:
                on_outputs = set()
                for entry in status:
                    on_outputs.add(entry[0])
                for output_id in on_outputs - self._previous_outputs:  # Outputs that are turned on
                    thread = Thread(target=self._call_remote,
                                    args=('set_output', {'id': output_id,
                                                         'is_on': '1'}))
                    thread.start()
                for output_id in self._previous_outputs - on_outputs:  # Outputs that are turned off
                    thread = Thread(target=self._call_remote,
                                    args=('set_output', {'id': output_id,
                                                         'is_on': '0'}))
                    thread.start()
                self._previous_outputs = on_outputs
            except Exception as ex:
                logger.exception('Error processing outputs')

    def _call_remote(self, api_call, params):
        # TODO: If there's an invalid_token error, call self._login() and try this call again
        try:
            if self._token is None:
                self._login()
            response = requests.get(self._endpoint.format(api_call),
                                    params=params,
                                    headers=self._headers)
            response_data = json.loads(response.text)
            if response_data.get('success', False) is False:
                logger.error('Could not execute API call {0}: {1}'.format(api_call, response_data.get('msg', 'Unknown error')))
        except Exception as ex:
            logger.exception('Unexpected error during API call {0}'.format(api_call))

    def _login(self):
        try:
            response = requests.get(self._endpoint.format('login'),
                                    params={'username': self._username,
                                            'password': self._password,
                                            'accept_terms': '1',
                                            'timeout': 60 * 60 * 24 * 30},
                                    headers=self._headers)
            response_data = json.loads(response.text)
            if response_data.get('success', False) is False:
                logger.error('Could not login: {0}'.format(response_data.get('msg', 'Unknown error')))
                self._token = None
            else:
                self._token = response_data.get('token')
                self._headers['Authorization'] = 'Bearer {0}'.format(self._token)
        except Exception as ex:
            logger.exception('Unexpected error during login')
            self._token = None

    @om_expose
    def get_config_description(self):
        return json.dumps(Syncer.config_description)

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
