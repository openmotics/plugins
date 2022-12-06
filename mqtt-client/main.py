# coding=utf-8
"""
An MQTT client plugin for sending/receiving data to/from an MQTT broker.
For more info: https://github.com/openmotics/plugins/blob/master/mqtt-client/README.md
"""

import six
import sys
import re
import time
from datetime import datetime
import pytz
import json
from threading import Thread
from plugins.base import om_expose, input_status, output_status, shutter_status, OMPluginBase, PluginConfigChecker, receive_events, om_metric_receive, background_task
from serial_utils import CommunicationTimedOutException
import logging

logger = logging.getLogger(__name__)

class MQTTClient(OMPluginBase):
    """
    An MQTT client plugin for sending/receiving data to/from an MQTT broker.
    For more info: https://github.com/openmotics/plugins/blob/master/mqtt-client/README.md
    """

    name = 'MQTTClient'
    version = '3.1.0'
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
        # home assistant support
        {
         'name': 'homeassistant_discovery_enabled',
         'type': 'bool',
         'description': 'Enable HomeAssistant Components Discovery.'
        },
        {'name': 'homeassistant_qos',
         'type': 'enum',
         'choices': ['0', '1', '2'],
         'description': 'Home Assistant message quality of service. Default: 0'},
        {'name': 'homeassistant_retain',
         'type': 'bool',
         'description': 'Home Assistant message retain.'},
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
        # shutter status
        {'name': 'shutter_status_enabled',
         'type': 'bool',
         'description': 'Enable shutter status publishing of messages.'},
        {'name': 'shutter_state_topic_format',
         'type': 'str',
         'description': 'Shutter state topic format. Default: openmotics/shutter/{id}/state'},
        {'name': 'shutter_position_topic_format',
         'type': 'str',
         'description': 'Shutter position topic format. Default: openmotics/shutter/{id}/position'},
        {'name': 'shutter_status_qos',
         'type': 'enum',
         'choices': ['0', '1', '2'],
         'description': 'Shutter status message quality of service. Default: 0'},
        {'name': 'shutter_status_retain',
         'type': 'bool',
         'description': 'Shutter status message retain.'},
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
        # sensor status
        {'name': 'sensor_status_enabled',
         'type': 'bool',
         'description': 'Enable sensor status publishing of messages.'},
        {'name': 'sensor_status_topic_format',
         'type': 'str',
         'description': 'Sensor status topic format. Default: openmotics/sensor/{id}/state'},
        {'name': 'sensor_status_qos',
         'type': 'enum',
         'choices': ['0', '1', '2'],
         'description': 'Sensor status message quality of service. Default: 0'},
        {'name': 'sensor_status_retain',
         'type': 'bool',
         'description': 'Sensor status message retain.'},
        {'name': 'sensor_status_poll_frequency',
         'type': 'int',
         'description': 'Polling frequency for sensor status in seconds. Default: 300, minimum: 10'},
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
        # shutter command
        {'name': 'shutter_command_topic',
         'type': 'str',
         'description': 'Topic to subscribe to for shutter command messages. Leave empty to turn off.'},
        # shutter position command
        {'name': 'shutter_position_command_topic',
         'type': 'str',
         'description': 'Topic to subscribe to for shutter position command messages. Leave empty to turn off.'},
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
        'homeassistant_qos': 0,
        'input_status_topic_format': 'openmotics/input/{id}/state',
        'input_status_qos': 0,
        'output_status_topic_format': 'openmotics/output/{id}/state',
        'output_status_qos': 0,
        'shutter_state_topic_format': 'openmotics/shutter/{id}/state',
        'shutter_position_topic_format': 'openmotics/shutter/{id}/position',
        'shutter_status_qos': 0,
        'event_status_topic_format': 'openmotics/event/{id}/state',
        'event_status_qos': 0,
        'sensor_status_topic_format': 'openmotics/sensor/{id}/state',
        'sensor_status_qos': 0,
        'sensor_status_poll_frequency': 300,
        'power_status_topic_format': 'openmotics/power/{module_id}/{sensor_id}/state',
        'power_status_qos': 0,
        'power_status_poll_frequency': 60,
        'energy_status_topic_format': 'openmotics/energy/{module_id}/{sensor_id}/state',
        'energy_status_qos': 0,
        'energy_status_poll_frequency': 3600,
        'output_command_topic': 'openmotics/output/+/set',
        'shutter_command_topic': 'openmotics/shutter/+/set',
        'shutter_position_command_topic': 'openmotics/shutter/+/position/set',
        'logging_topic': 'openmotics/logging',
        'timezone': 'UTC'
    }

    def __init__(self, webinterface, connector):
        super(MQTTClient, self).__init__(webinterface=webinterface,
                                            connector=connector)

        logger.info('Starting MQTTClient plugin...')

        self._config = self.read_config(MQTTClient.default_config)
        #logger.info("Default configuration '{0}'".format(self._config))
        self._config_checker = PluginConfigChecker(MQTTClient.config_description)

        paho_mqtt_wheel = '/opt/openmotics/python/plugins/MQTTClient/paho_mqtt-1.5.0-py2-none-any.whl'
        if paho_mqtt_wheel not in sys.path:
            sys.path.insert(0, paho_mqtt_wheel)

        self.client = None
        self._sensor_config = {}
        self._inputs = {}
        self._outputs = {}
        self._shutters = {}
        self._sensors = {}
        self._power_modules = {}
        self._rooms = {}

        self._read_config()
        self._try_connect()

        self._load_configuration()

        logger.info("Started MQTTClient plugin")

    def _read_config(self):
        # broker
        self._hostname = self._config.get('hostname')
        self._port     = self._config.get('port')
        self._username = self._config.get('username')
        self._password = self._config.get('password')
        # home assistant support
        self._homeassistant_discovery_enabled = self._config.get('homeassistant_discovery_enabled')
        self._homeassistant_qos     = int(self._config.get('homeassistant_qos'))
        self._homeassistant_retain  = self._config.get('homeassistant_retain')
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
        # shutters
        self._shutter_enabled          = self._config.get('shutter_status_enabled')
        self._shutter_topic            = self._config.get('shutter_state_topic_format')
        self._shutter_position_topic   = self._config.get('shutter_position_topic_format')
        self._shutter_qos              = int(self._config.get('shutter_status_qos'))
        self._shutter_retain           = self._config.get('shutter_status_retain')
        # events
        self._event_enabled = self._config.get('event_status_enabled')
        self._event_topic   = self._config.get('event_status_topic_format')
        self._event_qos     = int(self._config.get('event_status_qos'))
        self._event_retain  = self._config.get('event_status_retain')
        # sensors
        self._sensor_config = {
            'sensor': {
                'enabled':        self._config.get('sensor_status_enabled'),
                'topic':          self._config.get('sensor_status_topic_format'),
                'qos':            int(self._config.get('sensor_status_qos')),
                'retain':         self._config.get('sensor_status_retain'),
                'poll_frequency': int(self._config.get('sensor_status_poll_frequency'))
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
        self._sensor_enabled = self._sensor_config.get('sensor').get('enabled')
        self._power_enabled = (self._sensor_config.get('power').get('enabled') or self._sensor_config.get('energy').get('enabled'))
        # output command
        self._output_command_topic = self._config.get('output_command_topic')
        # shutter command
        self._shutter_command_topic = self._config.get('shutter_command_topic')
        # shutter position command
        self._shutter_position_command_topic = self._config.get('shutter_position_command_topic')
        # logging topic
        self._logging_topic = self._config.get('logging_topic')
        # timezone
        self._timezone = self._config.get('timezone')
        self._enabled = self._hostname is not None and self._port is not None
        logger.info('MQTTClient is {0}'.format('enabled' if self._enabled else 'disabled'))

    def _load_configuration(self):
        inputs_loaded = False
        outputs_loaded = False
        shutters_loaded = False
        sensors_loaded = False
        power_loaded = False
        rooms_loaded = False
        should_load = True

        while should_load:
            if not inputs_loaded:
                inputs_loaded = self._load_input_configuration()
            if not outputs_loaded:
                outputs_loaded = self._load_output_configuration()
            if not shutters_loaded:
                shutters_loaded = self._load_shutter_configuration()
            if not sensors_loaded:
                sensors_loaded = self._load_sensor_configuration()
            if not power_loaded:
                power_loaded = self._load_power_configuration()
            if not rooms_loaded:
                rooms_loaded = self._load_rooms_configuration()
            should_load = not all([inputs_loaded, outputs_loaded, shutters_loaded, sensors_loaded, power_loaded, rooms_loaded])
            if should_load:
                time.sleep(15)

        self._load_homeassistant_discovery()

    def _load_homeassistant_discovery(self):
        if self._homeassistant_discovery_enabled:
            try:
                self._logger('HomeAssistant Discovery started...')
                
                self._load_homeassistant_shutter_discovery()
                self._load_homeassistant_energy_discovery()
                self._load_homeassistant_power_discovery()
                self._load_homeassistant_sensor_discovery()

                self._logger('HomeAssistant Discovery finished.')
            except Exception as ex:
                self._logger('Error while loading HomeAssistant components discovery: {0}'.format(ex))

    def _load_homeassistant_shutter_discovery(self):
        if self._config.get('shutter_status_enabled'):
            for shutter_id in self._shutters.keys():
                shutter = self._shutters[shutter_id]
                thread = Thread(
                    target=self._send,
                    args=(
                        'homeassistant/cover/openmotics/{0}/config'.format(shutter_id), 
                        self._dump_shutter_discovery_json(shutter_id, shutter), 
                        self._homeassistant_qos, 
                        self._homeassistant_retain
                    )
                )
                thread.start()

    def _dump_shutter_discovery_json(self, shutter_id, shutter):
        room = ''

        if shutter.get('room_id') in self._rooms:
            room = self._rooms[shutter.get('room_id')]['name']

        return {
            "name": "OpenMotics {0} Shutter".format(shutter.get('name')),
            "friendly_name": shutter.get('name'),
            "unique_id": "openmotics {0} shutter".format(shutter.get('name').lower()),
            "set_position_topic": self._config.get('shutter_position_command_topic').replace('+', str(shutter_id)),
            "position_topic": self._config.get('shutter_position_topic_format').format(id=shutter_id),
            "command_topic": self._config.get('shutter_command_topic').replace('+', str(shutter_id)),
            "retain": "true",
            "payload_open": "up",
            "payload_close": "down",
            "payload_stop": "stop",
            "state_opening": "going_up",
            "state_closed": "down",
            "state_stopped": "stopped",
            "position_open": 0,
            "position_closed": 99,
            "device": {
                "name": "Shutter {0}".format(shutter.get('name')),
                "identifiers": "Shutter {0}".format(shutter.get('name')),
                "manufacturer": "OpenMotics",
                "model": "Relay module",
                "suggested_area": room
            },
            "device_class": "shutter"
        }

    def _load_homeassistant_energy_discovery(self):
        if self._config.get('energy_status_enabled'):
            for module_id in self._power_modules.keys():
                module_config = self._power_modules[module_id]

                for sensor_id in module_config.keys():
                    if module_config[sensor_id].get('name'):
                        thread = Thread(
                            target=self._send,
                            args=(
                                'homeassistant/sensor/{0}_energy/{1}/config'.format(module_id, sensor_id), 
                                self._dump_energy_discovery_json(module_id, sensor_id, module_config[sensor_id]), 
                                self._homeassistant_qos, 
                                self._homeassistant_retain
                            )
                        )
                        thread.start()

    def _dump_energy_discovery_json(self, module_id, sensor_id, sensor):
        return {
            "name": "OpenMotics {0} Energy".format(sensor.get('name')),
            "unique_id": "openmotics {0} energy".format(sensor.get('name').lower()),
            "state_topic": self._config.get('energy_status_topic_format').format(module_id=module_id, sensor_id=sensor_id),
            "value_template": "{{ value_json.night / 1000 | float | round(2) }}",
            "unit_of_measurement": "kWh",
            "device": {
                "name": "Energy {0}".format(sensor.get('name')),
                "identifiers": "Energy {0}".format(sensor.get('name')),
                "manufacturer": "OpenMotics",
                "model": "Energy module"
            },
            "device_class": "energy",
            "state_class": "total_increasing"
        }

    def _load_homeassistant_power_discovery(self):
        if self._config.get('power_status_enabled'):
            for module_id in self._power_modules.keys():
                module_config = self._power_modules[module_id]

                for sensor_id in module_config.keys():
                    if module_config[sensor_id].get('name'):
                        self._send_power_discovery(module_id, sensor_id, module_config[sensor_id])
                        self._send_power_voltage_discovery(module_id, sensor_id, module_config[sensor_id])
                        self._send_power_current_discovery(module_id, sensor_id, module_config[sensor_id])
                        self._send_power_frequency_discovery(module_id, sensor_id, module_config[sensor_id])

    def _send_power_discovery(self, module_id, sensor_id, sensor):
        thread = Thread(
            target=self._send,
            args=(
                'homeassistant/sensor/{0}_power/{1}/config'.format(module_id, sensor_id), 
                self._dump_power_discovery_json(module_id, sensor_id, sensor), 
                self._homeassistant_qos, 
                self._homeassistant_retain
            )
        )
        thread.start()

    def _dump_power_discovery_json(self, module_id, sensor_id, sensor):
        return {
            "name": "OpenMotics {0} Power".format(sensor.get('name')),
            "unique_id": "openmotics {0} power".format(sensor.get('name').lower()),
            "state_topic": self._config.get('power_status_topic_format').format(module_id=module_id, sensor_id=sensor_id),
            "value_template": "{{ value_json.power | float | round(2) }}",
            "unit_of_measurement": "W",
            "device": {
                "name": "Energy {0}".format(sensor.get('name')),
                "identifiers": "Energy {0}".format(sensor.get('name')),
                "manufacturer": "OpenMotics",
                "model": "Energy module"
            },
            "device_class": "power",
            "state_class": "measurement"
        }

    def _send_power_voltage_discovery(self, module_id, sensor_id, sensor):
        thread = Thread(
            target=self._send,
            args=(
                'homeassistant/sensor/{0}_power_voltage/{1}/config'.format(module_id, sensor_id), 
                self._dump_power_voltage_discovery_json(module_id, sensor_id, sensor), 
                self._homeassistant_qos, 
                self._homeassistant_retain
            )
        )
        thread.start()

    def _dump_power_voltage_discovery_json(self, module_id, sensor_id, sensor):
        return {
            "name": "OpenMotics {0} Voltage".format(sensor.get('name')),
            "unique_id": "openmotics {0} voltage".format(sensor.get('name').lower()),
            "state_topic": self._config.get('power_status_topic_format').format(module_id=module_id, sensor_id=sensor_id),
            "value_template": "{{ value_json.voltage | float | round(2) }}",
            "unit_of_measurement": "V",
            "device": {
                "name": "Energy {0}".format(sensor.get('name')),
                "identifiers": "Energy {0}".format(sensor.get('name')),
                "manufacturer": "OpenMotics",
                "model": "Energy module"
            },
            "device_class": "voltage",
            "state_class": "total_increasing"
        }

    def _send_power_current_discovery(self, module_id, sensor_id, sensor):
        thread = Thread(
            target=self._send,
            args=(
                'homeassistant/sensor/{0}_power_current/{1}/config'.format(module_id, sensor_id), 
                self._dump_power_current_discovery_json(module_id, sensor_id, sensor), 
                self._homeassistant_qos, 
                self._homeassistant_retain
            )
        )
        thread.start()

    def _dump_power_current_discovery_json(self, module_id, sensor_id, sensor):
        return {
            "name": "OpenMotics {0} Current".format(sensor.get('name')),
            "unique_id": "openmotics {0} current".format(sensor.get('name').lower()),
            "state_topic": self._config.get('power_status_topic_format').format(module_id=module_id, sensor_id=sensor_id),
            "value_template": "{{ value_json.current | float | round(3) }}",
            "unit_of_measurement": "A",
            "device": {
                "name": "Energy {0}".format(sensor.get('name')),
                "identifiers": "Energy {0}".format(sensor.get('name')),
                "manufacturer": "OpenMotics",
                "model": "Energy module"
            },
            "device_class": "current",
            "state_class": "total_increasing"
        }

    def _send_power_frequency_discovery(self, module_id, sensor_id, sensor):
        thread = Thread(
            target=self._send,
            args=(
                'homeassistant/sensor/{0}_power_frequency/{1}/config'.format(module_id, sensor_id), 
                self._dump_power_frequency_discovery_json(module_id, sensor_id, sensor), 
                self._homeassistant_qos, 
                self._homeassistant_retain
            )
        )
        thread.start()

    def _dump_power_frequency_discovery_json(self, module_id, sensor_id, sensor):
        return {
            "name": "OpenMotics {0} Frequency".format(sensor.get('name')),
            "unique_id": "openmotics {0} frequency".format(sensor.get('name').lower()),
            "state_topic": self._config.get('power_status_topic_format').format(module_id=module_id, sensor_id=sensor_id),
            "value_template": "{{ value_json.frequency | float | round(2) }}",
            "unit_of_measurement": "Hz",
            "device": {
                "name": "Energy {0}".format(sensor.get('name')),
                "identifiers": "Energy {0}".format(sensor.get('name')),
                "manufacturer": "OpenMotics",
                "model": "Energy module"
            },
            "device_class": "frequency",
            "state_class": "total_increasing"
        }

    def _load_homeassistant_sensor_discovery(self):
        if self._config.get('sensor_status_enabled'):
            for sensor_id in self._sensors.keys():
                sensor = self._sensors[sensor_id]

                sensor_data = self._dump_sensor_discovery_json(sensor_id, sensor)
                if sensor_data is not None:
                    thread = Thread(
                        target=self._send,
                        args=(
                            'homeassistant/sensor/openmotics_{0}/{1}/config'.format(sensor.get('physical_quantity'), sensor_id), 
                            sensor_data, 
                            self._homeassistant_qos, 
                            self._homeassistant_retain
                        )
                    )
                    thread.start()

    def _dump_sensor_discovery_json(self, sensor_id, sensor):
        if sensor.get('physical_quantity').lower() == 'temperature':
            # default temperature is celsius
            unit_of_measurement = 'ºC'
            device_class = 'temperature'
        elif sensor.get('physical_quantity').lower() == 'humidity':
            unit_of_measurement = '%'
            device_class = 'humidity'
        else:
            return None

        room = ''

        if sensor.get('room_id') in self._rooms:
            room = self._rooms[sensor.get('room_id')]['name']

        return {
            "name": sensor.get('name'),
            "unique_id": "openmotics {0} {1}".format(sensor.get('name').lower(), sensor.get('physical_quantity').lower()),
            "state_topic": self._config.get('sensor_status_topic_format').format(id=sensor_id),
            "value_template": "{{ value_json.value | float | round(2) }}",
            "unit_of_measurement": unit_of_measurement,
            "device": {
                "name": "Sensor {0}".format(sensor.get('name')),
                "identifiers": "Sensor {0}".format(sensor.get('name')),
                "manufacturer": "OpenMotics",
                "model": "Sensor module",
                "suggested_area": room
            },
            "device_class": device_class,
            "state_class": "measurement"
        }

    def _load_input_configuration(self):
        input_config_loaded = True
        if self._input_enabled:
            try:
                result = json.loads(self.webinterface.get_input_configurations())
                if result['success'] is False:
                    logger.error('Failed to load input configurations')
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
                    logger.info('Configuring {0} inputs'.format(len(ids)))
            except Exception as ex:
                logger.exception('Error while loading input configurations')
                input_config_loaded = False
            try:
                result = json.loads(self.webinterface.get_input_status())
                if result['success'] is False:
                    logger.error('Failed to get input status')
                    input_config_loaded = False
                else:
                    for input_data in result['status']:
                        input_id = input_data['id']
                        if input_id not in self._inputs:
                            continue
                        self._inputs[input_id]['status'] = input_data['status']
            except Exception as ex:
                logger.exception('Error getting input status')
                input_config_loaded = False
        return input_config_loaded

    def _load_output_configuration(self):
        output_config_loaded = True
        if self._output_enabled:
            try:
                result = json.loads(self.webinterface.get_output_configurations())
                if result['success'] is False:
                    output_config_loaded = False
                    logger.error('Failed to load output configurations')
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
                                                    'room_id': config['room'],
                                                    'type': 'relay' if config['type'] == 0 else 'light'}
                    for output_id in self._outputs.keys():
                        if output_id not in ids:
                            del self._outputs[output_id]
                    logger.info('Configuring {0} outputs'.format(len(ids)))
            except Exception as ex:
                output_config_loaded = False
                logger.exception('Error while loading output configurations')
            try:
                result = json.loads(self.webinterface.get_output_status())
                if result['success'] is False:
                    output_config_loaded = False
                    logger.error('Failed to get output status')
                else:
                    for output in result['status']:
                        output_id = output['id']
                        if output_id not in self._outputs:
                            continue
                        self._outputs[output_id]['status'] = output['status']
                        self._outputs[output_id]['dimmer'] = output['dimmer']
            except Exception as ex:
                output_config_loaded = False
                logger.exception('Error getting output status')
        return output_config_loaded

    def _load_shutter_configuration(self):
        shutter_config_loaded = True
        if self._shutter_enabled:
            try:
                result = json.loads(self.webinterface.get_shutter_configurations())
                if result['success'] is False:
                    shutter_config_loaded = False
                    self._logger('Failed to load shutter configurations')
                else:
                    ids = []
                    for config in result['config']:
                        if not config['in_use']:
                            continue
                        if not config['module']['hardware_type'] == "physical":
                            continue
                        shutter_id = config['id']
                        ids.append(shutter_id)
                        self._shutters[shutter_id] = {'name': config['name'],
                                                     'module_id': config['module']['module_id'],
                                                     'type': config['module']['hardware_module'],
                                                     'timer_up': config['timer_up'],
                                                     'timer_down': config['timer_down'],
                                                     'steps': config['steps'],
                                                     'up_down_config': config['up_down_config'],
                                                     'room_id': config['room']
                                                    }
                    for shutter_id in self._shutters.keys():
                        if shutter_id not in ids:
                            del self._shutters[shutter_id]
                    self._logger('Configuring {0} shutters'.format(len(ids)))
            except Exception as ex:
                shutter_config_loaded = False
                self._logger('Error while loading shutter configurations')
            try:
                result = json.loads(self.webinterface.get_shutter_status())
                if result['success'] is False:
                    shutter_config_loaded = False
                    self._logger('Failed to get shutter status')
                else:
                    for id in sorted(result['detail']):
                        shutter_id = int(id)
                        if shutter_id not in self._shutters:
                            continue
                        state = result['detail'][id]['state']
                        position = result['detail'][id]['actual_position']
                        self._logger('Shutter {0} state {1}'.format(shutter_id, state))
                        self._shutters[shutter_id]['state'] = state
                        if position is not None:
                            self._shutters[shutter_id]['position'] = position
            except Exception as ex:
                shutter_config_loaded = False
                self._logger('Error getting shutter status: {0}'.format(ex))
        return shutter_config_loaded

    def _load_sensor_configuration(self):
        sensor_config_loaded = True
        if self._sensor_enabled:
            try:
                result = json.loads(self.webinterface.get_sensor_configurations())
                if result['success'] is False:
                    sensor_config_loaded = False
                    logger.error('Failed to load sensor configurations: {0}'.format(result.get('msg')))
                else:
                    ids = []
                    for config in result['config']:
                        sensor_id = config['id']
                        ids.append(sensor_id)
                        self._sensors[sensor_id] = {'name': config['name'],
                                                    'external_id': str(config['external_id']),
                                                    'room_id': config['room'],
                                                    'physical_quantity': str(config['physical_quantity']),
                                                    'offset': config['offset'],
                                                    'source': config.get('source'),
                                                    'unit': config.get('unit')}
                    for sensor_id in self._sensors.keys():
                        if sensor_id not in ids:
                            del self._sensors[sensor_id]
                    logger.info('Configuring {0} sensors'.format(len(ids)))
            except Exception as ex:
                sensor_config_loaded = False
                logger.exception('Error while loading sensor configurations: {0}'.format(ex))
        return sensor_config_loaded

    def _load_power_configuration(self):
        power_config_loaded = True
        if self._power_enabled:
            try:
                result = json.loads(self.webinterface.get_power_modules())
                if result['success'] is False:
                    power_config_loaded = False
                    logger.error('Failed to load power configurations: {0}'.format(result.get('msg')))
                else:
                    ids = []
                    for module in result['modules']:
                        module_id = int(module['id'])
                        ids.append(module_id)
                        version = int(module['version'])
                        input_count = MQTTClient.energy_module_config.get(version, 0)
                        module_config = {}
                        if input_count == 0:
                            logger.warning('Warning: Skipping energy module {0}, version {1} is currently not supported by this plugin. Only versions: {2}'.format(
                                module_id,
                                version,
                                ', '.join(MQTTClient.energy_module_config.keys())))
                            continue
                        else:
    	                    logger.info('Configuring energy module {0} (version {1}) with {2} inputs'.format(module_id, version, input_count))
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
                logger.exception('Error while loading power configurations')
        return power_config_loaded

    def _load_rooms_configuration(self):
        room_config_loaded = True
        try:
            result = json.loads(self.webinterface.get_room_configurations())
            if result['success'] is False:
                self._logger('Failed to load room configurations')
                room_config_loaded = False
            else:
                ids = []
                for config in result['config']:
                    room_id = config['id']
                    if not config['name'].strip():
                        continue
                    ids.append(room_id)
                    self._rooms[room_id] = config
                self._logger('Configuring {0} rooms'.format(len(ids)))
        except Exception as ex:
            self._logger('Error while loading rooms configurations')
            room_config_loaded = False
        return room_config_loaded

    def _try_connect(self):
        if self._enabled is True:
            try:
                import paho.mqtt.client as client
                self.client = client.Client()
                if self._username is not None:
                    logger.info("MQTTClient is using username '{0}' and password".format(self._username))
                    self.client.username_pw_set(self._username, self._password)
                self.client.on_message = self.on_message
                self.client.on_connect = self.on_connect
                self.client.connect(self._hostname, self._port, 5)
                self.client.loop_start()
            except Exception as ex:
                logger.exception('Error connecting to MQTT broker')

    def _log(self, info):
        # for log messages QoS = 0 and retain = False
        thread = Thread(target=self._send, args=(self._logging_topic, info, 0, False))
        thread.start()

    def _send(self, topic, data, qos, retain):
        try:
            self.client.publish(topic, payload=json.dumps(data), qos=qos, retain=retain)
        except Exception as ex:
            logger.exception('Error sending data to topic {0}'.format(topic))

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
                    logger.info('Input {0} ({1}) switched {2}'.format(input_id, name,  status))
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
                    logger.error('Got event for unknown input {0}'.format(input_id))
            except Exception as ex:
                logger.exception('Error processing input {0}'.format(input_id))

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
                            logger.info('Output {0} ({1}) changed to ON'.format(output_id, name))
                        if dimmer != new_output_status[output_id]:
                            changed = True
                            current_output_status[output_id]['dimmer'] = new_output_status[output_id]
                            self._log('Output {0} ({1}) changed to level {2}'.format(output_id, name, new_output_status[output_id]))
                            logger.info('Output {0} ({1}) changed to level {2}'.format(output_id, name, new_output_status[output_id]))
                    elif status != 0:
                        changed = True
                        current_output_status[output_id]['status'] = 0
                        self._log('Output {0} ({1}) changed to OFF'.format(output_id, name))
                        logger.info('Output {0} ({1}) changed to OFF'.format(output_id, name))
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
                logger.exception('Error processing outputs')

    @shutter_status(version = 2)
    def shutter_status(self, status, detail):
        if self._enabled and self._shutter_enabled:
            try:
                new_shutter_status = {}
                for id, state in enumerate(status):
                    new_shutter_status[id] = {}
                    new_shutter_status[id]['state'] = state
                    new_shutter_status[id]['position'] = detail[id]['actual_position']
                current_shutter_status = self._shutters
                for shutter_id in current_shutter_status:
                    name = current_shutter_status[shutter_id].get('name')
                    state = current_shutter_status[shutter_id].get('state')
                    position = current_shutter_status[shutter_id].get('position', None)

                    new_state = new_shutter_status[shutter_id]['state']
                    new_position = new_shutter_status[shutter_id]['position']
                    if shutter_id in new_shutter_status:
                        if state != new_state:
                            current_shutter_status[shutter_id]['state'] = new_state
                            current_shutter_status[shutter_id]['position'] = new_position
                            thread = Thread(
                                target=self._send,
                                args=(self._shutter_topic.format(id=shutter_id), new_state, self._shutter_qos, self._shutter_retain)
                            )
                            thread.start()
                            self._logger('Shutter {0} ({1}) changed to {2} ({3})'.format(shutter_id, name, new_state, new_position), True)

                        if position != new_position:
                            thread = Thread(
                                target=self._send,
                                args=(self._shutter_position_topic.format(id=shutter_id), new_position, self._shutter_qos, self._shutter_retain)
                            )
                            thread.start()
            except Exception as ex:
                self._logger('Error processing shutters: {0}'.format(ex))

    @receive_events
    def receive_events(self, event_id):
        if self._enabled and self._event_enabled:
            try:
                self._log('Got event {0}'.format(event_id))
                logger.info('Got event {0}'.format(event_id))
                data = {'id': event_id,
                        'timestamp': self._timestamp2isoformat()}
                thread = Thread(
                    target=self._send,
                    args=(self._event_topic.format(id=event_id), data, self._event_qos, self._event_retain)
                )
                thread.start()
            except Exception as ex:
                logger.exception('Error processing event')

    @background_task
    def background_task_sensor_status(self):
        self._create_background_task(
            'sensor',
            self.webinterface.get_sensor_status,
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

    def _parse_sensor_value(self, value):
        if type(value) == float:
            return value
        return float(value)

    def _process_sensor_status(self, sensor_config, json_data):
        mqtt_messages = []
        data_list = list(filter(None, json_data.get('status', [])))
        for sensor_data in data_list:
            sensor_id, sensor_value = sensor_data.values()
            sensor = self._sensors.get(sensor_id)
            if sensor:
                sensor_data = {'id': sensor_id,
                               'source': sensor.get('source'),
                               'external_id': sensor.get('external_id'),
                               'physical_quantity': sensor.get('physical_quantity'),
                               'offset': sensor.get('offset'),
                               'unit': sensor.get('unit'),
                               'name': sensor.get('name'),
                               'value': self._parse_sensor_value(sensor_value),
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
                    logger.info('Background task to retrieve {0} sensor data started, will run every {1} seconds.'.format(sensor_type, frequency))
                    # highest frequency is every 10s
                    while frequency >= 10:
                        start = time.time()
                        try:
                            if sensor_config.get('enabled'):
                                result = json.loads(data_retriever())
                                if result['success'] is False:
                                    logger.error('Failed to load {0} sensor data: {1}'.format(sensor_type, result.get('msg')))
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
                            logger.exception('Error processing {0} sensor status {1}'.format(sensor_type, ex))
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
            self._logger('Error connecting: rc={0}', rc)
            return

        logger.info('Connected to MQTT broker {0}:{1}'.format(self._hostname, self._port))
        # subscribe to output command topic if provided
        if self._output_command_topic:
            try:
                self.client.subscribe(self._output_command_topic)
                logger.info('Subscribed to {0}'.format(self._output_command_topic))
            except Exception as ex:
                self._logger('Could not subscribe to {0}: {1}'.format(self._output_command_topic, ex))

        # subscribe to shutter command topic if provided
        if self._shutter_command_topic:
            try:
                self.client.subscribe(self._shutter_command_topic)
                self._logger('Subscribed to {0}'.format(self._shutter_command_topic))
            except Exception as ex:
                self._logger('Could not subscribe to {0}: {1}'.format(self._shutter_command_topic, ex))

        # subscribe to shutter position command topic if provided
        if self._shutter_position_command_topic:
            try:
                self.client.subscribe(self._shutter_position_command_topic)
                self._logger('Subscribed to {0}'.format(self._shutter_position_command_topic))
            except Exception as ex:
                self._logger('Could not subscribe to {0}: {1}'.format(self._shutter_position_command_topic, ex))

    def on_message(self, client, userdata, msg):
        output_regexp = self._output_command_topic.replace('+', '(\d+)')
        shutter_regexp = self._shutter_command_topic.replace('+', '(\d+)')
        shutter_position_regexp = self._shutter_position_command_topic.replace('+', '(\d+)')

        if re.search(output_regexp, msg.topic) is not None:
            # the output_id is the first match of the regular expression
            output_id = int(re.findall(output_regexp, msg.topic)[0])
            self._output_command(output_id, msg)
        elif re.search(shutter_regexp, msg.topic) is not None:
            # the shutter_id is the first match of the regular expression
            shutter_id = int(re.findall(shutter_regexp, msg.topic)[0])
            self._shutter_command(shutter_id, msg)
        elif re.search(shutter_position_regexp, msg.topic) is not None:
            # the shutter_id is the first match of the regular expression
            shutter_id = int(re.findall(shutter_position_regexp, msg.topic)[0])
            self._shutter_position_command(shutter_id, msg)
        else:
            self._log('Message with topic {0} ignored'.format(msg.topic))
            self.logger('Message with topic {0} ignored'.format(msg.topic))

    def _output_command(self, output_id, msg):
        try:
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
                        log_value = '{0} ON ({1}%)'.format(output_id, value)
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
            self._log('Failed to process message')

    def _shutter_command(self, shutter_id, msg):
        try:
            log_message = 'Execute shutter command on shutter {0}'.format(shutter_id)
            self._log(log_message)
            self.logger(log_message)

            if shutter_id in self._shutters:
                shutter = self._shutters[shutter_id]
                value = msg.payload
                if value.lower() in ['up', 'down', 'stop']:
                    thread = Thread(
                        target=self._execute_shutter_command,
                        args=(
                            shutter_id,
                            value.lower()
                        )
                    )
                    thread.start()
                else:
                    log_message = 'Failed to set shutter {0} to {1}'.format(shutter_id, value)
                    self._log(log_message)
                    self.logger(log_message)
            else:
                self._log('Unknown shutter: {0}'.format(shutter_id))
        except Exception as ex:
            self._log('Failed to process message: {0}'.format(ex))

    def _execute_shutter_command(self, shutter_id, command):
        try:
            if command == 'up':
                result = json.loads(self.webinterface.do_shutter_up(id=shutter_id))
            elif command == 'down':
                result = json.loads(self.webinterface.do_shutter_down(id=shutter_id))
            else:
                result = json.loads(self.webinterface.do_shutter_stop(id=shutter_id))

            if result['success'] is False:
                log_message = 'Failed to set shutter {0} to up: {1}'.format(shutter_id, result.get('msg', 'Unknown error'))
                self._log(log_message)
                self.logger(log_message)
            else:
                log_message = 'Message for shutter {0} with payload up'.format(shutter_id)
                self._log(log_message)
                self.logger(log_message)
        except Exception as ex:
            self.logger('Error calling shutter up web service: {0}'.format(ex))

    def _shutter_position_command(self, shutter_id, msg):
        try:
            log_message = 'Execute shutter position command on shutter {0}'.format(shutter_id)
            self._log(log_message)
            self.logger(log_message)

            if shutter_id in self._shutters:
                shutter = self._shutters[shutter_id]
                value = int(msg.payload)
                if value >= 0 and value <=99:
                    thread = Thread(
                        target=self._execute_shutter_position_command,
                        args=(
                            shutter_id,
                            value
                        )
                    )
                    thread.start()
                else:
                    log_message = 'Failed to set shutter {0} to {1}'.format(shutter_id, value)
                    self._log(log_message)
                    self.logger(log_message)
            else:
                self._log('Unknown shutter: {0}'.format(shutter_id))
        except Exception as ex:
            self._log('Failed to process message: {0}'.format(ex))

    def _execute_shutter_position_command(self, shutter_id, position):
        try:
            result = json.loads(self.webinterface.do_shutter_goto(id=shutter_id, position=position))

            if result['success'] is False:
                log_message = 'Failed to set shutter {0} to position {1}: {2}'.format(shutter_id, position, result.get('msg', 'Unknown error'))
                self._log(log_message)
                self.logger(log_message)
            else:
                log_message = 'Message for shutter {0} with payload {1}'.format(shutter_id, position)
                self._log(log_message)
                self.logger(log_message)
        except Exception as ex:
            self._logger('Error calling shutter position web service: {0}'.format(ex))

    def _logger(self, message, mqtt_logging=False):
        if mqtt_logging:
            self._log(message)
        self.logger(message)

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
                if isinstance(config[key], six.string_types):
                    config[key] = str(config[key])
            self._config_checker.check_config(config)
            self._config = config
            self._read_config()
            self.write_config(config)
            if self._enabled:
                thread = Thread(target=self._load_configuration)
                thread.start()
        except Exception as ex:
            logger.exception('Error saving configuration')

        self._try_connect()
        return json.dumps({'success': True})
