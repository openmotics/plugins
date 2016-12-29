"""
An MQTT client plugin for sending/receiving data to/from an MQTT broker.
For more info: https://github.com/openmotics/plugins/blob/master/mqtt-client/README.md
"""

import time
import simplejson as json
from threading import Thread
from subprocess import check_output
from plugins.base import om_expose, input_status, output_status, OMPluginBase, PluginConfigChecker
from serial_utils import CommunicationTimedOutException


class MQTTClient(OMPluginBase):
    """
    An MQTT client plugin for sending/receiving data to/from an MQTT broker.
    For more info: https://github.com/openmotics/plugins/blob/master/mqtt-client/README.md
    """

    name = 'MQTTClient'
    version = '1.0.27'
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

    default_config = {'broker_port': 1883}

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

        self.client = None
        self._outputs = {}
        self._inputs = {}

        self._read_config()
        self._try_connect()

        self._load_configuration()

        self.logger("Started MQTTClient plugin")

    def _read_config(self):
        self._ip = self._config.get('broker_ip')
        self._port = self._config.get('broker_port', MQTTClient.default_config['broker_port'])
        self._send_events = self._config.get('send_events', False)

        self._enabled = self._ip is not None and self._port is not None and self._send_events is True
        self.logger('MQTTClient is {0}'.format('enabled' if self._enabled else 'disabled'))

    def _load_configuration(self):
        # Inputs
        try:
            result = json.loads(self.webinterface.get_input_configurations(None))
            if result['success'] is False:
                self.logger('Failed to load input configurations')
            else:
                ids = []
                for config in result['config']:
                    input_id = config['id']
                    ids.append(input_id)
                    self._inputs[input_id] = config
                for input_id in self._inputs.keys():
                    if input_id not in ids:
                        del self._inputs[input_id]
        except CommunicationTimedOutException:
            self.logger('Error while loading input configurations: CommunicationTimedOutException')
        except Exception as ex:
            self.logger('Error while loading input configurations: {0}'.format(ex))
        # Outputs
        try:
            result = json.loads(self.webinterface.get_output_configurations(None))
            if result['success'] is False:
                self.logger('Failed to load output configurations')
            else:
                ids = []
                for config in result['config']:
                    if config['module_type'] not in ['o', 'O', 'd', 'D']:
                        continue
                    output_id = config['id']
                    ids.append(output_id)
                    self._outputs[output_id] = {'name': config['name'],
                                                'module_type': {'o': 'output',
                                                                'O': 'output',
                                                                'd': 'dimmer',
                                                                'D': 'dimmer'}[config['module_type']],
                                                'floor': config['floor'],
                                                'type': 'relay' if config['type'] == 0 else 'light'}
                for output_id in self._outputs.keys():
                    if output_id not in ids:
                        del self._outputs[output_id]
        except CommunicationTimedOutException:
            self.logger('Error while loading output configurations: CommunicationTimedOutException')
        except Exception as ex:
            self.logger('Error while loading output configurations: {0}'.format(ex))
        try:
            result = json.loads(self.webinterface.get_output_status(None))
            if result['success'] is False:
                self.logger('Failed to get output status')
            else:
                for output in result['status']:
                    output_id = output['id']
                    if output_id not in self._outputs:
                        continue
                    self._outputs[output_id]['status'] = output['status']
                    self._outputs[output_id]['dimmer'] = output['dimmer']
        except CommunicationTimedOutException:
            self.logger('Error getting output status: CommunicationTimedOutException')
        except Exception as ex:
            self.logger('Error getting output status: {0}'.format(ex))

    def _try_connect(self):
        if self._enabled is True:
            try:
                import paho.mqtt.client as client
                self.client = client.Client()
                self.client.connect(self._ip, self._port, 5)
                self.client.loop_start()
                self.logger('Connected to MQTT broker {0}:{1}'.format(self._ip, self._port))
            except Exception as ex:
                self.logger('Error connecting to MQTT broker: {0}'.format(ex))

    def _log(self, info):
        thread = Thread(target=self._send, args=('openmotics/logging', info))
        thread.start()

    def _send(self, topic, data):
        try:
            self.client.publish(topic, json.dumps(data))
        except:
            try:
                self.client.connect(self._ip, self._port, 5)
                self.client.publish(topic, json.dumps(data))
            except Exception as ex:
                self.logger('Error sending data to broker: {0}'.format(ex))

    @input_status
    def input_status(self, status):
        if self._enabled is True and self._send_events is True:
            input_id = status[0]
            try:
                if input_id in self._inputs:
                    name = self._inputs[input_id].get('name')
                    self._log('Input {0} ({1}) pressed'.format(input_id, name))
                    self.logger('Input {0} ({1}) pressed'.format(input_id, name))
                    data = {'id': input_id,
                            'name': name,
                            'timestamp': time.time()}
                    thread = Thread(target=self._send, args=('openmotics/events/input/{0}'.format(input_id), data))
                    thread.start()
                else:
                    self.logger('Got event for unknown input {0}'.format(input_id))
            except Exception as ex:
                self.logger('Error processing input {0}: {1}'.format(input_id, ex))

    @output_status
    def output_status(self, status):
        if self._enabled is True and self._send_events is True:
            try:
                on_outputs = {}
                for entry in status:
                    on_outputs[entry[0]] = entry[1]
                outputs = self._outputs
                for output_id in outputs:
                    status = outputs[output_id].get('status')
                    dimmer = outputs[output_id].get('dimmer')
                    name = outputs[output_id].get('name')
                    if status is None or dimmer is None:
                        continue
                    changed = False
                    if output_id in on_outputs:
                        if status != 1:
                            changed = True
                            outputs[output_id]['status'] = 1
                            self._log('Output {0} ({1}) changed to ON'.format(output_id, name))
                            self.logger('Output {0} changed to ON'.format(output_id))
                        if dimmer != on_outputs[output_id]:
                            changed = True
                            outputs[output_id]['dimmer'] = on_outputs[output_id]
                            self._log('Output {0} ({1}) changed to level {2}'.format(output_id, name, on_outputs[output_id]))
                            self.logger('Output {0} changed to level {1}'.format(output_id, on_outputs[output_id]))
                    elif status != 0:
                        changed = True
                        outputs[output_id]['status'] = 0
                        self._log('Output {0} ({1}) changed to OFF'.format(output_id, name))
                        self.logger('Output {0} changed to OFF'.format(output_id))
                    if changed is True:
                        if outputs[output_id]['module_type'] == 'output':
                            level = 100
                        else:
                            level = dimmer
                        if outputs[output_id]['status'] == 0:
                            level = 0
                        data = {'id': output_id,
                                'name': name,
                                'value': level,
                                'timestamp': time.time()}
                        thread = Thread(target=self._send, args=('openmotics/events/output/{0}'.format(output_id), data))
                        thread.start()
            except Exception as ex:
                self.logger('Error processing outputs: {0}'.format(ex))

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
        self._read_config()
        if self._enabled:
            thread = Thread(target=self._load_configuration)
            thread.start()
        self._try_connect()
        return json.dumps({'success': True})
