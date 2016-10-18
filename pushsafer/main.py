"""
A Pushsafer (http://www.pushsafer.com) plugin for pushing events through Pushsafer
"""

import requests
import collections
import simplejson as json
from threading import Thread
from plugins.base import om_expose, input_status, output_status, OMPluginBase, PluginConfigChecker


class Pushsafer(OMPluginBase):
    """
    A Pushsafer (http://www.pushsafer.com) plugin for pushing events through Pushsafer
    """

    name = 'Pushsafer'
    version = '1.0.1'
    interfaces = [('config', '1.0')]

    config_description = [{'name': 'privatekey',
                           'type': 'str',
                           'description': 'Your Private or Alias key.'},
                          {'name': 'input_id',
                           'type': 'int',
                           'description': 'The ID of the input that will trigger the event.'},
                          {'name': 'message',
                           'type': 'str',
                           'description': 'The message to be send.'}
                          {'name': 'title',
                           'type': 'str',
                           'description': 'The title of message to be send.'}
                          {'name': 'device',
                           'type': 'str',
                           'description': 'The device or device group id where the message to be send.'}
                          {'name': 'icon',
                           'type': 'str',
                           'description': 'The icon which is displayed with the message (a number 1-98).'}
                          {'name': 'sound',
                           'type': 'str',
                           'description': 'The notification sound of message (a number 0-28 or empty).'}
                          {'name': 'vibration',
                           'type': 'str',
                           'description': 'How often the device should vibrate (a number 1-3 or empty).'}
                          {'name': 'url',
                           'type': 'str',
                           'description': 'A URL or URL scheme: https://www.pushsafer.com/en/url_schemes'}
                          {'name': 'urltitle',
                           'type': 'str',
                           'description': 'the URLs title'}
                          {'name': 'time2live',
                           'type': 'str',
                           'description': 'Integer number 0-43200: Time in minutes after which message automatically gets purged.'}]

    default_config = {'privatekey': '', 'input_id': -1, 'message': '', 'title': 'OpenMotics', 'device': '', 'icon': '1', 'sound': '', 'vibration': '', 'url': '', 'urltitle': '', 'time2live': ''}

    def __init__(self, webinterface, logger):
        super(Pushsafer, self).__init__(webinterface, logger)
        self.logger('Starting Pushsafer plugin...')

        self._config = self.read_config(Pushsafer.default_config)
        self._config_checker = PluginConfigChecker(Pushsafer.config_description)

        self._read_config()

        self.logger("Started Pushsafer plugin")

    def _read_config(self):
        self._privatekey = self._config['privatekey']
        self._input_id = self._config['input_id']
        self._message = self._config['message']
        self._title = self._config['title']
        self._device = self._config['device']
        self._icon = self._config['icon']
        self._sound = self._config['sound']
        self._vibration = self._config['vibration']
        self._url = self._config['url']
        self._urltitle = self._config['urltitle']
        self._time2live = self._config['time2live']

        self._endpoint = 'https://www.pushsafer.com/api'
        self._headers = {'Content-type': 'application/x-www-form-urlencoded',
                         'X-Requested-With': 'OpenMotics plugin: Pushsafer'}

        self._enabled = self._privatekey != '' and self._message != ''

    def convert(self,data):
        if isinstance(data,basestring):
            return str(data)
        elif isinstance(data,collections.Mapping):
            return dict(map(self.convert, data.iteritems()))
        elif isinstance(data,collections.Iterable):
            return type(data)(map(self.convert,data))
        else:
            return data

    @input_status
    def input_status(self, status):
        if self._enabled is True:
            input_id = status[0]
            if input_id == self._input_id:
                thread = Thread(target=self._process_input, args=(input_id,))
                thread.start()
            
    def _process_input(self,input_id):      
        try:
            data = {'k': self._privatekey,
                    'm': self._message,
                    't': self._title,
                    'd': self._device,
                    'i': self._icon,
                    's': self._sound,
                    'v': self._vibration,
                    'u': self._url,
                    'ut': self._urltitle,
                    'l': self._time2live}
            self.logger('Sending: {0}'.format(data))
            response = requests.post(url=self._endpoint,
                                     data=data,
                                     headers=self._headers,
                                     verify=False)
            self.logger('Received: {0} ({1})'.format(response.text, response.status_code))
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
