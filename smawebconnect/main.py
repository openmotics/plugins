# Copyright (C) 2023 OpenMotics BV
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either versio 3 of the
# License, or (at your option) any later versio.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import os.path
import time
import requests
import json
import logging
from collections import deque
from typing import List
from plugins.base import om_expose, OMPluginBase, PluginConfigChecker, background_task, om_metric_data
from .lib.sma import SMADeviceOverIP, SMADeviceDummy
from .lib.constants import FieldMappingInstance

logger = logging.getLogger(__name__)

this_dir = os.path.dirname(os.path.realpath(__file__))


class SMAWebConnect(OMPluginBase):
    """
    Reads out an SMA inverter sensors using WebConnect protocol
    """

    name = 'SMAWebConnect'
    version = '1.0.5'
    interfaces = [('config', '1.0'), ('metrics', '1.0')]
    default_config = {}
    config_description = [{
        "name": "sample_rate",
        "type": "enum",
        "description": "How frequent (every x seconds) to fetch the sensor data",
        "choices": ["60", "900", "1800", "3600"]
        },
        {
            "name": "log_level",
            "type": "enum",
            "description": "Log verbosity for debugging (default: INFO)",
            "choices": ["INFO", "WARNING", "ERROR", "DEBUG"]
        },
        {'name': 'devices',
         'type': 'section',
         'description': 'List of all SMA devices.',
         'repeat': True,
         'min': 1,
         'content': [{'name': 'sma_inverter_ip',
                      'type': 'str',
                      'description': 'IP or hostname of the SMA inverter including the scheme (e.g. http:// or https://).'},
                     {'name': 'password',
                      'type': 'str',
                      'description': 'The password of the `User` account'}]
         }]
    metric_definitions = []

    def __init__(self, webinterface, connector):
        super(SMAWebConnect, self).__init__(webinterface=webinterface, connector=connector)
        logger.info(f'Starting {self.name} plugin (v{self.version})...')
        self._config = self.read_config(SMAWebConnect.default_config)
        self._config_checker = PluginConfigChecker(self.config_description)
        self._metrics_queue = deque()
        self._enabled = False
        self._sample_rate = 30
        self._sma_devices = {}
        self._sensor_dtos = {}
        self._measurement_counter_dtos = {}
        self._read_config()
        self._disable_ssl_warnings()  # the SMA devices are using self-signed certificates, disable warnings
        logger.info(f"Started {self.name} plugin")

    def _read_config(self):
        self._enabled = False
        self._log_level = self._config.get('log_level', 'INFO')
        logger.setLevel(self._log_level)
        self._sample_rate = int(self._config.get('sample_rate', 30))
        # self._sma_devices = [SMADevice(entry['sma_inverter_ip'], entry['password']) for entry in self._config.get('devices', [])]

        # A bit of a hidden feature:
        # When providing the ip as the string 'dummy' the password field will contain the dummy api response file
        # The dummy response files are located in the 'dummy-api-responses folder
        self._sma_devices = []
        for device_entry in self._config.get('devices', []):
            device_ip = device_entry['sma_inverter_ip']
            device_password = device_entry['password']
            if device_ip != 'dummy':
                self._sma_devices.append(SMADeviceOverIP(device_ip, device_password))
            else:
                try:
                    with open('{}/dummy-api-responses/{}'.format(this_dir, device_password)) as api_response_file:
                        file_content = '\n'.join(api_response_file.readlines())
                        api_response = json.loads(file_content)
                except Exception as ex:
                    logger.error(f"Could not load the dummy api response file {device_password}, {ex}")
                    continue
                self._sma_devices.append(SMADeviceDummy(api_response))
        self._enabled = len(self._sma_devices) > 0 and self._sample_rate > 30
        logger.info(f"{self.name} is {'enabled' if self._enabled else 'disabled'}")


    @background_task
    def run(self):
        while True:
            if not self._enabled:
                time.sleep(5)
                continue
            for sma_device in self._sma_devices:
                try:
                    mappings = sma_device.get_all_mappings()
                    self._populate_mappings(sma_device.serial, mappings)
                except Exception as ex:
                    logger.exception(f'Could not read from {sma_device}')
            time.sleep(self._sample_rate)

    def _populate_mappings(self, meter_serial: str, mappings: List[FieldMappingInstance]):
        for mapping in mappings:

            # explicitly use the same external_id value for both sensor and counter
            external_id = f'smawebconnect_{mapping.get_external_id()}'

            # sensor population
            if mapping.sensor_key is not None and mapping.sensor_mapping is not None:
                logger.debug(f"Processing mapping: Sensor: {mapping.sensor_mapping.name}; value = {mapping.sensor_mapping.value}")
                if external_id not in self._sensor_dtos and mapping.sensor_mapping.value is not None:
                    try:
                        # Register the sensor on the gateway
                        name = f'{mapping.sensor_mapping.description} (SMA {meter_serial} - SENSOR {mapping.sensor_key})'
                        sensor_dto = self.connector.sensor.register(external_id=external_id,
                                                                    name=name,
                                                                    physical_quantity=mapping.sensor_mapping.physical_quantity,
                                                                    unit=mapping.sensor_mapping.unit)
                        logger.info('Registered sensor %s' % sensor_dto)
                        self._sensor_dtos[external_id] = sensor_dto
                    except Exception:
                        logger.exception('Error registering sensor %s' % mapping.sensor_mapping)
                try:
                    sensor_dto = self._sensor_dtos.get(external_id)
                    # only update sensor value if the sensor is known on the gateway
                    if sensor_dto is not None:
                        value = round(mapping.sensor_mapping.value, 2) if mapping.sensor_mapping.value is not None else None
                        self.connector.sensor.report_status(sensor=sensor_dto,
                                                            value=value)
                except Exception:
                    logger.exception('Error while reporting sensor state')
            # measurement counter population
            if mapping.counter_key is not None and mapping.counter_mapping is not None:
                logger.debug(f"Processing mapping: Counter: {mapping.counter_mapping.name}; value = {mapping.counter_mapping.value}")
                if external_id not in self._measurement_counter_dtos and mapping.counter_mapping.value is not None:
                    try:
                        # Register the counter on the gateway
                        name = f'{mapping.counter_mapping.description} (SMA {meter_serial} - COUNTER {mapping.counter_key})'
                        counter_dto = self.connector.measurement_counter.register(
                            external_id=external_id,
                            type=mapping.counter_mapping.type.value,
                            category=mapping.counter_mapping.category.value,
                            name=name,
                            has_realtime=(mapping.sensor_mapping is not None)
                        )
                        logger.info('Registered counter %s' % counter_dto)
                        self._measurement_counter_dtos[external_id] = counter_dto
                    except Exception:
                        logger.exception('Error registering counter %s' % mapping.counter_mapping)
                try:
                    counter_dto = self._measurement_counter_dtos.get(external_id)
                    # only update counter value if the sensor is known on the gateway
                    if counter_dto is not None:
                        value = round(mapping.counter_mapping.value, 2) if mapping.counter_mapping.value is not None else None
                        self.connector.measurement_counter.report_counter_state(
                            measurement_counter=counter_dto,
                            total_consumed=value if not mapping.counter_mapping.is_injection else 0,
                            total_injected=value if mapping.counter_mapping.is_injection else 0,
                        )
                except Exception:
                    logger.exception('Error while reporting sensor state')

    @om_expose
    def get_config_description(self):
        return json.dumps(self.config_description)

    @om_expose
    def get_config(self):
        return json.dumps(self._config)

    @om_expose
    def set_config(self, config):
        config = json.loads(config)
        for key in config:
            if isinstance(config[key], str):
                config[key] = str(config[key])
        self._config_checker.check_config(config)
        self.write_config(config)
        self._config = config
        self._read_config()
        return json.dumps({'success': True})

    def _disable_ssl_warnings(self):
        # Disable HTTPS warnings becasue of self-signed HTTPS certificate on the SMA inverter
        from requests.packages.urllib3.exceptions import InsecureRequestWarning
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
