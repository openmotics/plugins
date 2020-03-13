"""
An MQTT client plugin for sending/receiving data to/from an MQTT broker.
For more info: https://github.com/openmotics/plugins/blob/master/mqtt-client/README.md
"""

import sys
import re
from datetime import datetime
import simplejson as json
from threading import Thread
from plugins.base import om_expose, input_status, output_status, OMPluginBase, PluginConfigChecker, receive_events
from serial_utils import CommunicationTimedOutException


class MQTTClient(OMPluginBase):
    """
    An MQTT client plugin for sending/receiving data to/from an MQTT broker.
    For more info: https://github.com/openmotics/plugins/blob/master/mqtt-client/README.md
    """

    name = 'MQTTClient'
    version = '1.4.0'
    interfaces = [('config', '1.0')]

    config_description = [{'name': 'broker_ip',
                           'type': 'str',
                           'description': 'IP or hostname of the MQTT broker.'},
                          {'name': 'broker_port',
                           'type': 'int',
                           'description': 'Port of the MQTT broker. Default: 1883'},
                          {'name': 'username',
                           'type': 'str',
                           'description': 'Username'},
                          {'name': 'password',
                           'type': 'str',
                           'description': 'Password'},
                           {'name': 'topic_prefix',
                            'type': 'str',
                            'description': 'Topic prefix'}]

    default_config = {'broker_port': 1883,
                      'topic_prefix': 'openmotics'}

    def __init__(self, webinterface, logger):
        super(MQTTClient, self).__init__(webinterface, logger)
        self.logger('Starting MQTTClient plugin...')

        self._config = self.read_config(MQTTClient.default_config)
        self._config_checker = PluginConfigChecker(MQTTClient.config_description)

        paho_mqtt_wheel = '/opt/openmotics/python/plugins/MQTTClient/paho_mqtt-1.5.0-py2-none-any.whl'
        if paho_mqtt_wheel not in sys.path:
            sys.path.insert(0, paho_mqtt_wheel)

        self.client = None
        self._inputs = {}
        self._outputs = {}

        self._read_config()
        self._try_connect()

        self._load_input_configuration()
        self._load_output_configuration()

        self.logger("Started MQTTClient plugin")

    def _read_config(self):
        self._ip = self._config.get('broker_ip')
        self._port = self._config.get('broker_port', MQTTClient.default_config['broker_port'])
        self._topic_prefix = self._config.get('topic_prefix', MQTTClient.default_config['topic_prefix'])
        self._username = self._config.get('username')
        self._password = self._config.get('password')

        self._enabled = self._ip is not None and self._port is not None
        self.logger('MQTTClient is {0}'.format('enabled' if self._enabled else 'disabled'))

    def _load_input_configuration(self):
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

    def _load_output_configuration(self):
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
                if self._username is not None:
                    self.logger("MQTTClient is using username/password")
                    self.client.username_pw_set(self._username, self._password)
                self.client.on_message = self.on_message
                self.client.on_connect = self.on_connect
                self.client.connect(self._ip, self._port, 5)
                self.client.loop_start()
            except Exception as ex:
                self.logger('Error connecting to MQTT broker: {0}'.format(ex))

    def _log(self, info):
        thread = Thread(target=self._send, args=('{0}/logging'.format(self._topic_prefix), info), kwargs={'retain': False})
        thread.start()

    def _send(self, topic, data, retain=True):
        try:
            self.client.publish(topic, json.dumps(data), retain=retain)
        except Exception as ex:
            self.logger('Error sending data to broker: {0}'.format(ex))

    @input_status(version=2)
    def input_status(self, data):
        if self._enabled is True:
            input_id = data.get('input_id')
            status = 'ON' if data.get('status') else 'OFF'
            try:
                if input_id in self._inputs:
                    name = self._inputs[input_id].get('name')
                    self._log('Input {0} ({1}) switched {2}'.format(input_id, name, status))
                    self.logger('Input {0} ({1}) switched {2}'.format(input_id, name,  status))
                    data = {'id': input_id,
                            'name': name,
                            'status': status,
                            'timestamp': datetime.now().isoformat()}
                    thread = Thread(target=self._send, args=('{0}/input/{1}/state'.format(self._topic_prefix, input_id), data))
                    thread.start()
                else:
                    self.logger('Got event for unknown input {0}'.format(input_id))
            except Exception as ex:
                self.logger('Error processing input {0}: {1}'.format(input_id, ex))

    @output_status
    def output_status(self, status):
        if self._enabled is True:
            try:
                new_output_status = {}
                for entry in status:
                    new_output_status[entry[0]] = entry[1]
                current_output_status = self._outputs
                for output_id in current_output_status:
                    status = current_output_status[output_id].get('status')
                    dimmer = current_output_status[output_id].get('dimmer')
                    name = current_output_status[output_id].get('name')
                    if status is None or dimmer is None:
                        continue
                    changed = False
                    if output_id in new_output_status:
                        if status != 1:
                            changed = True
                            current_output_status[output_id]['status'] = 1
                            self._log('Output {0} ({1}) changed to ON'.format(output_id, name))
                            self.logger('Output {0} ({1}) changed to ON'.format(output_id, name))
                        if dimmer != new_output_status[output_id]:
                            changed = True
                            current_output_status[output_id]['dimmer'] = new_output_status[output_id]
                            self._log('Output {0} ({1}) changed to level {2}'.format(output_id, name, new_output_status[output_id]))
                            self.logger('Output {0} ({1}) changed to level {2}'.format(output_id, name, new_output_status[output_id]))
                    elif status != 0:
                        changed = True
                        current_output_status[output_id]['status'] = 0
                        self._log('Output {0} ({1}) changed to OFF'.format(output_id, name))
                        self.logger('Output {0} ({1}) changed to OFF'.format(output_id, name))
                    if changed is True:
                        if current_output_status[output_id]['module_type'] == 'output':
                            level = 100
                        else:
                            level = dimmer
                        if current_output_status[output_id]['status'] == 0:
                            level = 0
                        data = {'id': output_id,
                                'name': name,
                                'value': level,
                                'timestamp': datetime.now().isoformat()}
                        thread = Thread(target=self._send, args=('{0}/output/{1}/state'.format(self._topic_prefix, output_id), data))
                        thread.start()
            except Exception as ex:
                self.logger('Error processing outputs: {0}'.format(ex))

    @receive_events
    def receive_events(self, id):
        if self._enabled is True:
            try:
                self._log('Got event {0}'.format(id))
                self.logger('Got event {0}'.format(id))
                data = {'id': id,
                        'timestamp': datetime.now().isoformat()}
                thread = Thread(target=self._send, args=('{0}/event/{1}/state'.format(id), data))
                thread.start()
            except Exception as ex:
                self.logger('Error processing event: {0}'.format(ex))

    def on_connect(self, client, userdata, flags, rc):
        if rc != 0:
            self.logger('Error connecting: rc={0}', rc)
            return

        self.logger('Connected to MQTT broker {0}:{1}'.format(self._ip, self._port))
        try:
            output_command_topic = '{0}/output/+/set'.format(self._topic_prefix)
            self.client.subscribe(output_command_topic)
            self.logger('Subscribed to {0}'.format(output_command_topic))
        except Exception as ex:
            self.logger('Could not subscribe: {0}'.format(ex))

    def on_message(self, client, userdata, msg):
        base_topic = '{0}/output/+/set'.format(self._topic_prefix)
        regexp = base_topic.replace('+', '(\d+)')
        if re.search(regexp, msg.topic) is not None:
            try:
                # the output_id is the first math of the regular expression
                output_id = int(re.findall(regexp, msg.topic)[0])
                if output_id in self._outputs:
                    output = self._outputs[output_id]
                    value = int(msg.payload)
                    if value > 0:
                        is_on = 'true'
                        log_value = 'ON'
                    else:
                        is_on = 'false'
                        log_value = 'OFF'
                    dimmer = None
                    if output['module_type'] == 'dimmer':
                        dimmer = None if value == 0 else max(0, min(100, value))
                        if value > 0:
                            log_value = 'ON ({0}%)'.format(value)
                    result = json.loads(self.webinterface.set_output(None, output_id, is_on, dimmer, None))
                    if result['success'] is False:
                        log_message = 'Failed to set output {0} to {1}: {2}'.format(output_id, log_value, result.get('msg', 'Unknown error'))
                        self._log(log_message)
                        self.logger(log_message)
                    else:
                        log_message = 'Output {0} set to {1}'.format(output_id, log_value)
                        self._log(log_message)
                        self.logger(log_message)
                else:
                    self._log('Unknown output: {0}'.format(output_id))
            except Exception as ex:
                self._log('Failed to process message: {0}'.format(ex))
        else:
            self._log('Message with topic {0} ignored'.format(msg.topic))
            self.logger('Message with topic {0} ignored'.format(msg.topic))

    @om_expose
    def get_config_description(self):
        return json.dumps(MQTTClient.config_description)

    @om_expose
    def get_config(self):
        return json.dumps(self._config)

    @om_expose
    def set_config(self, config):
        config = json.loads(config)
        # Convert unicode to str
        config['broker_ip'] = config['broker_ip'].encode('ascii', 'ignore')
        config['username'] = config['username'].encode('ascii', 'ignore')
        config['password'] = config['password'].encode('ascii', 'ignore')
        config['topic_prefix'] = config['topic_prefix'].encode('ascii', 'ignore')
        self._config_checker.check_config(config)
        self.write_config(config)
        self._config = config
        self._read_config()
        if self._enabled:
            thread = Thread(target=self._load_configuration)
            thread.start()
        self._try_connect()
        return json.dumps({'success': True})
