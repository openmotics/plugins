# coding=utf-8
"""
HomeAssistant MQTT Discovery
"""

from enums import OutputType, HardwareType
from threading import Thread
import simplejson as json

class HomeAssistant():
    """
    Openmotics outputs not supported on HomeAssistant:
        OutputType.ALARM: 'alarm',
        OutputType.APPLIANCE: 'appliance',
        OutputType.PUMP: 'pump',
        OutputType.HVAC: 'hvac',
        OutputType.GENERIC: 'generic',
        OutputType.MOTOR: 'motor',
        OutputType.HEATER: 'heater',
    """
    output_ha_types = {OutputType.OUTLET: 'switch',
                       OutputType.VALVE: 'switch',
                       OutputType.VENTILATION: 'fan',
                       OutputType.SHUTTER_RELAY: 'shutter',
                       OutputType.LIGHT: 'light'}

    def __init__(self, logger, client, config, outputs, shutters, power_modules, sensors, rooms):
        self._logger = logger
        self._config = config
        self._enabled = self._config.get('homeassistant_discovery_enabled')
        self._qos = int(self._config.get('homeassistant_qos'))
        self._retain = self._config.get('homeassistant_retain')
        self._outputs = outputs
        self._shutters = shutters
        self._power_modules = power_modules
        self._sensors = sensors
        self._rooms = rooms
        self._client = client

    def start_discovery(self):
        if self._enabled:
            try:
                self._logger('HomeAssistant Discovery started...')
                
                self._output_discovery()
                self._shutter_discovery()
                self._energy_discovery()
                self._power_discovery()
                self._sensor_discovery()

                self._logger('HomeAssistant Discovery finished.')
            except Exception as ex:
                self._logger('Error while loading HomeAssistant components discovery: {0}'.format(ex))

    def _output_discovery(self):
        if self._config.get('output_status_enabled'):
            for output_id in self._outputs.keys():
                output = self._outputs[output_id]

                if output.get('type') == OutputType.LIGHT:
                    call_function = self._dump_light_discovery_json(output_id=output_id, light=output)
                elif output.get('type') == OutputType.OUTLET:
                    call_function = self._dump_switch_discovery_json(output_id=output_id, switch=output)
                elif output.get('type') == OutputType.VALVE:
                    call_function = self._dump_valve_discovery_json(output_id=output_id, valve=output)
                elif output.get('type') == OutputType.VENTILATION:
                    call_function = self._dump_ventilation_discovery_json(output_id=output_id, ventilation=output)
                else:
                    continue

                thread = Thread(
                    target=self._send,
                    args=(
                        'homeassistant/{0}/openmotics/{1}/config'.format(HomeAssistant.output_ha_types.get(output.get('type')), output_id), 
                        call_function,
                        self._qos, 
                        self._retain
                    )
                )
                thread.start()

    def _shutter_discovery(self):
        if self._config.get('shutter_status_enabled'):
            for shutter_id in self._shutters.keys():
                shutter = self._shutters[shutter_id]
                thread = Thread(
                    target=self._send,
                    args=(
                        'homeassistant/cover/openmotics/{0}/config'.format(shutter_id), 
                        self._dump_shutter_discovery_json(shutter_id, shutter), 
                        self._qos, 
                        self._retain
                    )
                )
                thread.start()

    def _energy_discovery(self):
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
                                self._qos, 
                                self._retain
                            )
                        )
                        thread.start()

    def _power_discovery(self):
        if self._config.get('power_status_enabled'):
            for module_id in self._power_modules.keys():
                module_config = self._power_modules[module_id]

                for sensor_id in module_config.keys():
                    if module_config[sensor_id].get('name'):
                        self._send_power_discovery(module_id, sensor_id, module_config[sensor_id])
                        self._send_power_voltage_discovery(module_id, sensor_id, module_config[sensor_id])
                        self._send_power_current_discovery(module_id, sensor_id, module_config[sensor_id])
                        self._send_power_frequency_discovery(module_id, sensor_id, module_config[sensor_id])

    def _sensor_discovery(self):
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
                            self._qos, 
                            self._retain
                        )
                    )
                    thread.start()

    def _send_power_discovery(self, module_id, sensor_id, sensor):
        thread = Thread(
            target=self._send,
            args=(
                'homeassistant/sensor/{0}_power/{1}/config'.format(module_id, sensor_id), 
                self._dump_power_discovery_json(module_id, sensor_id, sensor), 
                self._qos, 
                self._retain
            )
        )
        thread.start()

    def _send_power_voltage_discovery(self, module_id, sensor_id, sensor):
        thread = Thread(
            target=self._send,
            args=(
                'homeassistant/sensor/{0}_power_voltage/{1}/config'.format(module_id, sensor_id), 
                self._dump_power_voltage_discovery_json(module_id, sensor_id, sensor), 
                self._qos, 
                self._retain
            )
        )
        thread.start()

    def _send_power_current_discovery(self, module_id, sensor_id, sensor):
        thread = Thread(
            target=self._send,
            args=(
                'homeassistant/sensor/{0}_power_current/{1}/config'.format(module_id, sensor_id), 
                self._dump_power_current_discovery_json(module_id, sensor_id, sensor), 
                self._qos, 
                self._retain
            )
        )
        thread.start()

    def _send_power_frequency_discovery(self, module_id, sensor_id, sensor):
        thread = Thread(
            target=self._send,
            args=(
                'homeassistant/sensor/{0}_power_frequency/{1}/config'.format(module_id, sensor_id), 
                self._dump_power_frequency_discovery_json(module_id, sensor_id, sensor), 
                self._qos, 
                self._retain
            )
        )
        thread.start()

    def _dump_light_discovery_json(self, output_id, light):
        room = ''

        if light.get('room_id') in self._rooms:
            room = self._rooms[light.get('room_id')]['name']

        return {
            "name": light.get('name'),
            "unique_id": "openmotics {0} light".format(light.get('name').lower()),
            "state_topic": self._config.get('output_status_topic_format').format(id=output_id),
            "command_topic": self._config.get('output_command_topic').replace('+', str(output_id)),
            "retain": self._config.get('output_status_retain'),
            "state_value_template": "{{ value_json.value }}",
            "payload_on": "100",
            "payload_off": "0",
            "payload_available": "100",
            "payload_not_available": "0",
            "supported_color_modes": [],
            "device": {
                "name": "Light {0}".format(light.get('name')),
                "identifiers": "Light {0}".format(light.get('name')),
                "manufacturer": "OpenMotics",
                "model": ("Relay module" if light['hardware_type'] == HardwareType.PHYSICAL else "Virtual relay module"),
                "suggested_area": room
            },
            "device_class": HomeAssistant.output_ha_types.get(light.get('type'))
        }

    def _dump_switch_discovery_json(self, output_id, switch):
        room = ''

        if switch.get('room_id') in self._rooms:
            room = self._rooms[switch.get('room_id')]['name']

        return {
            "name": "Switch {0}".format(switch.get('name')),
            "unique_id": "openmotics {0} switch".format(switch.get('name').lower()),
            "state_topic": self._config.get('output_status_topic_format').format(id=output_id),
            "command_topic": self._config.get('output_command_topic').replace('+', str(output_id)),
            "retain": self._config.get('output_status_retain'),
            "value_template": "{{ value_json.value }}",
            "state_on": "100",
            "state_off": "0",
            "payload_on": "100",
            "payload_off": "0",
            "payload_available": "100",
            "payload_not_available": "0",
            "device": {
                "name": "Switch {0}".format(switch.get('name')),
                "identifiers": "Switch {0}".format(switch.get('name')),
                "manufacturer": "OpenMotics",
                "model": ("Relay module" if switch['hardware_type'] == HardwareType.PHYSICAL else "Virtual relay module"),
                "suggested_area": room
            },
            "device_class": HomeAssistant.output_ha_types.get(switch.get('type'))
        }

    def _dump_valve_discovery_json(self, output_id, valve):
        room = ''

        if valve.get('room_id') in self._rooms:
            room = self._rooms[valve.get('room_id')]['name']

        return {
            "name": valve.get('name'),
            "icon": "mdi:valve-closed",
            "unique_id": "openmotics {0} valve".format(valve.get('name').lower()),
            "state_topic": self._config.get('output_status_topic_format').format(id=output_id),
            "command_topic": self._config.get('output_command_topic').replace('+', str(output_id)),
            "retain": self._config.get('output_status_retain'),
            "value_template": "{{ value_json.value }}",
            "state_on": "100",
            "state_off": "0",
            "payload_on": "100",
            "payload_off": "0",
            "payload_available": "100",
            "payload_not_available": "0",
            "device": {
                "name": "Valve {0}".format(valve.get('name')),
                "identifiers": "Valve {0}".format(valve.get('name')),
                "manufacturer": "OpenMotics",
                "model": ("Relay module" if valve['hardware_type'] == HardwareType.PHYSICAL else "Virtual relay module"),
                "suggested_area": room
            },
            "device_class": HomeAssistant.output_ha_types.get(valve.get('type'))
        }

    def _dump_ventilation_discovery_json(self, output_id, ventilation):
        room = ''

        if ventilation.get('room_id') in self._rooms:
            room = self._rooms[ventilation.get('room_id')]['name']

        return {
            "name": ventilation.get('name'),
            "icon": "mdi:fan",
            "unique_id": "openmotics {0} ventilation".format(ventilation.get('name').lower()),
            "state_topic": self._config.get('output_status_topic_format').format(id=output_id),
            "command_topic": self._config.get('output_command_topic').replace('+', str(output_id)),
            "retain": self._config.get('output_status_retain'),
            "state_value_template": "{{ value_json.value }}",
            "payload_on": "100",
            "payload_off": "0",
            "payload_available": "100",
            "payload_not_available": "0",
            "device": {
                "name": "Ventilation {0}".format(ventilation.get('name')),
                "identifiers": "Ventilation {0}".format(ventilation.get('name')),
                "manufacturer": "OpenMotics",
                "model": ("Relay module" if ventilation['hardware_type'] == HardwareType.PHYSICAL else "Virtual relay module"),
                "suggested_area": room
            },
            "device_class": HomeAssistant.output_ha_types.get(ventilation.get('type'))
        }

    def _dump_shutter_discovery_json(self, shutter_id, shutter):
        room = ''

        if shutter.get('room_id') in self._rooms:
            room = self._rooms[shutter.get('room_id')]['name']

        return {
            "name": shutter.get('name'),
            "unique_id": "openmotics {0} shutter".format(shutter.get('name').lower()),
            "set_position_topic": self._config.get('shutter_position_command_topic').replace('+', str(shutter_id)),
            "position_topic": self._config.get('shutter_position_topic_format').format(id=shutter_id),
            "command_topic": self._config.get('shutter_command_topic').replace('+', str(shutter_id)),
            "retain": self._config.get('shutter_status_retain'),
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

    def _dump_energy_discovery_json(self, module_id, sensor_id, sensor):
        return {
            "name": "OpenMotics {0} Energy".format(sensor.get('name')),
            "unique_id": "openmotics {0} {1} energy".format(module_id, sensor.get('name').lower()),
            "state_topic": self._config.get('energy_status_topic_format').format(module_id=module_id, sensor_id=sensor_id),
            "value_template": "{{ value_json.night / 1000 | float | round(2) }}",
            "unit_of_measurement": "kWh",
            "retain": self._config.get('energy_status_retain'),
            "device": {
                "name": "Energy {0}".format(sensor.get('name')),
                "identifiers": "Energy {0}".format(sensor.get('name')),
                "manufacturer": "OpenMotics",
                "model": "Energy module"
            },
            "device_class": "energy",
            "state_class": "total_increasing"
        }

    def _dump_power_discovery_json(self, module_id, sensor_id, sensor):
        return {
            "name": sensor.get('name'),
            "unique_id": "openmotics {0} {1} power".format(module_id, sensor.get('name').lower()),
            "state_topic": self._config.get('power_status_topic_format').format(module_id=module_id, sensor_id=sensor_id),
            "value_template": "{{ value_json.power | float | round(2) }}",
            "unit_of_measurement": "W",
            "retain": self._config.get('power_status_retain'),
            "device": {
                "name": "Energy {0}".format(sensor.get('name')),
                "identifiers": "Energy {0}".format(sensor.get('name')),
                "manufacturer": "OpenMotics",
                "model": "Energy module"
            },
            "device_class": "power",
            "state_class": "measurement"
        }

    def _dump_power_voltage_discovery_json(self, module_id, sensor_id, sensor):
        return {
            "name": "OpenMotics {0} Voltage".format(sensor.get('name')),
            "unique_id": "openmotics {0} {1} voltage".format(module_id, sensor.get('name').lower()),
            "state_topic": self._config.get('power_status_topic_format').format(module_id=module_id, sensor_id=sensor_id),
            "value_template": "{{ value_json.voltage | float | round(2) }}",
            "unit_of_measurement": "V",
            "retain": self._config.get('power_status_retain'),
            "device": {
                "name": "Energy {0}".format(sensor.get('name')),
                "identifiers": "Energy {0}".format(sensor.get('name')),
                "manufacturer": "OpenMotics",
                "model": "Energy module"
            },
            "device_class": "voltage",
            "state_class": "total_increasing"
        }

    def _dump_power_current_discovery_json(self, module_id, sensor_id, sensor):
        return {
            "name": "OpenMotics {0} Current".format(sensor.get('name')),
            "unique_id": "openmotics {0} {1} current".format(module_id, sensor.get('name').lower()),
            "state_topic": self._config.get('power_status_topic_format').format(module_id=module_id, sensor_id=sensor_id),
            "value_template": "{{ value_json.current | float | round(3) }}",
            "unit_of_measurement": "A",
            "retain": self._config.get('power_status_retain'),
            "device": {
                "name": "Energy {0}".format(sensor.get('name')),
                "identifiers": "Energy {0}".format(sensor.get('name')),
                "manufacturer": "OpenMotics",
                "model": "Energy module"
            },
            "device_class": "current",
            "state_class": "total_increasing"
        }

    def _dump_power_frequency_discovery_json(self, module_id, sensor_id, sensor):
        return {
            "name": "OpenMotics {0} Frequency".format(sensor.get('name')),
            "unique_id": "openmotics {0} {1} frequency".format(module_id, sensor.get('name').lower()),
            "state_topic": self._config.get('power_status_topic_format').format(module_id=module_id, sensor_id=sensor_id),
            "value_template": "{{ value_json.frequency | float | round(2) }}",
            "unit_of_measurement": "Hz",
            "retain": self._config.get('power_status_retain'),
            "device": {
                "name": "Energy {0}".format(sensor.get('name')),
                "identifiers": "Energy {0}".format(sensor.get('name')),
                "manufacturer": "OpenMotics",
                "model": "Energy module"
            },
            "device_class": "frequency",
            "state_class": "total_increasing"
        }

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
            "retain": self._config.get('sensor_status_retain'),
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

    def _send(self, topic, data, qos, retain):
        try:
            self._client.publish(topic, payload=json.dumps(data), qos=qos, retain=retain)
        except Exception as ex:
            self._logger('Error sending data to topic {0}'.format(topic), True)