"""
A Healthbox 3 plugin, for reading and controlling your Renson Healthbox 3
"""
"""
structuur:

3 threads:
    device discovery
    device data pulling
    cloud data syncing

local caching:
    dict with as key the reg_key of the device and value? (dict voor de variabele maar ook object voor status etc?)
"""

import simplejson as json
import time
import logging
from plugins.base import om_expose, output_status, OMPluginBase, PluginConfigChecker, background_task, om_metric_data
from .api_handler import ApiHandler
from .healtbox3 import HealthBox3Manager, HealthBox3Driver

logger = logging.getLogger(__name__)


class HealthboxPlugin(OMPluginBase):
    """
    A Healthbox 3 plugin, for reading and controlling your Renson Healthbox 3
    """

    name = 'Healthbox3'
    version = '1.1.0'
    interfaces = [('config', '1.0'),
                  ('metrics', '1.0')]

    config_descr = [
        {'name': 'update_delay', 'type': 'int', 'description': 'The time to wait in seconds between polling statements for syncing back with the device'}
    ]
    default_config = {'update_delay': 30}

    def __init__(self, webinterface, connector):
        super(HealthboxPlugin, self).__init__(webinterface=webinterface,
                                              connector=connector)

        self.__config = self.read_config(HealthboxPlugin.default_config)
        self.__config_checker = PluginConfigChecker(HealthboxPlugin.config_descr)
        self._enabled = True

        self.api_handler = ApiHandler()
        self.discovered_devices = {}  # dict of all the Healthbox3 drivers mapped with register key as key

        logger.info("Started Healthbox 3 plugin")

        self.healtbox_manager = HealthBox3Manager()
        self.healtbox_manager.set_discovery_callback(self.discover_callback)
        self.healtbox_manager.start_discovery()

        # roomID is used as a placeholder for the room number, this is replaced through _define_sensors_with_rooms function
        self.sensorsGeneral =   [
                {
                    'sensor_id'        :'roomID - indoor temperature[roomID]_HealthBox 3[Healthbox3] - temperature',
                    'sensor_name'      :'Temperature Room roomID',
                    'physical_quantity':'temperature',
                    'unit'             :'celcius',
                },
                {
                    'sensor_id'        :'roomID - indoor relative humidity[roomID]_HealthBox 3[Healthbox3] - humidity',
                    'sensor_name'      :'Humidity Room roomID',
                    'physical_quantity':'humidity',
                    'unit'             :'percent',
                },
                # deprecated way of co2
                # {
                #     'sensor_id'        :'roomID - indoor air quality[roomID]_HealthBox 3[Healthbox3] - co2',
                #     'sensor_name'      :'CO2 Room roomID',
                #     'physical_quantity':'co2',
                #     'unit'             :'parts_per_million',
                # },
                {
                    'sensor_id'        :'roomID - indoor CO2[roomID]_HealthBox 3[Healthbox3] - concentration',
                    'sensor_name'      :'CO2 Room roomID',
                    'physical_quantity':'co2',
                    'unit'             :'parts_per_million',
                },
                {
                    'sensor_id'        :'roomID - indoor volatile organic compounds[roomID]_HealthBox 3[Healthbox3] - concentration',
                    'sensor_name'      :'VOC Room roomID',
                    'physical_quantity':'voc',
                    'unit'             :'parts_per_million',
                },

            ]

    @om_expose
    def get_config_description(self):
        return json.dumps(HealthboxPlugin.config_descr)

    @om_expose
    def get_config(self):
        return json.dumps(self.__config)

    @om_expose
    def set_config(self, config):
        config = json.loads(config)
        try:
            self._check_config(config)
        except Exception as ex:
            logger.error("Could not set new config, config check failed: {}".format(ex))
            return json.dumps({'success': False})

        self.__config_checker.check_config(config)
        self.write_config(config)
        self.__config = config
        logger.info("Succesfully saved new config")

        return json.dumps({'success': True})

    @staticmethod
    def _check_config(config):
        # check if all fields are populated
        if 'update_delay' not in config:
            raise RuntimeError('Config has no field "update_delay" (required)')

        # check all the fields if they are valid input
        delay = config['update_delay']
        try:
            delay = int(delay)
        except Exception as ex:
            raise RuntimeError('field "update_delay": ({}) is not a valid input in the provided config (not int)'.format(delay))

    @background_task
    def background_worker(self):
        while True:
            self.api_handler.do_requests()
            time.sleep(10)

    def discover_callback(self, ip):
        # type: (str) -> None
        """ callback for when a new device has been discovered """
        serial_key = self.healtbox_manager.get_serial(ip)
        if serial_key is not None:
            try:
                self.discovered_devices[serial_key] = HealthBox3Driver(ip=ip)
                logger.info('Found Healthbox3 device @ ip: {} with serial key: {}'.format(ip, serial_key))
                self.register_ventilation_config(serial_key)
            except Exception as ex:
                logger.error("Discovered device @ {}, but could not connect to the device... {}".format(ip, ex))

    def register_ventilation_config(self, serial_key):
        # type: (str) -> None
        """ Registers a new device to the gateway """
        if serial_key not in self.discovered_devices:
            logger.error('Could not register new ventilation device, serial key is not known to the plugin')
            return
        hbd = self.discovered_devices[serial_key]
        if hbd is None:
            logger.error('Could not register new ventilation device, driver is not working properly to request data')
            return
        serial_key = hbd.get_variable('serial')
        self.connector.ventilation.register(external_id=serial_key,
                                            name=hbd.get_variable('device name'),
                                            amount_of_levels=2,
                                            device_type='HealthBox3',
                                            device_vendor='Renson',
                                            device_serial=serial_key)
        logger.info('Successfully registered new ventilation device')

    def _define_sensors_with_rooms(self, rooms, sensor_list):
        # type: (list, list of dicts) -> list of dicts
        # because we do not want to boilerplate the variable names for all availe rooms, we introduce this function
        new_sensor_list = []
        # loop over all the room numbers
        for room in rooms:
            # loop over all the sensors per room
            for sensor in sensor_list:
                # add roomnumber to sensor
                new_sensor = {}
                for key, value in sensor.items():
                    new_sensor[key] = value.replace('roomID', str(room))
                new_sensor_list.append(new_sensor)
        return new_sensor_list

    @background_task
    def _sensor_manager(self):
        logger.info("Starting to register and update sensors on the gateway")
        while not self._enabled:
            time.sleep(2)
        while self._enabled:
            # get list of all Healthbox3 devices and loop over devices
            serial_keys = self.discovered_devices.keys()
            for serial_key in serial_keys:
                hbd = self.discovered_devices[serial_key]  # type: HealthBox3Driver
                if hbd is None:
                    logger.error('Could not get Healthbox3 information, driver is not working properly to request data')
                    continue
                # get list of variables available to this device
                variables = hbd.get_list_of_variables()
                # get sensors per room
                rooms = hbd.get_available_rooms()
                sensors = self._define_sensors_with_rooms(rooms, self.sensorsGeneral)
                # check if sensor in sensor list is available on the device (safety check)
                for sensor in sensors:
                    if sensor['sensor_id'] not in variables:
                        continue
                    # Now we know that the sensor exists on the device, check if it is already registered on the gateway
                    gateway_sensor = hbd.get_gateway_sensor(sensor['sensor_id'])
                    if not gateway_sensor:
                        # Register the sensor on the gateway
                        external_id = '{0} {1}'.format(serial_key, sensor['sensor_id'])
                        name = '{0} {1}'.format(serial_key, sensor['sensor_name'])
                        gateway_sensor = self.connector.sensor.register(external_id=external_id,
                                                                        physical_quantity=sensor['physical_quantity'],
                                                                        unit=sensor['unit'],
                                                                        name=name)
                        hbd.set_gateway_sensor(sensor['sensor_id'], gateway_sensor)
                    # get sensor data
                    sensor_data = hbd.get_variable(sensor['sensor_id'])
                    self.connector.sensor.report_state(sensor=gateway_sensor,
                                                       value=sensor_data)
            time.sleep(30)
            # test

