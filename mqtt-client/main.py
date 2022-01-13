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
from plugins.base import om_expose, input_status, output_status, OMPluginBase, PluginConfigChecker, receive_events, om_metric_receive, background_task
from serial_utils import CommunicationTimedOutException


class MQTTClient(OMPluginBase):
    """
    An MQTT client plugin for sending/receiving data to/from an MQTT broker.
    For more info: https://github.com/openmotics/plugins/blob/master/mqtt-client/README.md
    """

    name = 'MQTTClient'
    version = '2.0.2'
    interfaces = [('config', '1.0')]

    energy_module_config = {
        1: 8,
        8: 8,
        12: 12
    }

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
         'description': 'Input status topic format. Default: openmotics/input/{id}/state'},
        {'name': 'input_status_qos',
         'type': 'enum',
         'choices': ['0', '1', '2'],
         'description': 'Input status message quality of service. Default: 0'},
        {'name': 'input_status_retain',
         'type': 'bool',
         'description': 'Input status message retain.'},
        # output status
        {'name': 'output_status_enabled',
         'type': 'bool',
         'description': 'Enable output status publishing of messages.'},
        {'name': 'output_status_topic_format',
         'type': 'str',
         'description': 'Output status topic format. Default: openmotics/output/{id}/state'},
        {'name': 'output_status_qos',
         'type': 'enum',
         'choices': ['0', '1', '2'],
         'description': 'Output status message quality of service. Default: 0'},
        {'name': 'output_status_retain',
         'type': 'bool',
         'description': 'Output status message retain.'},
        # event status
        {'name': 'event_status_enabled',
         'type': 'bool',
         'description': 'Enable event status publishing of messages.'},
        {'name': 'event_status_topic_format',
         'type': 'str',
         'description': 'Event status topic format. Default: openmotics/event/{id}/state'},
        {'name': 'event_status_qos',
         'type': 'enum',
         'choices': ['0', '1', '2'],
         'description': 'Event status message quality of service. Default: 0'},
        {'name': 'event_status_retain',
         'type': 'bool',
         'description': 'Event status message retain.'},
        # temperature status
        {'name': 'temperature_status_enabled',
         'type': 'bool',
         'description': 'Enable temperature status publishing of messages.'},
        {'name': 'temperature_status_topic_format',
         'type': 'str',
         'description': 'Temperature status topic format. Default: openmotics/temperature/{id}/state'},
        {'name': 'temperature_status_qos',
         'type': 'enum',
         'choices': ['0', '1', '2'],
         'description': 'Temperature status message quality of service. Default: 0'},
        {'name': 'temperature_status_retain',
         'type': 'bool',
         'description': 'Temperature status message retain.'},
        {'name': 'temperature_status_poll_frequency',
         'type': 'int',
         'description': 'Polling frequency for temperature status in seconds. Default: 300, minimum: 10'},
        # humidity status
        {'name': 'humidity_status_enabled',
         'type': 'bool',
         'description': 'Enable humidity status publishing of messages.'},
        {'name': 'humidity_status_topic_format',
         'type': 'str',
         'description': 'Humidity status topic format. Default: openmotics/humidity/{id}/state'},
        {'name': 'humidity_status_qos',
         'type': 'enum',
         'choices': ['0', '1', '2'],
         'description': 'Humidity status message quality of service. Default: 0'},
        {'name': 'humidity_status_retain',
         'type': 'bool',
         'description': 'Humidity status message retain.'},
        {'name': 'humidity_status_poll_frequency',
         'type': 'int',
         'description': 'Polling frequency for humidity status in seconds. Default: 300, minimum: 10'},
        # brightness status
        {'name': 'brightness_status_enabled',
         'type': 'bool',
         'description': 'Enable brightness status publishing of messages.'},
        {'name': 'brightness_status_topic_format',
         'type': 'str',
         'description': 'Brightness status topic format. Default: openmotics/brightness/{id}/state'},
        {'name': 'brightness_status_qos',
         'type': 'enum',
         'choices': ['0', '1', '2'],
         'description': 'Brightness status message quality of service. Default: 0'},
        {'name': 'brightness_status_retain',
         'type': 'bool',
         'description': 'Brightness status message retain. Default: False'},
        {'name': 'brightness_status_poll_frequency',
         'type': 'int',
         'description': 'Polling frequency for brightness status in seconds. Default: 300, minimum: 10'},
        # power status
        {'name': 'power_status_enabled',
         'type': 'bool',
         'description': 'Enable power status publishing of messages.'},
        {'name': 'power_status_topic_format',
         'type': 'str',
         'description': 'Power status topic format. Default: openmotics/power/{module_id}/{sensor_id}/state'},
        {'name': 'power_status_qos',
         'type': 'enum',
         'choices': ['0', '1', '2'],
         'description': 'Power status quality of Service. Default: 0'},
        {'name': 'power_status_retain',
         'type': 'bool',
         'description': 'Power status retain.'},
        {'name': 'power_status_poll_frequency',
        'type': 'int',
        'description': 'Polling frequency for power status in seconds. Default: 60, minimum: 10'},
        # energy status
        {'name': 'energy_status_enabled',
         'type': 'bool',
         'description': 'Enable energy status publishing of messages.'},
        {'name': 'energy_status_topic_format',
         'type': 'str',
         'description': 'Energy status topic format. Default: openmotics/energy/{module_id}/{sensor_id}/state'},
        {'name': 'energy_status_qos',
         'type': 'enum',
         'choices': ['0', '1', '2'],
         'description': 'Energy status quality of Service. Default: 0'},
        {'name': 'energy_status_retain',
         'type': 'bool',
         'description': 'Energy status retain.'},
        {'name': 'energy_status_poll_frequency',
        'type': 'int',
        'description': 'Polling frequency for energy status in seconds. Default: 3600 (1 hour), minimum: 10'},
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
        'temperature_status_topic_format': 'openmotics/temperature/{id}/state',
        'temperature_status_qos': 0,
        'temperature_status_poll_frequency': 300,
        'humidity_status_topic_format': 'openmotics/humidity/{id}/state',
        'humidity_status_qos': 0,
        'humidity_status_poll_frequency': 300,
        'brightness_status_topic_format': 'openmotics/brightness/{id}/state',
        'brightness_status_qos': 0,
        'brightness_status_poll_frequency': 300,
        'power_status_topic_format': 'openmotics/power/{module_id}/{sensor_id}/state',
        'power_status_qos': 0,
        'power_status_poll_frequency': 60,
        'energy_status_topic_format': 'openmotics/energy/{module_id}/{sensor_id}/state',
        'energy_status_qos': 0,
        'energy_status_poll_frequency': 3600,
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
        self._sensor_config = {}
        self._inputs = {}
        self._outputs = {}
        self._sensors = {}
        self._power_modules = {}

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
        self._sensor_config = {
            'temperature': {
                'enabled':        self._config.get('temperature_status_enabled'),
                'topic':          self._config.get('temperature_status_topic_format'),
                'qos':            int(self._config.get('temperature_status_qos')),
                'retain':         self._config.get('temperature_status_retain'),
                'poll_frequency': int(self._config.get('temperature_status_poll_frequency'))
            },
            'humidity': {
                'enabled':        self._config.get('humidity_status_enabled'),
                'topic':          self._config.get('humidity_status_topic_format'),
                'qos':            int(self._config.get('humidity_status_qos')),
                'retain':         self._config.get('humidity_status_retain'),
                'poll_frequency': int(self._config.get('humidity_status_poll_frequency'))
            },
            'brightness': {
                'enabled':        self._config.get('brightness_status_enabled'),
                'topic':          self._config.get('brightness_status_topic_format'),
                'qos':            int(self._config.get('brightness_status_qos')),
                'retain':         self._config.get('brightness_status_retain'),
                'poll_frequency': int(self._config.get('brightness_status_poll_frequency'))
            },
            'power': {
                'enabled':        self._config.get('power_status_enabled'),
                'topic':          self._config.get('power_status_topic_format'),
                'qos':            int(self._config.get('power_status_qos')),
                'retain':         self._config.get('power_status_retain'),
                'poll_frequency': int(self._config.get('power_status_poll_frequency'))
            },
            'energy': {
                'enabled':        self._config.get('energy_status_enabled'),
                'topic':          self._config.get('energy_status_topic_format'),
                'qos':            int(self._config.get('energy_status_qos')),
                'retain':         self._config.get('energy_status_retain'),
                'poll_frequency': int(self._config.get('energy_status_poll_frequency'))
            }
        }
        self._sensor_enabled = (self._sensor_config.get('temperature').get('enabled') or self._sensor_config.get('humidity').get('enabled') or self._sensor_config.get('brightness').get('enabled'))
        self._power_enabled = (self._sensor_config.get('power').get('enabled') or self._sensor_config.get('energy').get('enabled'))
        # output command
        self._output_command_topic = self._config.get('output_command_topic')
        # logging topic
        self._logging_topic = self._config.get('logging_topic')
        # timezone
        self._timezone = self._config.get('timezone')
        self._enabled = self._hostname is not None and self._port is not None
        self.logger('MQTTClient is {0}'.format('enabled' if self._enabled else 'disabled'))

    def _load_configuration(self):
        inputs_loaded  = False
        outputs_loaded = False
        sensors_loaded = False
        power_loaded   = False
        should_load = True

        while should_load:
            if not inputs_loaded:
                inputs_loaded = self._load_input_configuration()
            if not outputs_loaded:
                outputs_loaded = self._load_output_configuration()
            if not sensors_loaded:
                sensors_loaded = self._load_sensor_configuration()
            if not power_loaded:
                power_loaded = self._load_power_configuration()
            should_load = not all([inputs_loaded, outputs_loaded, sensors_loaded, power_loaded])
            if should_load:
                time.sleep(15)

    def _load_input_configuration(self):
        input_config_loaded = True
        if self._input_enabled:
            try:
                result = json.loads(self.webinterface.get_input_configurations())
                if result['success'] is False:
                    self.logger('Failed to load input configurations')
                    input_config_loaded = False
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
            except Exception as ex:
                self.logger('Error while loading input configurations: {0}'.format(ex))
                input_config_loaded = False
            try:
                result = json.loads(self.webinterface.get_input_status())
                if result['success'] is False:
                    self.logger('Failed to get input status')
                    input_config_loaded = False
                else:
                    for input_data in result['status']:
                        input_id = input_data['id']
                        if input_id not in self._inputs:
                            continue
                        self._inputs[input_id]['status'] = input_data['status']
            except Exception as ex:
                self.logger('Error getting input status: {0}'.format(ex))
                input_config_loaded = False
        return input_config_loaded

    def _load_output_configuration(self):
        output_config_loaded = True
        if self._output_enabled:
            try:
                result = json.loads(self.webinterface.get_output_configurations())
                if result['success'] is False:
                    output_config_loaded = False
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
                                                    'type': 'relay' if config['type'] == 0 else 'light'}
                    for output_id in self._outputs.keys():
                        if output_id not in ids:
                            del self._outputs[output_id]
                    self.logger('Configuring {0} outputs'.format(len(ids)))
            except Exception as ex:
                output_config_loaded = False
                self.logger('Error while loading output configurations: {0}'.format(ex))
            try:
                result = json.loads(self.webinterface.get_output_status())
                if result['success'] is False:
                    output_config_loaded = False
                    self.logger('Failed to get output status')
                else:
                    for output in result['status']:
                        output_id = output['id']
                        if output_id not in self._outputs:
                            continue
                        self._outputs[output_id]['status'] = output['status']
                        self._outputs[output_id]['dimmer'] = output['dimmer']
            except Exception as ex:
                output_config_loaded = False
                self.logger('Error getting output status: {0}'.format(ex))
        return output_config_loaded

    def _load_sensor_configuration(self):
        sensor_config_loaded = True
        if self._sensor_enabled:
            try:
                result = json.loads(self.webinterface.get_sensor_configurations())
                if result['success'] is False:
                    sensor_config_loaded = False
                    self.logger('Failed to load sensor configurations: {0}'.format(result.get('msg')))
                else:
                    ids = []
                    for config in result['config']:
                        sensor_id = int(config['external_id'])
                        ids.append(sensor_id)
                        self._sensors[sensor_id] = {'name': config['name'], 'offset': float(config['offset'])}
                    for sensor_id in self._sensors.keys():
                        if sensor_id not in ids:
                            del self._sensors[sensor_id]
                    self.logger('Configuring {0} sensors'.format(len(ids)))
            except Exception as ex:
                sensor_config_loaded = False
                self.logger('Error while loading sensor configurations: {0}'.format(ex))
        return sensor_config_loaded

    def _load_power_configuration(self):
        power_config_loaded = True
        if self._power_enabled:
            try:
                result = json.loads(self.webinterface.get_power_modules())
                if result['success'] is False:
                    power_config_loaded = False
                    self.logger('Failed to load power configurations: {0}'.format(result.get('msg')))
                else:
                    ids = []
                    for module in result['modules']:
                        module_id = int(module['id'])
                        ids.append(module_id)
                        version = int(module['version'])
                        input_count = MQTTClient.energy_module_config.get(version, 0)
                        module_config = {}
                        if input_count == 0:
                            self.logger('Warning: Skipping energy module {0}, version {1} is currently not supported by this plugin. Only versions: {2}'.format(
                                module_id,
                                version,
                                ', '.join(MQTTClient.energy_module_config.keys())))
                            continue
                        else:
    	                    self.logger('Configuring energy module {0} (version {1}) with {2} inputs'.format(module_id, version, input_count))
                        for input_id in range(0, input_count):
                            module_config[input_id] = {'name':     module['input{0}'.format(input_id)],
                                                       'sensor':   module['sensor{0}'.format(input_id)],
                                                       'times':    module['times{0}'.format(input_id)],
                                                       'inverted': module['inverted{0}'.format(input_id)]}
                        self._power_modules[module_id] = module_config
                    for module_id in self._power_modules.keys():
                        if module_id not in ids:
                            del self._power_modules[module_id]
            except Exception as ex:
                power_config_loaded = False
                self.logger('Error while loading power configurations: {0}'.format(ex))
        return power_config_loaded

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

    @background_task
    def background_task_temperature_status(self):
        self._create_background_task(
            'temperature',
            self.webinterface.get_sensor_temperature_status,
            self._process_sensor_status
        )()

    @background_task
    def background_task_humidity_status(self):
        self._create_background_task(
            'humidity',
            self.webinterface.get_sensor_humidity_status,
            self._process_sensor_status
        )()

    @background_task
    def background_task_brightness_status(self):
        self._create_background_task(
            'brightness',
            self.webinterface.get_sensor_brightness_status,
            self._process_sensor_status
        )()

    @background_task
    def background_task_realtime_power(self):
        self._create_background_task(
            'power',
            self.webinterface.get_realtime_power,
            self._process_realtime_power
        )()

    @background_task
    def background_task_total_energy(self):
        self._create_background_task(
            'energy',
            self.webinterface.get_total_energy,
            self._process_total_energy
        )()

    def _process_sensor_status(self, sensor_config, json_data):
        mqtt_messages = []
        data_list = list(filter(None, json_data.get('status', [])))
        for sensor_id, sensor_value in enumerate(data_list):
            sensor = self._sensors.get(sensor_id)
            if sensor:
                sensor_data = {'id': sensor_id,
                               'name': sensor.get('name'),
                               'value': float(sensor_value) + float(sensor.get('offset')),
                               'timestamp': self._timestamp2isoformat()}
                mqtt_messages.append({'topic': sensor_config.get('topic').format(id=sensor_id),
                                      'message': sensor_data})
        return mqtt_messages

    def _process_realtime_power(self, sensor_config, json_data):
        mqtt_messages = []
        json_data.pop('success')
        for module_id, values in json_data.items():
            module = self._power_modules.get(int(module_id))
            if module:
                for input_id, sensor_values in enumerate(values):
                    power_input = module.get(int(input_id))
                    if power_input:
                        sensor_data = {'sensor_id': input_id,
                                       'module_id': module_id,
                                       'name': power_input.get('name'),
                                       'voltage': sensor_values[0],
                                       'frequency': sensor_values[1],
                                       'current': sensor_values[2],
                                       'power': sensor_values[3],
                                       'timestamp': self._timestamp2isoformat()}
                        mqtt_messages.append({'topic': sensor_config.get('topic').format(module_id=module_id, sensor_id=input_id),
                                              'message': sensor_data })
        return mqtt_messages

    def _process_total_energy(self, sensor_config, json_data):
        mqtt_messages = []
        json_data.pop('success')
        for module_id, values in json_data.items():
            module = self._power_modules.get(int(module_id))
            if module:
                for input_id, sensor_values in enumerate(values):
                    power_input = module.get(int(input_id))
                    if power_input:
                        sensor_data = {'sensor_id': input_id,
                                       'module_id': module_id,
                                       'name': power_input.get('name'),
                                       'day': sensor_values[0],
                                       'night': sensor_values[1],
                                       'timestamp': self._timestamp2isoformat()}
                    mqtt_messages.append({'topic': sensor_config.get('topic').format(module_id=module_id, sensor_id=input_id),
                                          'message': sensor_data})
        return mqtt_messages

    def _create_background_task(self, sensor_type, data_retriever, data_processor):
        def background_function():
            while True:
                if self._enabled:
                    sensor_config = self._sensor_config.get(sensor_type)
                    frequency = sensor_config.get('poll_frequency')
                    self.logger('Background task to retrieve {0} sensor data started, will run every {1} seconds.'.format(sensor_type, frequency))
                    # highest frequency is every 10s
                    while frequency >= 10:
                        start = time.time()
                        try:
                            if sensor_config.get('enabled'):
                                result = json.loads(data_retriever())
                                if result['success'] is False:
                                    self.logger('Failed to load {0} sensor data: {1}'.format(sensor_type, result.get('msg')))
                                else:
                                    mqtt_messages = data_processor(sensor_config, result)
                                    for mqtt_message in mqtt_messages:
                                        thread = Thread(target=self._send,
                                                        args=(mqtt_message.get('topic'),
                                                              mqtt_message.get('message'),
                                                              sensor_config.get('qos'),
                                                              sensor_config.get('retain')))
                                        thread.start()
                        except Exception as ex:
                            self.logger('Error processing {0} sensor status: {1}'.format(sensor_type, ex))
                        # This loop will run approx. every 'frequency' seconds
                        sleep = frequency - (time.time() - start)
                        if sleep < 0:
                            sleep = 1
                        time.sleep(sleep)
                else:
                    time.sleep(15)
        return background_function

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
            self._config = config
            self._read_config()
            self.write_config(config)
            if self._enabled:
                thread = Thread(target=self._load_configuration)
                thread.start()
        except Exception as ex:
            self.logger('Error saving configuration: {0}'.format(ex))

        self._try_connect()
        return json.dumps({'success': True})
