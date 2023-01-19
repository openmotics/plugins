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

import time
import requests
import json
import logging
from collections import deque
from typing import List
from plugins.base import om_expose, OMPluginBase, PluginConfigChecker, background_task, om_metric_data
from .lib.sma import SMADevice, Sensor

logger = logging.getLogger(__name__)


class SMASensors(OMPluginBase):
    """
    Reads out an SMA inverter sensors using WebConnect protocol
    """

    name = 'SMASensors'
    version = '1.0.0'
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
        super(SMASensors, self).__init__(webinterface=webinterface, connector=connector)
        logger.info(f'Starting {self.name} plugin...')
        self._config = self.read_config(SMASensors.default_config)
        self._config_checker = PluginConfigChecker(self.config_description)
        self._metrics_queue = deque()
        self._enabled = False
        self._sample_rate = 30
        self._sma_devices = {}
        self._sensor_dtos = {}
        self._read_config()
        self._disable_ssl_warnings()  # the SMA devices are using self-signed certificates, disable warnings
        logger.info(f"Started {self.name} plugin")

    def _read_config(self):
        self._enabled = False
        self._log_level = self._config.get('log_level', 'INFO')
        logger.setLevel(self._log_level)
        self._sample_rate = int(self._config.get('sample_rate', 30))
        self._sma_devices = [SMADevice(entry['sma_inverter_ip'], entry['password']) for entry in self._config.get('devices', [])]
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
                    sensors = sma_device.get_sensors()
                    self._populate_sensors(sensors)
                except Exception as ex:
                    logger.exception(f'Could not read from {sma_device}')
            time.sleep(self._sample_rate)

    def _populate_sensors(self, sensors: List[Sensor]):
        for sensor in sensors:
            external_id = f'smasensor_{sensor.serial}_{sensor.name}'
            if external_id not in self._sensor_dtos:
                try:
                    # Register the sensor on the gateway
                    name = f'SMA {sensor.description}'
                    sensor_dto = self.connector.sensor.register(external_id=external_id,
                                                                name=name,
                                                                physical_quantity=sensor.physical_quantity,
                                                                unit=sensor.unit)
                    logger.info('Registered %s' % sensor)
                    self._sensor_dtos[external_id] = sensor_dto
                except Exception:
                    logger.exception('Error registering sensor %s' % sensor)
            try:
                sensor_dto = self._sensor_dtos[external_id]
                value = round(sensor.value, 2) if sensor.value is not None else None
                self.connector.sensor.report_state(sensor=sensor_dto,
                                                   value=value)
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
