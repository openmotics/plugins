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

import six
import requests
import simplejson as json
import time
from socket import *
from threading import Thread
from plugins.base import om_expose, output_status, OMPluginBase, PluginConfigChecker, background_task, om_metric_data
from .api_handler import ApiHandler
from .healtbox3 import HealthBox3Manager, HealthBox3Driver

class HealthboxPlugin(OMPluginBase):
    """
    A Healthbox 3 plugin, for reading and controlling your Renson Healthbox 3
    """

    name = 'Healthbox3'
    version = '1.0.7'
    interfaces = [('config', '1.0'),
                  ('metrics', '1.0')]

    config_descr = [
        {'name': 'update_delay', 'type': 'int', 'description': 'The time to wait in seconds between polling statements for syncing back with the device'}
    ]
    default_config = {'update_delay': 30}

    def __init__(self, webinterface, logger):
        super(HealthboxPlugin, self).__init__(webinterface, logger)

        self.__config = self.read_config(HealthboxPlugin.default_config)
        self.__config_checker = PluginConfigChecker(HealthboxPlugin.config_descr)
        self._enabled = True

        self.api_handler = ApiHandler(self.logger)
        self.discovered_devices = {}  # dict of all the Healthbox3 drivers mapped with register key as key
        self.serial_key_to_gateway_id = {}  # mapping of register key to gateway id (for api calls)

        self.logger("Started Healthbox 3 plugin")

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
                {
                    'sensor_id'        :'roomID - indoor air quality[roomID]_HealthBox 3[Healthbox3] - co2',
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
            self.logger("Could not set new config, config check failed: {}".format(ex))
            return json.dumps({'success': False})

        self.__config_checker.check_config(config)
        self.write_config(config)
        self.__config = config
        self.logger("Succesfully saved new config")

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
                self.logger('Found Healthbox3 device @ ip: {} with serial key: {}'.format(ip, serial_key))
                self.register_ventilation_config(serial_key)
            except Exception as ex:
                self.logger("Discovered device @ {}, but could not connect to the device... {}".format(ip, ex))

    def register_ventilation_config(self, serial_key):
        # type: (str) -> None
        """ Registers a new device to the gateway """
        if serial_key not in self.discovered_devices:
            self.logger('Could not register new ventilation device, serial key is not known to the plugin')
            return
        hbd = self.discovered_devices[serial_key]
        if hbd is None:
            self.logger('Could not register new ventilation device, driver is not working properly to request data')
            return
        serial_key = hbd.get_variable('serial')
        config = {
            "name": hbd.get_variable('device name'),
            "amount_of_levels": 2,
            "device": {"type": "HealthBox3",
                       "vendor": "Renson",
                       "serial": serial_key
            }
        }
        response = self.webinterface.ventilation.register(serial_key, config)
        if not response:
            self.logger('Could not register new ventilation device, registration failed trough API')
        gateway_id = response.id
        serial_key = response.external_id
        self.serial_key_to_gateway_id[serial_key] = gateway_id
        self.logger('Successfully registered new ventilation device @ gateway id: {}'.format(gateway_id))

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

    def _register_sensor(self, serial_key, sensor_id, sensor_name, physical_quantity, unit_of_measure):
        # Registering the sensor
        external_id = str(serial_key)+ ' ' + str(sensor_id)
        name        = str(serial_key)+ ' ' + str(sensor_name)
        config = {
            'name' : name, 
        }
        response = self.webinterface.sensor.register(external_id = external_id, physical_quantity = physical_quantity, unit = unit_of_measure, config=config)
        if not response:
            return None
        return response

    def _update_sensor(self, serial_key, sensor_id, value, gateway_id):
        data = {'id': gateway_id, 'value': value}
        response = self.webinterface.sensor.set_status(sensor_id = gateway_id, value = value)
        if response is None:
            self.logger('Could not update sensor data for sensor {} for HealthBox3 with key {}'.format(sensor_id, serial_key))
            return False
        return True

    @background_task
    def _sensor_manager(self):
        self.logger("Starting to register and update sensors on the gateway")
        while not self._enabled:
            time.sleep(2)
        while self._enabled:
            # get list of all Healthbox3 devices and loop over devices
            serial_keys = self.discovered_devices.keys()
            for serial_key in serial_keys:
                hbd = self.discovered_devices[serial_key]  # type: HealthBox3Driver
                if hbd is None:
                    self.logger('Could not get Healthbox3 information, driver is not working properly to request data')
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
                    # Now we know that the sensor exists on the device, check if it is already registered on the cloud
                    gateway_id = hbd.get_gateway_id(sensor['sensor_id'])
                    if not gateway_id:
                        # Register the sensor on the cloud
                        response = self._register_sensor(serial_key, sensor['sensor_id'], sensor['sensor_name'], sensor['physical_quantity'], sensor['unit'])
                        if response == None:
                            self.logger('Failed to register sensor in gateway with sensor_id {} and serial_key {}'.format(sensor['sensor_id'], serial_key))
                            continue
                        # save the gateway_id on the gateway
                        hbd.set_gateway_id(sensor['sensor_id'], response.id)
                        gateway_id = hbd.get_gateway_id(sensor['sensor_id'])
                    # get sensor data
                    sensor_data = hbd.get_variable(sensor['sensor_id'])
                    # update sensor data of known sensor in EDD
                    self._update_sensor(serial_key, sensor['sensor_id'], sensor_data, gateway_id)
            time.sleep(30)
            # test

