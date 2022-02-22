"""
A Pushsafer (http://www.pushsafer.com) plugin for pushing events through Pushsafer
"""

import collections
import time
import requests
import simplejson as json
from threading import Thread
from plugins.base import om_expose, input_status, OMPluginBase, PluginConfigChecker


class Pushsafer(OMPluginBase):
    """
    A Pushsafer (http://www.pushsafer.com) plugin for pushing events through Pushsafer
    """

    name = 'Pushsafer'
    version = '2.1.1'
    interfaces = [('config', '1.0')]

    config_description = [{'name': 'privatekey',
                           'type': 'str',
                           'description': 'Your Private or Alias key.'},
                          {'name': 'input_mapping',
                           'type': 'section',
                           'description': 'The mapping between input_id and a given Pushsafer settings',
                           'repeat': True,
                           'min': 1,
                           'content': [{'name': 'input_id',
                                        'type': 'int',
                                        'description': 'The ID of the (virtual) input that will trigger the event.'},
                                       {'name': 'message',
                                        'type': 'str',
                                        'description': 'The message to be send.'},
                                       {'name': 'title',
                                        'type': 'str',
                                        'description': 'The title of message to be send.'},
                                       {'name': 'device',
                                        'type': 'str',
                                        'description': 'The device or device group id where the message to be send.'},
                                       {'name': 'icon',
                                        'type': 'str',
                                        'description': 'The icon which is displayed with the message (a number 1-98).'},
                                       {'name': 'sound',
                                        'type': 'int',
                                        'description': 'The notification sound of message (a number 0-28 or empty).'},
                                       {'name': 'vibration',
                                        'type': 'str',
                                        'description': 'How often the device should vibrate (a number 1-3 or empty).'},
                                       {'name': 'url',
                                        'type': 'str',
                                        'description': 'A URL or URL scheme: https://www.pushsafer.com/en/url_schemes'},
                                       {'name': 'urltitle',
                                        'type': 'str',
                                        'description': 'the URLs title'},
                                       {'name': 'time2live',
                                        'type': 'str',
                                        'description': 'Integer number 0-43200: Time in minutes after which message automatically gets purged.'}]}]

    default_config = {'privatekey': '', 'input_id': -1, 'message': '', 'title': 'OpenMotics', 'device': '', 'icon': '1', 'sound': '', 'vibration': '',
                      'url': '', 'urltitle': '', 'time2live': ''}

    def __init__(self, webinterface, logger):
        super(Pushsafer, self).__init__(webinterface, logger)
        self.logger('Starting Pushsafer plugin...')

        self._config = self.read_config(Pushsafer.default_config)
        self._config_checker = PluginConfigChecker(Pushsafer.config_description)

        self._cooldown = {}
        self._read_config()

        self.logger("Started Pushsafer plugin")

    def _read_config(self):
        self._privatekey = self._config['privatekey']
        self._mapping = self._config.get('input_mapping', [])

        self._endpoint = 'https://www.pushsafer.com/api'
        self._headers = {'Content-type': 'application/x-www-form-urlencoded',
                         'X-Requested-With': 'OpenMotics plugin: Pushsafer'}

        self._enabled = self._privatekey != '' and len(self._mapping) > 0
        self.logger('Pushsafer is {0}'.format('enabled' if self._enabled else 'disabled'))

    def convert(self, data):
        try:
            basestring
        except NameError:
            basestring = str
        if isinstance(data, basestring):
            return str(data)
        elif isinstance(data, collections.Mapping):
            return dict(map(self.convert, data.iteritems()))
        elif isinstance(data, collections.Iterable):
            return type(data)(map(self.convert, data))
        else:
            return data

    @input_status
    def input_status(self, status):
        now = time.time()
        if self._enabled is True:
            input_id = status[0]
            if self._cooldown.get(input_id, 0) > now - 10:
                self.logger('Ignored duplicate Input in 10 seconds.')
                return
            data_send = False
            for mapping in self._mapping:
                if input_id == mapping['input_id']:
                    data = {'k': self._privatekey,
                            'm': mapping['message'],
                            't': mapping['title'],
                            'd': mapping['device'],
                            'i': mapping['icon'],
                            's': mapping['sound'],
                            'v': mapping['vibration'],
                            'u': mapping['url'],
                            'ut': mapping['urltitle'],
                            'l': mapping['time2live']}
                    thread = Thread(target=self._send_data, args=(data,))
                    thread.start()
                    data_send = True
            if data_send is True:
                self._cooldown[input_id] = now

    def _send_data(self, data):
        try:
            self.logger('Sending data')
            response = requests.post(url=self._endpoint,
                                     data=data,
                                     headers=self._headers,
                                     verify=False)
            if response.status_code != 200:
                self.logger('Got error response: {0} ({1})'.format(response.text, response.status_code))
            else:
                result = json.loads(response.text)
                if result['status'] != 1:
                    self.logger('Got error response: {0}'.format(result['error']))
                else:
                    self.logger('Got reply: {0}'.format(result['success']))
                    quotas = []
                    for data in result['available'].values():
                        device = data.keys()[0]
                        quotas.append('{0}: {1}'.format(device, data[device]))
                    self.logger('Remaining quotas: {0}'.format(', '.join(quotas)))
        except Exception as ex:
            self.logger('Error sending: {0}'.format(ex))

    @om_expose
    def get_config_description(self):
        return json.dumps(Pushsafer.config_description)

    @om_expose
    def get_config(self):
        return json.dumps(self._config)

    @om_expose
    def set_config(self, config):
        config = json.loads(config)
        config = self.convert(config)
        self._config_checker.check_config(config)
        self._config = config
        self._read_config()
        self.write_config(config)
        return json.dumps({'success': True})
