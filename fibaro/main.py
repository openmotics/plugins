"""
A Fibaro plugin, for controlling devices in your Fibaro Home Center (lite)
"""

import requests
import simplejson as json
from threading import Thread
from plugins.base import om_expose, receive_events, OMPluginBase, PluginConfigChecker


class Fibaro(OMPluginBase):
    """
    A Fibaro plugin, for controlling devices in your Fibaro Home Center (lite)
    """

    name = 'Fibaro'
    version = '0.3.1'
    interfaces = [('config', '1.0')]

    config_description = [{'name': 'ip',
                           'type': 'str',
                           'description': 'The IP of the Fibaro Home Center (lite) device. E.g. 1.2.3.4'},
                          {'name': 'username',
                           'type': 'str',
                           'description': 'Username of a user with the required access.'},
                          {'name': 'password',
                           'type': 'str',
                           'description': 'Password of the user.'},
                          {'name': 'mapping',
                           'type': 'str',
                           'description': 'A JSON formatted single-line string containing the Event Code - Action mapping. See README.md for more information.'}]

    default_config = {'ip': '', 'username': '', 'password': '', 'mapping': '{}'}

    def __init__(self, webinterface, logger):
        super(Fibaro, self).__init__(webinterface, logger)
        self.logger('Starting Fibaro plugin...')

        self._config = self.read_config(Fibaro.default_config)
        self._config_checker = PluginConfigChecker(Fibaro.config_description)

        self._read_config()

        self.logger("Started Fibaro plugin")

    def _read_config(self):
        self._ip = self._config['ip']
        self._mapping = json.loads(self._config['mapping'])
        self._username = self._config['username']
        self._password = self._config['password']

        self._endpoint = 'http://{0}/api/callAction'.format(self._ip)
        self._headers = {'X-Requested-With': 'OpenMotics plugin: Fibaro',
                         'X-Fibaro-Version': '2'}

        self._enabled = self._ip != '' and self._username != '' and self._password != ''
        self.logger('Fibaro is {0}'.format('enabled' if self._enabled else 'disabled'))

    @receive_events
    def recv_events(self, code):
        if self._enabled is True:
            try:
                self.logger('Got event {0}'.format(code))
                code = str(code)
                if code in self._mapping:
                    data = self._mapping[code]
                    thread = Thread(target=self._send, args=(data,))
                    thread.start()
                else:
                    self.logger('No mapping for event {0}'.format(code))
                self.logger('Event {0} processed'.format(code))
            except Exception as ex:
                self.logger('Error processing event: {0}'.format(ex))

    def _send(self, data):
        for entry in data:
            try:
                response = requests.get(url=self._endpoint,
                                        params=entry,
                                        headers=self._headers,
                                        auth=(self._username, self._password))
                self.logger('Executed GET {0}'.format(response.url))
                if response.status_code != 202:
                    self.logger('Send failed, received: {0} ({1})'.format(response.text, response.status_code))
                    return
                result = response.json()
                if result['result']['result'] != 1:
                    self.logger('Send failed, received: {0} ({1})'.format(response.text, response.status_code))
                    return
                self.logger('Action executed on Fibaro API')
            except Exception as ex:
                self.logger('Error sending: {0}'.format(ex))

    @om_expose
    def get_power_usage(self):
        if self._enabled:
            response = requests.get(url='http://{0}/api/devices'.format(self._ip),
                                    headers=self._headers,
                                    auth=(self._username, self._password))
            if response.status_code != 200:
                self.logger('Failed to load power devices')
                return json.dumps({'success': False, 'error': 'Could not load power devices'})
            result = response.json()
            devices = {}
            for device in result:
                if 'properties' in device and 'power' in device['properties']:
                    devices[device['id']] = {'id': device['id'],
                                             'name': device['name'],
                                             'power': float(device['properties']['power']),
                                             'counter': float(device['properties']['energy']) * 1000}
            return json.dumps({'success': True, 'result': devices})
        else:
            return json.dumps({'success': False, 'error': 'Fibaro plugin not enabled'})

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
            if isinstance(config[key], basestring):
                config[key] = str(config[key])
        self._config_checker.check_config(config)
        self._config = config
        self._read_config()
        self.write_config(config)
        return json.dumps({'success': True})
