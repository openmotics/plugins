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

import time
import requests
import simplejson as json
from plugins.base import om_expose, OMPluginBase, PluginConfigChecker, background_task, om_metric_data
from collections import deque


class SMAWebConnect(OMPluginBase):
    """
    Reads out an SMA inverter using WebConnect
    """

    name = 'SMAWebConnect'
    version = '0.0.26'
    interfaces = [('config', '1.0'), ('metrics', '1.0')]

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
                                        'description': 'The password of the `User` account'}]}]

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
                                       for entry in FIELD_MAPPING.itervalues()]}]

    def __init__(self, webinterface, logger):
        super(SMAWebConnect, self).__init__(webinterface, logger)
        self.logger('Starting SMAWebConnect plugin...')
        self._config = self.read_config(SMAWebConnect.default_config)
        self._config_checker = PluginConfigChecker(SMAWebConnect.config_description)
        self._metrics_queue = deque()
        self._enabled = False
        self._sample_rate = 30
        self._sma_devices = {}
        self._sma_sid = {}
        self._read_config()

        # Disable HTTPS warnings becasue of self-signed HTTPS certificate on the SMA inverter
        from requests.packages.urllib3.exceptions import InsecureRequestWarning
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

        self.logger("Started SMAWebConnect plugin")

    def _read_config(self):
        self._enabled = False
        self._sample_rate = int(self._config.get('sample_rate', 30))
        self._sma_devices = self._config.get('devices', [])
        self._debug = bool(self._config.get('debug', False))

        self._enabled = len(self._sma_devices) > 0 and self._sample_rate > 5
        self.logger('SMAWebConnect is {0}'.format('enabled' if self._enabled else 'disabled'))

    def _log_debug(self, message):
        if self._debug:
            self.logger(message)

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
                    self.logger('Could not read SMA device values: {0}'.format(ex))
            time.sleep(self._sample_rate)

    def _read_data(self, sma_device):
        metrics_values = {}
        ip = sma_device['sma_inverter_ip']
        while True:
            sid = self._sma_sid.get(ip, '')
            endpoint = '{0}/dyn/getValues.json?sid={1}'.format(ip, sid)
            response = requests.post(endpoint,
                                     json={'destDev': [], 'keys': SMAWebConnect.FIELD_MAPPING.keys()},
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
        self._log_debug('Read values:')
        for key, info in SMAWebConnect.FIELD_MAPPING.iteritems():
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
            if key not in SMAWebConnect.FIELD_MAPPING.keys():
                self._log_debug('* Unknown key {0}: {1}'.format(key, data[key]))
        offline = 'frequency' not in metrics_values or metrics_values['frequency'] is None
        metrics_values['online'] = not offline
        self._enqueue_metrics(serial, metrics_values)

    def _extract_values(self, key, values, factor):
        if len(values) != 1 or '1' not in values:
            self.logger('* Unexpected structure for {0}: {1}'.format(key, values))
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
            self.logger('* Unexpected structure for {0}: {1}'.format(key, value_container))
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
            self.logger('Got unexpected error while enqueueing metrics: {0}'.format(ex))

    @om_metric_data(interval=15)
    def collect_metrics(self):
        try:
            while True:
                yield self._metrics_queue.pop()
        except IndexError:
            pass

    @om_expose
    def get_config_description(self):
        return json.dumps(SMAWebConnect.config_description)

    @om_expose
    def get_config(self):
        return json.dumps(self._config)

    @om_expose
    def set_config(self, config):
        config = json.loads(config)
        for key in config:
            if isinstance(config[key], basestring):
                config[key] = str(config[key])
        self._config_checker.check_config(config)
        self.write_config(config)
        self._config = config
        self._read_config()
        return json.dumps({'success': True})
