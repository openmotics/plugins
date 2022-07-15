"""
Get sensor values from modbus
"""

import six
import sys
import time
import struct
import simplejson as json
from plugins.base import om_expose, OMPluginBase, PluginConfigChecker, background_task
import logging

logger = logging.getLogger(__name__)


class ModbusTCPSensor(OMPluginBase):
    """
    Get sensor values form modbus
    """

    name = 'modbusTCPSensor'
    version = '1.0.19'
    interfaces = [('config', '1.0')]

    config_description = [{'name': 'modbus_server_ip',
                           'type': 'str',
                           'description': 'IP or hostname of the ModBus server.'},
                          {'name': 'modbus_port',
                           'type': 'int',
                           'description': 'Port of the ModBus server. Default: 502'},
                          {'name': 'debug',
                           'type': 'int',
                           'description': 'Turn on debugging (0 = off, 1 = on)'},
                          {'name': 'sample_rate',
                           'type': 'int',
                           'description': 'How frequent (every x seconds) to fetch the sensor data, Default: 60'},
                          {'name': 'sensors',
                           'type': 'section',
                           'description': 'OM sensor ID (e.g. 4), a sensor type and a Modbus Address',
                           'repeat': True,
                           'min': 0,
                           'content': [{'name': 'sensor_id', 'type': 'int'},
                                       {'name': 'sensor_type', 'type': 'enum', 'choices': ['temperature',
                                                                                           'humidity',
                                                                                           'brightness',
                                                                                           'validation_bit']},
                                       {'name': 'modbus_address', 'type': 'int'},
                                       {'name': 'modbus_register_length', 'type': 'int'}]},
                          {'name': 'bits',
                           'type': 'section',
                           'description': 'OM validation bit ID (e.g. 4), and a Modbus Coil Address',
                           'repeat': True,
                           'min': 0,
                           'content': [{'name': 'validation_bit_id', 'type': 'int'},
                                       {'name': 'modbus_coil_address', 'type': 'int'}]}]

    default_config = {'modbus_port': 502, 'sample_rate': 60}

    def __init__(self, webinterface, connector):
        super(ModbusTCPSensor, self).__init__(webinterface=webinterface,
                                    connector=connector)
        logger.info('Starting ModbusTCPSensor plugin...')

        self._config = self.read_config(ModbusTCPSensor.default_config)
        self._config_checker = PluginConfigChecker(ModbusTCPSensor.config_description)

        py_modbus_tcp_egg = '/opt/openmotics/python/plugins/modbusTCPSensor/pyModbusTCP-0.1.7-py2.7.egg'
        if py_modbus_tcp_egg not in sys.path:
            sys.path.insert(0, py_modbus_tcp_egg)

        self._client = None
        self._samples = []
        self._save_times = {}
        self._read_config()

        logger.info("Started ModbusTCPSensor plugin")

    def _read_config(self):
        self._ip = self._config.get('modbus_server_ip')
        self._port = self._config.get('modbus_port', ModbusTCPSensor.default_config['modbus_port'])
        self._debug = self._config.get('debug', 0) == 1
        self._sample_rate = self._config.get('sample_rate', ModbusTCPSensor.default_config['sample_rate'])
        self._sensors = []
        # Load Sensors
        for sensor in self._config.get('sensors', []):
            if 0 <= sensor['sensor_id'] < 32:
                self._sensors.append(sensor)
        # Load Validation bits
        self._validation_bits = []
        for validation_bit in self._config.get('bits', []):
            if 0 <= validation_bit['validation_bit_id'] < 256:
                self._validation_bits.append(validation_bit)
        self._enabled = len(self._sensors) > 0

        try:
            from pyModbusTCP.client import ModbusClient
            self._client = ModbusClient(self._ip, self._port, auto_open=True, auto_close=True)
            self._client.open()
            self._enabled = self._enabled & True
        except Exception as ex:
            logger.exception('Error connecting to Modbus server: {0}'.format(ex))

        logger.info('ModbusTCPSensor is {0}'.format('enabled' if self._enabled else 'disabled'))

    @background_task
    def run(self):
        while True:
            try:
                if not self._enabled or self._client is None:
                    time.sleep(5)
                    continue
                # Process all configured sensors
                self.process_sensors()
                # Process all validation bits
                self.process_validation_bits()

                time.sleep(self._sample_rate)
            except Exception as ex:
                logger.exception('Could not process sensor values: {0}'.format(ex))
                time.sleep(15)

    def clamp_sensor(self, value, sensor_type):
        clamping = {'temperature': [-32, 95.5, 1],
                    'humidity': [0, 100, 1],
                    'brightness': [0, 100, 0]}
        return round(max(clamping[sensor_type][0], min(value, clamping[sensor_type][1])), clamping[sensor_type][2])

    def process_sensors(self):
        om_sensors = {}
        for sensor in self._sensors:
            registers = self._client.read_holding_registers(sensor['modbus_address'],
                                                            sensor['modbus_register_length'])
            if registers is None:
                continue
                
            sensor_value = struct.unpack('>f', struct.pack('BBBB',
                                                           registers[1] >> 8, registers[1] & 255,
                                                           registers[0] >> 8, registers[0] & 255))[0]
            if not om_sensors.get(sensor['sensor_id']):
                om_sensors[sensor['sensor_id']] = {'temperature': None, 'humidity': None, 'brightness': None}

            sensor_value = self.clamp_sensor(sensor_value, sensor['sensor_type'])

            om_sensors[sensor['sensor_id']][sensor['sensor_type']] = sensor_value
        if self._debug == 1:
            logger.debug('The sensors values are: {0}'.format(om_sensors))

        for sensor_id, values in om_sensors.iteritems():
            result = json.loads(self.webinterface.set_virtual_sensor(sensor_id, **values))
            if result['success'] is False:
                logger.error('Error when updating virtual sensor {0}: {1}'.format(sensor_id, result['msg']))

    def process_validation_bits(self):
        for validation_bit in self._validation_bits:
            bit = self._client.read_coils(validation_bit['modbus_coil_address'], 1)

            if bit is None or len(bit) != 1:
                if self._debug == 1:
                    logger.debug('Failed to read bit {0}, bit is {1}'.format(validation_bit['validation_bit_id'], bit))
                continue
            result = json.loads(self.webinterface.do_basic_action(None,
                                                                  237 if bit[0] else 238,
                                                                  validation_bit['validation_bit_id']))
            if result['success'] is False:
                logger.error('Failed to set bit {0} to {1}'.format(validation_bit['validation_bit_id'], 1 if bit[0] else 0))
            else:
                if self._debug == 1:
                    logger.debug('Successfully set bit {0} to {1}'.format(validation_bit['validation_bit_id'], 1 if bit[0] else 0))

    @om_expose
    def get_config_description(self):
        return json.dumps(ModbusTCPSensor.config_description)

    @om_expose
    def get_config(self):
        return json.dumps(self._config)

    @om_expose
    def set_config(self, config):
        config = json.loads(config)
        for key in config:
            if isinstance(config[key], six.string_types):
                config[key] = str(config[key])
        self._config_checker.check_config(config)
        self.write_config(config)
        self._config = config
        self._read_config()
        return json.dumps({'success': True})
