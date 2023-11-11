# Copyright (C) 2020 OpenMotics BV
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

import six
import time
import requests
import json
from plugins.base import om_expose, OMPluginBase, PluginConfigChecker, background_task, om_metric_data
from collections import deque
from threading import Thread
import logging

logger = logging.getLogger(__name__)


class SMAdndConnect(OMPluginBase):
    """
    Reads out an SMA inverter using WebConnect
    """

    name = 'SMAdndConnect'
    version = '0.0.38'
    interfaces = [('config', '1.0'), ('metrics', '1.0')]

    counter_device_types = ['gas', 'heat', 'water', 'electricity']
    counter_unit_types = ['energy', 'volume', 'power', 'flow']
    types_mapping = {'energy': 'energy', 'power': 'energy', 'volume': 'volume', 'flow': 'volume'}

    default_config = {}

    FIELD_MAPPING = {'6100_40263F00': {'name': 'grid_power',
                                       'description': 'Grid power',
                                       'unit': 'W', 'type': 'gauge',
                                       'factor': 1.0},
                     '6100_00465700': {'name': 'frequency',
                                       'description': 'Frequency',
                                       'unit': 'Hz', 'type': 'gauge',
                                       'factor': 100.0},
                     '6100_00464800': {'name': 'voltage_l1',
                                       'description': 'Voltage L1',
                                       'unit': 'V', 'type': 'gauge',
                                       'factor': 100.0},
                     '6100_00464900': {'name': 'voltage_l2',
                                       'description': 'Voltage L2',
                                       'unit': 'V', 'type': 'gauge',
                                       'factor': 100.0},
                     '6100_00464A00': {'name': 'voltage_l3',
                                       'description': 'Voltage L3',
                                       'unit': 'V', 'type': 'gauge',
                                       'factor': 100.0},
                     '6100_40465300': {'name': 'current_l1',
                                       'description': 'Current L1',
                                       'unit': 'A', 'type': 'gauge',
                                       'factor': 1000.0},
                     '6100_40465400': {'name': 'current_l2',
                                       'description': 'Current L2',
                                       'unit': 'A', 'type': 'gauge',
                                       'factor': 1000.0},
                     '6100_40465500': {'name': 'current_l3',
                                       'description': 'Current L3',
                                       'unit': 'A', 'type': 'gauge',
                                       'factor': 1000.0},
                     '6100_0046C200': {'name': 'pv_power',
                                       'description': 'PV power',
                                       'unit': 'W', 'type': 'gauge',
                                       'factor': 1.0},
                     '6380_40451F00': {'name': 'pv_voltage',
                                       'description': 'PV voltage (average of all PV channels)',
                                       'unit': 'V', 'type': 'gauge',
                                       'factor': 100.0},
                     '6380_40452100': {'name': 'pv_current',
                                       'description': 'PV current (average of all PV channels)',
                                       'unit': 'A', 'type': 'gauge',
                                       'factor': 1000.0},
                     '6400_0046C300': {'name': 'pv_gen_meter',
                                       'description': 'PV generation meter',
                                       'unit': 'Wh', 'type': 'counter',
                                       'factor': 1.0},
                     '6400_00260100': {'name': 'total_yield',
                                       'description': 'Total yield',
                                       'unit': 'Wh', 'type': 'counter',
                                       'factor': 1.0},
                     '6400_00262200': {'name': 'daily_yield',
                                       'description': 'Daily yield',
                                       'unit': 'Wh', 'type': 'counter',
                                       'factor': 1.0},
                     '6100_40463600': {'name': 'grid_power_supplied',
                                       'description': 'Grid power supplied',
                                       'unit': 'W', 'type': 'gauge',
                                       'factor': 1.0},
                     '6100_40463700': {'name': 'grid_power_absorbed',
                                       'description': 'Grid power absorbed',
                                       'unit': 'W', 'type': 'gauge',
                                       'factor': 1.0},
                     '6400_00462400': {'name': 'grid_total_yield',
                                       'description': 'Grid total yield',
                                       'unit': 'Wh', 'type': 'counter',
                                       'factor': 1.0},
                     '6400_00462500': {'name': 'grid_total_absorbed',
                                       'description': 'Grid total absorbed',
                                       'unit': 'Wh', 'type': 'counter',
                                       'factor': 1.0},
                     '6100_00543100': {'name': 'current_consumption',
                                       'description': 'Current consumption',
                                       'unit': 'W', 'type': 'gauge',
                                       'factor': 1.0},
                     '6400_00543A00': {'name': 'total_consumption',
                                       'description': 'Total consumption',
                                       'unit': 'Wh', 'type': 'counter',
                                       'factor': 1.0}}

    metric_definitions = [{'type': 'sma',
                           'tags': ['device'],
                           'metrics': [{'name': 'online',
                                        'description': 'Indicates if the SMA device is operating',
                                        'type': 'gauge', 'unit': 'Boolean'}] +
                                      [{'name': entry['name'], 'description': entry['description'],
                                        'unit': entry['unit'], 'type': entry['type']}
                                        for entry in FIELD_MAPPING.values()]}]

    def __init__(self, webinterface, connector):
        super(SMAdndConnect, self).__init__(webinterface=webinterface,
                                    connector=connector)

        logger.info('Starting SMAdndConnect plugin...')
        self.config_description = self._create_config_description()
        self._config = self.read_config(SMAdndConnect.default_config)
        self._config_checker = PluginConfigChecker(self.config_description)
        self._metrics_queue = deque()
        self._enabled = False
        self._sample_rate = 30
        self._sma_devices = {}
        self._sma_sid = {}
        self._counter_rate_to_total = {}
        self._read_config()

        # Disable HTTPS warnings becasue of self-signed HTTPS certificate on the SMA inverter
        from requests.packages.urllib3.exceptions import InsecureRequestWarning
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

        logger.info("Started SMAdndConnect plugin")

    def _create_config_description(self):
        self.pc_config = json.loads(self.webinterface.get_pulse_counter_configurations())
        pc_names = [pc_config['name'] for pc_config in self.pc_config['config'] if pc_config['name']]
        config_description = [{'name': 'sample_rate',
                               'type': 'int',
                               'description': 'How frequent (every x seconds) to fetch the sensor data, Default: 30'},
                              {'name': 'debug',
                               'type': 'bool',
                               'description': 'Indicate whether debug logging should be enabled'},
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
                                            'description': 'The password of the `User` account'},
                                           {'name': 'counter_mapping',
                                            'type': 'section',
                                            'description': 'Counter mapping',
                                            'repeat': True,
                                            'min': 0,
                                            'content': [{'name': 'name',
                                                         'type': 'enum',
                                                         'description': 'Name of the pulse counter',
                                                         'choices': [v['name'] for v in SMAdndConnect.FIELD_MAPPING.values()]},
                                                        {'name': 'pulsecounter_name',
                                                         'type': 'enum',
                                                         'description': 'Name of the counter to which the selected value needs to be mapped',
                                                         'choices': pc_names},
                                                        {'name': 'unit_type',
                                                         'type': 'enum',
                                                         'description': 'Unit type of measurement',
                                                         'choices': SMAdndConnect.counter_unit_types},
                                                        {'name': 'convert_to_counter',
                                                         'type': 'enum',
                                                         'description': 'The read value needs to be made into a counter (i.e. cumulative)',
                                                         'choices': ['NO', 'YES']},
                                                        {'name': 'multiplier',
                                                         'type': 'str',
                                                         'description': 'Multiplier for readout of values (default=1; required to ensure units of'
                                                                        'kW(h) or m3(/h) for values given to pulse counters)'},
                                                        ]}
                                           ]}
                              ]

        return config_description

    def _read_config(self):
        self._enabled = False
        self._sample_rate = int(self._config.get('sample_rate', 30))
        self._sma_devices = self._config.get('devices', [])
        self._debug = bool(self._config.get('debug', False))

        self._enabled = len(self._sma_devices) > 0 and self._sample_rate > 5
        logger.info('SMAdndConnect is {0}'.format('enabled' if self._enabled else 'disabled'))

    def _log_debug(self, message):
        if self._debug:
            logger.debug(message)

    @background_task
    def run(self):
        while True:
            if not self._enabled:
                time.sleep(5)
                continue
            for sma_device in self._sma_devices:
                try:
                    self._read_data(sma_device)
                except Exception as ex:
                    logger.exception('Could not read SMA device values')
            time.sleep(self._sample_rate)

    def _read_data(self, sma_device):
        metrics_values = {}
        ip = sma_device['sma_inverter_ip']
        while True:
            sid = self._sma_sid.get(ip, '')
            endpoint = '{0}/dyn/getValues.json?sid={1}'.format(ip, sid)
            response = requests.post(endpoint,
                                     json={'destDev': [], 'keys': SMAdndConnect.FIELD_MAPPING.keys()},
                                     timeout=10,
                                     verify=False).json()
            if response.get('err') == 401:
                self._login(sma_device)
                continue
            break
        if 'result' not in response or len(response['result']) != 1:
            raise RuntimeError('Unexpected response: {0}'.format(response))
        serial = response['result'].keys()[0]
        data = response['result'][serial]
        if data is None:
            raise RuntimeError('Unexpected response: {0}'.format(response))
        self._log_debug('Read values (ip: {0}, serial number: {1}):'.format(ip, serial))
        for key, info in SMAdndConnect.FIELD_MAPPING.items():
            name = info['name']
            unit = info['unit']
            if key in data:
                values = self._extract_values(key, data[key], info['factor'])
                if len(values) == 0:
                    self._log_debug('* {0}: No values'.format(name))
                elif len(values) == 1:
                    value = values[0]
                    self._log_debug('* {0}: {1}{2}'.format(name, value, unit if value is not None else ''))
                    if value is not None:
                        metrics_values[name] = value
                else:
                    self._log_debug('* {0}:'.format(name))
                    for value in values:
                        self._log_debug('** {0}{1}'.format(value, unit if value is not None else ''))
                    values = [value for value in values
                              if value is not None]
                    if len(values) == 1:
                        metrics_values[name] = values[0]
                    elif len(values) > 1:
                        metrics_values[name] = sum(values) / len(values)
            else:
                self._log_debug('* Missing key: {0}'.format(key))
        for key in data:
            if key not in SMAdndConnect.FIELD_MAPPING.keys():
                self._log_debug('* Unknown key {0}: {1}'.format(key, data[key]))
        offline = 'frequency' not in metrics_values or metrics_values['frequency'] is None
        metrics_values['online'] = not offline
        self._enqueue_metrics(serial, metrics_values)
        self._update_pulsecounter(sma_device, metrics_values)

    def _extract_values(self, key, values, factor):
        if len(values) != 1 or '1' not in values:
            logger.error('* Unexpected structure for {0}: {1}'.format(key, values))
            return []
        values = values['1']
        if len(values) == 0:
            return []
        if len(values) == 1:
            return [self._clean_value(key, values[0], factor)]
        return_data = []
        for raw_value in values:
            value = self._clean_value(key, raw_value, factor)
            if value is not None:
                return_data.append(value)
        return return_data

    def _clean_value(self, key, value_container, factor):
        if 'val' not in value_container:
            logger.error('* Unexpected structure for {0}: {1}'.format(key, value_container))
            return None
        value = value_container['val']
        if value is None:
            return None
        return float(value) / factor

    def _login(self, sma_device):
        ip = sma_device['sma_inverter_ip']
        endpoint = '{0}/dyn/login.json'.format(ip)
        response = requests.post(endpoint,
                                 json={'right': 'usr',
                                       'pass': sma_device['password']},
                                 verify=False).json()
        if 'result' in response and 'sid' in response['result']:
            self._sma_sid[ip] = response['result']['sid']
        else:
            error_code = response.get('err', 'unknown')
            if error_code == 503:
                raise RuntimeError('Maximum amount of sessions')
            raise RuntimeError('Could not login: {0}'.format(error_code))

    def _enqueue_metrics(self, device_id, values):
        try:
            now = time.time()
            self._metrics_queue.appendleft({'type': 'sma',
                                            'timestamp': now,
                                            'tags': {'device': device_id},
                                            'values': values})
        except Exception as ex:
            logger.exception('Got unexpected error while enqueueing metrics')

    @om_metric_data(interval=15)
    def collect_metrics(self):
        try:
            while True:
                yield self._metrics_queue.pop()
        except IndexError:
            pass

    def _update_pulsecounter(self, device_config, values):
        """Add the values defined in counter_mapping not only to influxdb as metrics, but also create and update
        pulse counters for them. If configured, convert the measurement into a counter, i.e. make it cumulative."""
        for mapping in device_config.get('counter_mapping', []):
            value_name = str(mapping['name'])
            unit_type = SMAdndConnect.types_mapping.get(mapping.get('unit_type'))
            current_value = values[value_name] * float(mapping.get('multiplier', 1))
            pc_name = str(mapping['pulsecounter_name'])
            self.pc_config = json.loads(self.webinterface.get_pulse_counter_configurations())
            pc_id = [pc_config['id'] for pc_config in self.pc_config['config'] if pc_config['name'] == pc_name]
            if len(pc_id) == 0 or len(pc_id) > 1:
                logger.warning("No or multiple pulsecounters found for name {0}. Skipping this pulsecounter".format(pc_name))
                continue
            pc_id = pc_id[0]

            if not self._counter_rate_to_total.get(pc_name):
                self._counter_rate_to_total[pc_name] = 0.0

            # If the measured value is a power measurement, it needs to be converted to energy.
            # Assume the value you are getting is in kW and needs to be converted to a kWh counter
            if mapping.get('unit_type') == 'power' or mapping.get('unit_type') == 'flow':
                self._log_debug('* Converting {0} to {1}...'.format(mapping.get('unit_type'), unit_type))
                current_value_amount = current_value * self._sample_rate / 3600  # convert kW or m3/h to kWh or m3
                # You need an internal counter, because a pulse counter only works with integers, while a kWh-value
                # over 1 minute is often lower than 1
                self._counter_rate_to_total[pc_name] += current_value_amount
                if self._counter_rate_to_total[pc_name] < 1.0:
                    self._log_debug('* {0} for counter {1} has not reached cumulative value of 1 yet (currently {2}) - '
                              'adding 0 to pulse counter'.format(mapping.get('unit_type'), pc_name,
                                                                 self._counter_rate_to_total[pc_name]))
                    current_value = 0
                else:
                    current_value = self._counter_rate_to_total[pc_name]
                    self._counter_rate_to_total[pc_name] = self._counter_rate_to_total[pc_name] - 1.0

            # If the measured values still need to be made cumulative
            if mapping.get('convert_to_counter', 'NO') == 'YES':
                result = json.loads(self.webinterface.get_pulse_counter_status())
                previous_value = result['counters'][pc_id] if result['counters'][pc_id] else 0
                value = int(current_value + previous_value)
            else:
                value = int(current_value)

            self._log_debug(
                '* Processing ... Setting counter {0} with name {1} to {2}'.format(pc_id, pc_name, value))
            result = json.loads(self.webinterface.set_pulse_counter_status(pulse_counter_id=pc_id, value=value))
            if result['success'] is False:
                self._log_debug('* Could not update counter value for {0} (ID {1}): {2}'.format(pc_name, pc_id,
                                                                                          result.get('msg')))

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
            if isinstance(config[key], six.string_types):
                config[key] = str(config[key])
        self._config_checker.check_config(config)
        self.write_config(config)
        self._config = config
        self._read_config()
        return json.dumps({'success': True})
