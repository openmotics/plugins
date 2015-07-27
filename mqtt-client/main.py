"""
An MQTT client plugin for sending/receiving data to/from an MQTT broker.
For more info: https://github.com/openmotics/plugins/blob/master/mqtt-client/README.md
"""

import time
import simplejson as json
from subprocess import check_output
from plugins.base import om_expose, input_status, output_status, OMPluginBase, PluginConfigChecker


class MQTTClient(OMPluginBase):
    """
    An MQTT client plugin for sending/receiving data to/from an MQTT broker.
    For more info: https://github.com/openmotics/plugins/blob/master/mqtt-client/README.md
    """

    name = 'MQTTClient'
    version = '1.0.14'
    interfaces = [('config', '1.0')]

    config_description = [{'name': 'broker_ip',
                           'type': 'str',
                           'description': 'IP or hostname of the MQTT broker.'},
                          {'name': 'broker_port',
                           'type': 'int',
                           'description': 'Port of the MQTT broker. Default: 1883'},
                          {'name': 'send_events',
                           'type': 'bool',
                           'description': 'Send input/output events. Default: True'}]

    default_config = {'broker_port': 1883, 'send_events': False}

    def __init__(self, webinterface, logger):
        super(MQTTClient, self).__init__(webinterface, logger)
        self.logger('Starting MQTTClient plugin...')

        self._config = self.read_config(MQTTClient.default_config)
        self._config_checker = PluginConfigChecker(MQTTClient.config_description)

        try:
            import paho.mqtt.client as client
        except ImportError:
            check_output('mount -o remount,rw /', shell=True)
            check_output('pip install paho-mqtt', shell=True)
            check_output('mount -o remount,ro /', shell=True)
            import paho.mqtt.client as client

        self.client = client.Client()
        self.client.connect(self._config['broker_ip'], self._config['broker_port'], 5)
        self.client.loop_start()

        self.logger("Started MQTTClient plugin")

    def _log(self, info):
        self._send('openmotics/logging', info)

    def _send(self, topic, data):
        try:
            self.client.publish(topic, json.dumps(data))
        except:
            self.client.connect(self._config['broker_ip'], self._config['broker_port'], 5)
            self.client.publish(topic, json.dumps(data))

    @input_status
    def input_status(self, status):
        self._log('input')
        if self._config['send_events'] is True:
            self._log(status)
            input_id = status[0]
            try:
                input_config = self.webinterface.get_input_configuration(None, input_id)
            except Exception, ex:
                self._log('Error: {0}'.format(ex))
                return
            self._log(input_config)
            data = {'id': input_id,
                    'name': input_config['config']['name'],
                    'timestamp': time.time()}
            self._send('openmotics/events/input', data)

    @output_status
    def output_status(self, status):
        if self._config['send_events'] is True:
            for entry in status:
                output_id = entry[0]
                try:
                    output_config = self.webinterface.get_output_configuration(None, output_id)
                except Exception, ex:
                    self._log('{0}: {1}'.format(type(ex), ex))
                    return
                self._log(output_config)
                data = {'id': output_id,
                        'name': output_config['config']['name'],
                        'timestamp': time.time()}
                self._send('openmotics/events/output', data)

    @om_expose
    def get_config_description(self):
        return json.dumps(MQTTClient.config_description)

    @om_expose
    def get_config(self):
        return json.dumps(self._config)

    @om_expose
    def set_config(self, config):
        config = json.loads(config)
        self._config_checker.check_config(config)
        self.write_config(config)
        self._config = config
        return json.dumps({'success': True})
