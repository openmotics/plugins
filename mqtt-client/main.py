"""
An MQTT client plugin for sending/receiving data to/from an MQTT broker.
For more info: https://github.com/openmotics/plugins/blob/master/mqtt-client/README.md
"""

import sys
import re
import time
from datetime import datetime
import pytz
import simplejson as json
from threading import Thread
from plugins.base import om_expose, input_status, output_status, OMPluginBase, PluginConfigChecker, receive_events, om_metric_receive
from serial_utils import CommunicationTimedOutException


class MQTTClient(OMPluginBase):
    """
    An MQTT client plugin for sending/receiving data to/from an MQTT broker.
    For more info: https://github.com/openmotics/plugins/blob/master/mqtt-client/README.md
    """

    name = 'MQTTClient'
    version = '2.0.0'
    interfaces = [('config', '1.0')]

    config_description = [
        {'name': 'hostname',
         'type': 'str',
         'description': 'MQTT broker hostname or IP address.'},
        {'name': 'port',
         'type': 'int',
         'description': 'MQTT broker port. Default: 1883'},
        {'name': 'username',
         'type': 'str',
         'description': 'MQTT broker username. Default: openmotics'},
        {'name': 'password',
         'type': 'password',
         'description': 'MQTT broker password'},
        # input status
        {'name': 'input_status_enabled',
         'type': 'bool',
         'description': 'Enable input status publishing of messages.'},
        {'name': 'input_status_topic_format',
         'type': 'str',
         'description': 'Input status topic format. Default: openmotics/input/{id}/status'},
        {'name': 'input_status_qos',
         'type': 'enum',
         'choices': ['0', '1', '2'],
         'description': 'Input status message quality of service. Default: 0'},
        {'name': 'input_status_retain',
         'type': 'bool',
         'description': 'Input status message retain. Default: False'},
        # output status
        {'name': 'output_status_enabled',
         'type': 'bool',
         'description': 'Enable output status publishing of messages.'},
        {'name': 'output_status_topic_format',
         'type': 'str',
         'description': 'Output status topic format. Default: openmotics/output/{id}/status'},
        {'name': 'output_status_qos',
         'type': 'enum',
         'choices': ['0', '1', '2'],
         'description': 'Output status message quality of service. Default: 0'},
        {'name': 'output_status_retain',
         'type': 'bool',
         'description': 'Output status message retain. Default: False'},
        # event status
        {'name': 'event_status_enabled',
         'type': 'bool',
         'description': 'Enable event status publishing of messages.'},
        {'name': 'event_status_topic_format',
         'type': 'str',
         'description': 'Event status topic format. Default: openmotics/event/{id}/status'},
        {'name': 'event_status_qos',
         'type': 'enum',
         'choices': ['0', '1', '2'],
         'description': 'Event status message quality of service. Default: 0'},
        {'name': 'event_status_retain',
         'type': 'bool',
         'description': 'Event status message retain. Default: False'},
        # sensor status
        {'name': 'sensor_status_enabled',
         'type': 'bool',
         'description': 'Enable sensor status publishing of messages.'},
        {'name': 'sensor_status_topic_format',
         'type': 'str',
         'description': 'Sensor status topic format. Default: openmotics/sensor/{id}/status'},
        {'name': 'sensor_status_qos',
         'type': 'enum',
         'choices': ['0', '1', '2'],
         'description': 'Sensor status message quality of service. Default: 0'},
        {'name': 'sensor_status_retain',
         'type': 'bool',
         'description': 'Sensor status message retain. Default: False'},
        # this doesn't seem to work, removing config parameter for now
        # {'name': 'sensor_metric_poll_frequency',
        #  'type': 'int',
        #  'description': 'Polling frequency for sensor metrics in seconds. Default: 300'},
        # energy status
        {'name': 'energy_status_enabled',
         'type': 'bool',
         'description': 'Enable energy status publishing of messages.'},
        {'name': 'energy_status_topic_format',
         'type': 'str',
         'description': 'Energy status topic format. Default: openmotics/energy/{id}/status'},
        {'name': 'energy_status_qos',
         'type': 'enum',
         'choices': ['0', '1', '2'],
         'description': 'Energy status quality of Service. Default: 0'},
        {'name': 'energy_status_retain',
         'type': 'bool',
         'description': 'Energy status retain. Default: False'},
        # this doesn't seem to work, removing config parameter for now
        # {'name': 'energy_metric_poll_frequency',
        # 'type': 'int',
        # 'description': 'Polling frequency for energy metrics in seconds. Default: 60'},
        # output command
        {'name': 'output_command_topic',
         'type': 'str',
         'description': 'Topic to subscribe to for output command messages. Leave empty to turn off.'},
        # logging
        {'name': 'logging_topic',
         'type': 'str',
         'description': 'Topic for logging messages. Leave empty to turn off.'},
        # timestamp timezone
        {'name': 'timezone',
         'type': 'str',
         'description': 'Timezone. Default: UTC. Example: Europe/Brussels'}
    ]

    default_config = {
        'port': 1883,
        'username': 'openmotics',
        'input_status_topic_format': 'openmotics/input/{id}/state',
        'input_status_qos': 0,
        'output_status_topic_format': 'openmotics/output/{id}/state',
        'output_status_qos': 0,
        'event_status_topic_format': 'openmotics/event/{id}/state',
        'event_status_qos': 0,
        'sensor_status_topic_format': 'openmotics/sensor/{id}/state',
        'sensor_status_qos': 0,
        # this doesn't seem to work, removing config parameter for now
        # 'sensor_metric_poll_frequency': 300,
        'energy_status_topic_format': 'openmotics/energy/{id}/state',
        'energy_status_qos': 0,
        # this doesn't seem to work, removing config parameter for now
        #'energy_metric_poll_frequency': 60,
        'output_command_topic': 'openmotics/output/+/set',
        'logging_topic': 'openmotics/logging',
        'timezone': 'UTC'
    }

    def __init__(self, webinterface, logger):
        super(MQTTClient, self).__init__(webinterface, logger)
        self.logger('Starting MQTTClient plugin...')

        self._config = self.read_config(MQTTClient.default_config)
        #self.logger("Default configuration '{0}'".format(self._config))
        self._config_checker = PluginConfigChecker(MQTTClient.config_description)

        paho_mqtt_wheel = '/opt/openmotics/python/plugins/MQTTClient/paho_mqtt-1.5.0-py2-none-any.whl'
        if paho_mqtt_wheel not in sys.path:
            sys.path.insert(0, paho_mqtt_wheel)

        self.client = None
        self._inputs = {}
        self._outputs = {}

        self._read_config()
        self._try_connect()

        self._load_configuration()

        self.logger("Started MQTTClient plugin")

    def _read_config(self):
        # broker
        self._hostname = self._config.get('hostname')
        self._port     = self._config.get('port')
        self._username = self._config.get('username')
        self._password = self._config.get('password')
        # inputs
        self._input_enabled = self._config.get('input_status_enabled')
        self._input_topic   = self._config.get('input_status_topic_format')
        self._input_qos     = int(self._config.get('input_status_qos'))
        self._input_retain  = self._config.get('input_status_retain')
        # outputs
        self._output_enabled = self._config.get('output_status_enabled')
        self._output_topic   = self._config.get('output_status_topic_format')
        self._output_qos     = int(self._config.get('output_status_qos'))
        self._output_retain  = self._config.get('output_status_retain')
        # events
        self._event_enabled = self._config.get('event_status_enabled')
        self._event_topic   = self._config.get('event_status_topic_format')
        self._event_qos     = int(self._config.get('event_status_qos'))
        self._event_retain  = self._config.get('event_status_retain')
        # sensors
        self._sensor_enabled = self._config.get('sensor_status_enabled')
        self._sensor_topic   = self._config.get('sensor_status_topic_format')
        self._sensor_qos     = int(self._config.get('sensor_status_qos'))
        self._sensor_retain  = self._config.get('sensor_status_retain')
        # this doesn't seem to work, removing config parameter for now
        #self.receive_sensor_metric_data.om_metric_receive['interval'] = int(self._config.get('sensor_metric_poll_frequency'))
        # energy
        self._energy_enabled = self._config.get('energy_status_enabled')
        self._energy_topic   = self._config.get('energy_status_topic_format')
        self._energy_qos     = int(self._config.get('energy_status_qos'))
        self._energy_retain  = self._config.get('energy_status_retain')
        # this doesn't seem to work, removing config parameter for now
        #self.receive_energy_metric_data.om_metric_receive['interval'] =  int(self._config.get('energy_metric_poll_frequency'))
        # output command
        self._output_command_topic = self._config.get('output_command_topic')
        # logging topic
        self._logging_topic = self._config.get('logging_topic')
        # timezone
        self._timezone = self._config.get('timezone')

        self._enabled = self._hostname is not None and self._port is not None
        self.logger('MQTTClient is {0}'.format('enabled' if self._enabled else 'disabled'))

    def _load_configuration(self):
        if self._input_enabled:
            self._load_input_configuration()
        if self._output_enabled:
            self._load_output_configuration()

    def _load_input_configuration(self):
        try:
            result = json.loads(self.webinterface.get_input_configurations())
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
                self.logger('Configuring {0} inputs'.format(len(ids)))
        except CommunicationTimedOutException:
            self.logger('Error while loading input configurations: CommunicationTimedOutException')
        except Exception as ex:
            self.logger('Error while loading input configurations: {0}'.format(ex))
        try:
            result = json.loads(self.webinterface.get_input_status())
            if result['success'] is False:
                self.logger('Failed to get input status')
            else:
                for input_data in result['status']:
                    input_id = input_data['id']
                    if input_id not in self._inputs:
                        continue
                    self._inputs[input_id]['status'] = input_data['status']
        except CommunicationTimedOutException:
            self.logger('Error getting input status: CommunicationTimedOutException')
        except Exception as ex:
            self.logger('Error getting input status: {0}'.format(ex))

    def _load_output_configuration(self):
        try:
            result = json.loads(self.webinterface.get_output_configurations())
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
                self.logger('Configuring {0} outputs'.format(len(ids)))
        except CommunicationTimedOutException:
            self.logger('Error while loading output configurations: CommunicationTimedOutException')
        except Exception as ex:
            self.logger('Error while loading output configurations: {0}'.format(ex))
        try:
            result = json.loads(self.webinterface.get_output_status())
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
                    self.logger("MQTTClient is using username '{0}' and password".format(self._username))
                    self.client.username_pw_set(self._username, self._password)
                self.client.on_message = self.on_message
                self.client.on_connect = self.on_connect
                self.client.connect(self._hostname, self._port, 5)
                self.client.loop_start()
            except Exception as ex:
                self.logger('Error connecting to MQTT broker: {0}'.format(ex))

    def _log(self, info):
        # for log messages QoS = 0 and retain = False
        thread = Thread(target=self._send, args=(self._logging_topic, info, 0, False))
        thread.start()

    def _send(self, topic, data, qos, retain):
        try:
            self.client.publish(topic, payload=json.dumps(data), qos=qos, retain=retain)
        except Exception as ex:
            self.logger('Error sending data to broker: {0}'.format(ex))

    def _timestamp2isoformat(self, timestamp=None):
        # start with UTC
        dt = datetime.utcnow()
        if (timestamp is not None):
            dt.utcfromtimestamp(float(timestamp))
        # localize the UTC date/time, make it "aware" instead of naive
        dt = pytz.timezone('UTC').localize(dt)
        # convert to timezone from configuration
        if self._timezone is not None and self._timezone is not 'UTC':
            dt = dt.astimezone(pytz.timezone(self._timezone))
        return dt.isoformat()

    @input_status(version=2)
    def input_status(self, data):
        if self._enabled and self._input_enabled:
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
                            'timestamp': self._timestamp2isoformat()}
                    thread = Thread(
                        target=self._send,
                        args=(self._input_topic.format(id=input_id), data, self._input_qos, self._input_retain)
                    )
                    thread.start()
                else:
                    self.logger('Got event for unknown input {0}'.format(input_id))
            except Exception as ex:
                self.logger('Error processing input {0}: {1}'.format(input_id, ex))

    @output_status
    def output_status(self, status):
        if self._enabled and self._output_enabled:
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
                                'timestamp': self._timestamp2isoformat()}
                        thread = Thread(
                            target=self._send,
                            args=(self._output_topic.format(id=output_id), data, self._output_qos, self._output_retain)
                        )
                        thread.start()
            except Exception as ex:
                self.logger('Error processing outputs: {0}'.format(ex))

    @receive_events
    def receive_events(self, event_id):
        if self._enabled and self._event_enabled:
            try:
                self._log('Got event {0}'.format(event_id))
                self.logger('Got event {0}'.format(event_id))
                data = {'id': event_id,
                        'timestamp': self._timestamp2isoformat()}
                thread = Thread(
                    target=self._send,
                    args=(self._event_topic.format(id=event_id), data, self._event_qos, self._event_retain)
                )
                thread.start()
            except Exception as ex:
                self.logger('Error processing event: {0}'.format(ex))

    @om_metric_receive(metric_type='sensor', interval=300)
    def receive_sensor_metric_data(self, metric):
        #self.logger('Receiving sensor metrics with interval: {0}'.format(self.receive_sensor_metric_data.om_metric_receive.get('interval')))
        try:
            if self._enabled and self._sensor_enabled:
                sensor_data = metric.get('tags')
                sensor_values = metric.get('values')
                for key, sensor_value in sensor_values.items():
                    if key == 'hum':
                        sensor_data['humidity'] = sensor_value
                    elif key == 'temp':
                        sensor_data['temperature'] = sensor_value
                    elif key == 'bright':
                        sensor_data['brightness'] = sensor_value
                    else:
                        sensor_data[key] = sensor_value

                sensor_data['timestamp'] = self._timestamp2isoformat(metric.get('timestamp'))
                thread = Thread(
                    target=self._send,
                    args=(self._sensor_topic.format(id=sensor_data.get('id')), sensor_data, self._sensor_qos, self._sensor_retain)
                )
                thread.start()
        except Exception as ex:
            self.logger('Error receiving sensor metrics: {0}'.format(ex))

    @om_metric_receive(metric_type='energy', interval=60)
    def receive_energy_metric_data(self, metric):
        #self.logger('Receiving energy metrics with interval: {0}'.format(self.receive_energy_metric_data.om_metric_receive.get('interval')))
        try:
            if self._enabled and self._energy_enabled:
                energy_data = metric.get('tags')
                energy_values = metric.get('values')

                energy_id = energy_data.get('id')
                if energy_id is not None:
                    regexp = 'E\w+\.(\d+)'
                    if re.search(regexp, energy_id) is not None:
                        energy_data['id'] = re.findall(regexp, energy_id)[0]

                        for key, energy_value in energy_values.items():
                            energy_data[key] = energy_value

                        energy_data['timestamp'] = self._timestamp2isoformat()
                        thread = Thread(
                            target=self._send,
                            args=(self._energy_topic.format(id=energy_data.get('id')), energy_data, self._energy_qos, self._energy_retain)
                        )
                        thread.start()
        except Exception as ex:
            self.logger('Error receiving energy metrics: {0}'.format(ex))

    def on_connect(self, client, userdata, flags, rc):
        if rc != 0:
            self.logger('Error connecting: rc={0}', rc)
            return

        self.logger('Connected to MQTT broker {0}:{1}'.format(self._hostname, self._port))
        # subscribe to output command topic if provided
        if self._output_command_topic:
            try:
                self.client.subscribe(self._output_command_topic)
                self.logger('Subscribed to {0}'.format(self._output_command_topic))
            except Exception as ex:
                self.logger('Could not subscribe: {0}'.format(ex))

    def on_message(self, client, userdata, msg):
        if self._output_command_topic:
            regexp = self._output_command_topic.replace('+', '(\d+)')
            if re.search(regexp, msg.topic) is not None:
                try:
                    # the output_id is the first match of the regular expression
                    output_id = int(re.findall(regexp, msg.topic)[0])
                    if output_id in self._outputs:
                        output = self._outputs[output_id]
                        value = int(msg.payload)
                        if value > 0:
                            is_on = 'true'
                        else:
                            is_on = 'false'
                        dimmer = None
                        if output['module_type'] == 'dimmer':
                            dimmer = None if value == 0 else max(0, min(100, value))
                            if value > 0:
                                log_value = 'ON ({0}%)'.format(value)
                        result = json.loads(self.webinterface.set_output(id=output_id, is_on=is_on, dimmer=dimmer))
                        if result['success'] is False:
                            log_message = 'Failed to set output {0} to {1}: {2}'.format(output_id, value, result.get('msg', 'Unknown error'))
                            self._log(log_message)
                            self.logger(log_message)
                        else:
                            log_message = 'Message for output {0} with payload {1}'.format(output_id, value)
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
        try:
            config = json.loads(config)
            for key in config:
                if isinstance(config[key], basestring):
                    config[key] = str(config[key])
                self._config_checker.check_config(config)
            self.write_config(config)
            self._config = config
            self._read_config()
            if self._enabled:
                thread = Thread(target=self._load_configuration)
                thread.start()
        except Exception as ex:
            self.logger('Error saving configuration: {0}'.format(ex))

        self._try_connect()
        return json.dumps({'success': True})
