"""
A Pushetta (http://www.pushetta.com) plugin for pushing events through Pushetta
"""

import requests
import simplejson as json
from plugins.base import om_expose, input_status, output_status, OMPluginBase, PluginConfigChecker


class Pushetta(OMPluginBase):
    """
    A Pushetta (http://www.pushetta.com) plugin for pushing events through Pushetta
    """

    name = 'Pushetta'
    version = '1.0.11'
    interfaces = [('config', '1.0')]

    config_description = [{'name': 'api_key',
                           'type': 'str',
                           'description': 'Your API key.'},
                          {'name': 'input_id',
                           'type': 'int',
                           'description': 'The ID of the input that will trigger the event.'},
                          {'name': 'channel',
                           'type': 'str',
                           'description': 'The channel to push the event to.'},
                          {'name': 'message',
                           'type': 'str',
                           'description': 'The message to be send.'}]

    default_config = {'api_key': '', 'input_id': -1, 'channel': '', 'message': ''}

    def __init__(self, webinterface, logger):
        super(Pushetta, self).__init__(webinterface, logger)
        self.logger('Starting Pushetta plugin...')

        self._config = self.read_config(Pushetta.default_config)
        self._config_checker = PluginConfigChecker(Pushetta.config_description)

        self._read_config()

        self.logger("Started Pushetta plugin")

    def _read_config(self):
        self._api_key = self._config['api_key']
        self._input_id = self._config['input_id']
        self._channel = self._config['channel']
        self._message = self._config['message']

        self._endpoint = 'http://api.pushetta.com/api/pushes/{0}/'.format(self._channel)
        self._headers = {'Accept': 'application/json',
                         'Authorization': 'Token {0}'.format(self._api_key),
                         'Content-type': 'application/json',
                         'X-Requested-With': 'OpenMotics plugin: Pushetta'}

        self._enabled = self._api_key != '' and self._input_id > -1 and self._channel != '' and self._message != ''

    @input_status
    def input_status(self, status):
        if self._enabled is True:
            input_id = status[0]
            if input_id == self._input_id:
                try:
                    data = json.dumps({'body': self._message,
                                       'message_type': 'text/plain'})
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
        return json.dumps(Pushetta.config_description)

    @om_expose
    def get_config(self):
        return json.dumps(self._config)

    @om_expose
    def set_config(self, config):
        config = json.loads(config)
        self._config_checker.check_config(config)
        self._config = config
        self._read_config()
        self.write_config(config)
        return json.dumps({'success': True})
