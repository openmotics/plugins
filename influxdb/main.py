"""
An InfluxDB plugin, for sending statistics to InfluxDB
"""

import time
import requests
import simplejson as json
from threading import Thread
from plugins.base import om_expose, input_status, output_status, background_task, OMPluginBase, PluginConfigChecker
from serial_utils import CommunicationTimedOutException


class InfluxDB(OMPluginBase):
    """
    An InfluxDB plugin, for sending statistics to InfluxDB
    """

    name = 'InfluxDB'
    version = '1.2.3'
    interfaces = [('config', '1.0')]

    config_description = [{'name': 'url',
                           'type': 'str',
                           'description': 'The enpoint for the InfluxDB using HTTP. E.g. http://1.2.3.4:8086'},
                          {'name': 'username',
                           'type': 'str',
                           'description': 'Optional username for InfluxDB authentication.'},
                          {'name': 'password',
                           'type': 'str',
                           'description': 'Optional password for InfluxDB authentication.'},
                          {'name': 'database',
                           'type': 'str',
                           'description': 'The InfluxDB database name to witch statistics need to be send.'},
                          {'name': 'intervals',
                           'type': 'section',
                           'description': 'Optional interval overrides.',
                           'repeat': True,
                           'min': 0,
                           'content': [{'name': 'component', 'type': 'str'},
                                       {'name': 'interval', 'type': 'int'}]},
                          {'name': 'tags',
                           'type': 'section',
                           'description': 'Additional tags which are added based on the name of a power sensor',
                           'repeat': True,
                           'min': 0,
                           'content': [{'name': 'name',
                                        'type': 'str',
                                        'description': 'name of the power input'},
                                       {'name': 'tags',
                                        'type': 'section',
                                        'repeat': True,
                                        'description': 'Key/Value pairs indicating the additional tags to be added for the selected name. Don\'t use name, type or id as key',
                                        'content': [{'name': 'tag key',
                                                     'type': 'str',
                                                     'description': 'tag key'},
                                                    {'name': 'tag value',
                                                     'type': 'str',
                                                     'description': 'tag value'}]},
                                      ]
                          }]

    default_config = {'url': '', 'database': 'openmotics'}

    def __init__(self, webinterface, logger):
        super(InfluxDB, self).__init__(webinterface, logger)
        self.logger('Starting InfluxDB plugin...')

        self._start = time.time()
        self._last_service_uptime = 0
        self._config = self.read_config(InfluxDB.default_config)
        self._config_checker = PluginConfigChecker(InfluxDB.config_description)
        self._environment = {'inputs': {},
                             'outputs': {},
                             'sensors': {},
                             'pulse_counters': {}}
        self._timings = {}

        self._load_environment_configurations()
        self._read_config()
        self._has_fibaro_power = False
        if self._enabled:
            thread = Thread(target=self._check_fibaro_power)
            thread.start()

        self.logger("Started InfluxDB plugin")

    def _read_config(self):
        self._url = self._config['url']
        self._database = self._config['database']
        intervals = self._config.get('intervals', [])
        self._intervals = {}
        for item in intervals:
            self._intervals[item['component']] = item['interval']

        tags = self._config.get('tags',[])
        self._tags = {}
        for item in tags:
            self._tags[item['name']] = {}
            for tagdef in item['tags']:
                self._tags[item['name']][tagdef['tag key']] = tagdef['tag value']

        username = self._config.get('username', '')
        password = self._config.get('password', '')
        self._auth = None if username == '' else (username, password)

        self._endpoint = '{0}/write?db={1}'.format(self._url, self._database)
        self._query_endpoint = '{0}/query?db={1}&epoch=ns'.format(self._url, self._database)
        self._headers = {'X-Requested-With': 'OpenMotics plugin: InfluxDB'}

        self._enabled = self._url != '' and self._database != ''
        self.logger('InfluxDB is {0}'.format('enabled' if self._enabled else 'disabled'))

    def _load_environment_configurations(self, interval=None):
        while True:
            start = time.time()
            # Inputs
            try:
                result = json.loads(self.webinterface.get_input_configurations(None))
                if result['success'] is False:
                    self.logger('Failed to load input configurations')
                else:
                    ids = []
                    for config in result['config']:
                        input_id = config['id']
                        ids.append(input_id)
                        config['clean_name'] = InfluxDB.clean_name(config['name'])
                        self._environment['inputs'][input_id] = config
                    for input_id in self._environment['inputs'].keys():
                        if input_id not in ids:
                            del self._environment['inputs'][input_id]
            except CommunicationTimedOutException:
                self.logger('Error while loading input configurations: CommunicationTimedOutException')
            except Exception as ex:
                self.logger('Error while loading input configurations: {0}'.format(ex))
            # Outputs
            try:
                result = json.loads(self.webinterface.get_output_configurations(None))
                if result['success'] is False:
                    self.logger('Failed to load output configurations')
                else:
                    ids = []
                    for config in result['config']:
                        if config['module_type'] not in ['o', 'O', 'd', 'D']:
                            continue
                        output_id = config['id']
                        ids.append(output_id)
                        self._environment['outputs'][output_id] = {'name': InfluxDB.clean_name(config['name']),
                                                                   'module_type': {'o': 'output',
                                                                                   'O': 'output',
                                                                                   'd': 'dimmer',
                                                                                   'D': 'dimmer'}[config['module_type']],
                                                                   'floor': config['floor'],
                                                                   'type': 'relay' if config['type'] == 0 else 'light'}
                    for output_id in self._environment['outputs'].keys():
                        if output_id not in ids:
                            del self._environment['outputs'][output_id]
            except CommunicationTimedOutException:
                self.logger('Error while loading output configurations: CommunicationTimedOutException')
            except Exception as ex:
                self.logger('Error while loading output configurations: {0}'.format(ex))
            # Sensors
            try:
                result = json.loads(self.webinterface.get_sensor_configurations(None))
                if result['success'] is False:
                    self.logger('Failed to load sensor configurations')
                else:
                    ids = []
                    for config in result['config']:
                        input_id = config['id']
                        ids.append(input_id)
                        config['clean_name'] = InfluxDB.clean_name(config['name'])
                        self._environment['sensors'][input_id] = config
                    for input_id in self._environment['sensors'].keys():
                        if input_id not in ids:
                            del self._environment['sensors'][input_id]
            except CommunicationTimedOutException:
                self.logger('Error while loading sensor configurations: CommunicationTimedOutException')
            except Exception as ex:
                self.logger('Error while loading sensor configurations: {0}'.format(ex))
            # Pulse counters
            try:
                result = json.loads(self.webinterface.get_pulse_counter_configurations(None))
                if result['success'] is False:
                    self.logger('Failed to load pulse counter configurations')
                else:
                    ids = []
                    for config in result['config']:
                        input_id = config['id']
                        ids.append(input_id)
                        config['clean_name'] = InfluxDB.clean_name(config['name'])
                        self._environment['pulse_counters'][input_id] = config
                    for input_id in self._environment['pulse_counters'].keys():
                        if input_id not in ids:
                            del self._environment['pulse_counters'][input_id]
            except CommunicationTimedOutException:
                self.logger('Error while loading pulse counter configurations: CommunicationTimedOutException')
            except Exception as ex:
                self.logger('Error while loading pulse counter configurations: {0}'.format(ex))
            if interval is None:
                return
            else:
                self._pause(start, interval, 'environment_configurations')

    def _check_fibaro_power(self):
        time.sleep(10)
        try:
            self._has_fibaro_power = self._get_fibaro_power() is not None
        except:
            time.sleep(50)
            self._has_fibaro_power = self._get_fibaro_power() is not None
        self.logger('Fibaro plugin {0}detected'.format('' if self._has_fibaro_power else 'not '))

    @staticmethod
    def clean_name(name):
        return name.replace(' ', '\ ')

    @input_status
    def process_input_status(self, status):
        if self._enabled is True:
            input_id = status[0]
            thread = Thread(target=self._process_input, args=(input_id,))
            thread.start()

    def _process_input(self, input_id):
        try:
            inputs = self._environment['inputs']
            if input_id not in inputs:
                return
            input_name = inputs[input_id]['clean_name']
            if input_name != '':
                data = {'type': 'input',
                        'id': input_id,
                        'name': input_name}
                self._send(self._build_command('event', data, 'true'))
                self.logger('Processed input {0} ({1})'.format(input_id, inputs[input_id]['name']))
            else:
                self.logger('Not sending input {0}: Name is empty'.format(input_id))
        except Exception as ex:
            self.logger('Error processing input: {0}'.format(ex))

    @output_status
    def process_output_status(self, status):
        if self._enabled is True:
            try:
                on_outputs = {}
                for entry in status:
                    on_outputs[entry[0]] = entry[1]
                outputs = self._environment['outputs']
                for output_id in outputs:
                    status = outputs[output_id].get('status')
                    dimmer = outputs[output_id].get('dimmer')
                    if status is None or dimmer is None:
                        continue
                    changed = False
                    if output_id in on_outputs:
                        if status != 1:
                            changed = True
                            outputs[output_id]['status'] = 1
                            self.logger('Output {0} changed to ON'.format(output_id))
                        if dimmer != on_outputs[output_id]:
                            changed = True
                            outputs[output_id]['dimmer'] = on_outputs[output_id]
                            self.logger('Output {0} changed to level {1}'.format(output_id, on_outputs[output_id]))
                    elif status != 0:
                        changed = True
                        outputs[output_id]['status'] = 0
                        self.logger('Output {0} changed to OFF'.format(output_id))
                    if changed is True:
                        thread = Thread(target=self._process_outputs, args=([output_id],))
                        thread.start()
            except Exception as ex:
                self.logger('Error processing outputs: {0}'.format(ex))

    def _process_outputs(self, output_ids):
        try:
            influx_data = []
            outputs = self._environment['outputs']
            for output_id in output_ids:
                output_name = outputs[output_id].get('name')
                status = outputs[output_id].get('status')
                dimmer = outputs[output_id].get('dimmer')
                if output_name != '' and status is not None and dimmer is not None:
                    if outputs[output_id]['module_type'] == 'output':
                        level = 100
                    else:
                        level = dimmer
                    if status == 0:
                        level = 0
                    data = {'id': output_id,
                            'name': output_name}
                    for key in ['module_type', 'type', 'floor']:
                        if key in outputs[output_id]:
                            data[key] = outputs[output_id][key]
                    influx_data.append(self._build_command('output', data, '{0}i'.format(level)))
            self._send(influx_data)
        except Exception as ex:
            self.logger('Error processing outputs {0}: {1}'.format(output_ids, ex))

    @background_task
    def run(self):
        threads = [InfluxDB._start_thread(self._run_system, self._intervals.get('system', 60)),
                   InfluxDB._start_thread(self._run_outputs, self._intervals.get('outputs', 60)),
                   InfluxDB._start_thread(self._run_sensors, self._intervals.get('sensors', 60)),
                   InfluxDB._start_thread(self._run_thermostats, self._intervals.get('thermostats', 60)),
                   InfluxDB._start_thread(self._run_errors, self._intervals.get('errors', 120)),
                   InfluxDB._start_thread(self._run_pulsecounters, self._intervals.get('pulsecounters', 30)),
                   InfluxDB._start_thread(self._run_power_openmotics, self._intervals.get('power_openmotics', 10)),
                   InfluxDB._start_thread(self._run_power_openmotics_analytics, self._intervals.get('power_openmotics_analytics', 60)),
                   InfluxDB._start_thread(self._run_power_fibaro, self._intervals.get('power_fibaro', 15)),
                   InfluxDB._start_thread(self._load_environment_configurations, 900)]
        for thread in threads:
            thread.join()

    @staticmethod
    def _start_thread(workload, interval):
        thread = Thread(target=workload, args=(interval,))
        thread.start()
        return thread

    def _pause(self, start, interval, name):
        elapsed = time.time() - start
        if name not in self._timings:
            self._timings[name] = []
        self._timings[name].append(elapsed)
        if len(self._timings[name]) == 100:
            min_elapsed = round(min(self._timings[name]), 2)
            max_elapsed = round(max(self._timings[name]), 2)
            avg_elapsed = round(sum(self._timings[name]) / 100.0, 2)
            self.logger('Duration stats of {0}: min {1}s, avg {2}s, max {3}s'.format(name, min_elapsed, avg_elapsed, max_elapsed))
            self._timings[name] = []
        if elapsed > interval:
            self.logger('Duration of {0} ({1}s) longer than interval ({2}s)'.format(name, round(elapsed, 2), interval))
        sleep = max(0.1, interval - elapsed)
        time.sleep(sleep)

    def _run_system(self, interval):
        while True:
            start = time.time()
            try:
                with open('/proc/uptime', 'r') as f:
                    system_uptime = float(f.readline().split()[0])
                service_uptime = time.time() - self._start
                if service_uptime > self._last_service_uptime + 3600:
                    self._start = time.time()
                    service_uptime = 0
                self._last_service_uptime = service_uptime
                self._send(self._build_command('system', {'name': 'gateway'}, {'service_uptime': service_uptime,
                                                                               'system_uptime': system_uptime}))
            except Exception as ex:
                self.logger('Error sending system data: {0}'.format(ex))
            self._pause(start, interval, 'system')

    def _run_outputs(self, interval):
        while True:
            start = time.time()
            try:
                result = json.loads(self.webinterface.get_output_status(None))
                if result['success'] is False:
                    self.logger('Failed to get output status')
                else:
                    for output in result['status']:
                        output_id = output['id']
                        if output_id not in self._environment['outputs']:
                            continue
                        self._environment['outputs'][output_id]['status'] = output['status']
                        self._environment['outputs'][output_id]['dimmer'] = output['dimmer']
            except CommunicationTimedOutException:
                self.logger('Error getting output status: CommunicationTimedOutException')
            except Exception as ex:
                self.logger('Error getting output status: {0}'.format(ex))
            self._process_outputs(self._environment['outputs'].keys())
            self._pause(start, interval, 'outputs')

    def _run_sensors(self, interval):
        while True:
            start = time.time()
            try:
                temperatures = json.loads(self.webinterface.get_sensor_temperature_status(None))
                humidities = json.loads(self.webinterface.get_sensor_humidity_status(None))
                brightnesses = json.loads(self.webinterface.get_sensor_brightness_status(None))
                influx_data = []
                for sensor_id, sensor in self._environment['sensors'].iteritems():
                    name = sensor['clean_name']
                    if name == '' or name == 'NOT_IN_USE':
                        continue
                    data = {'id': sensor_id,
                            'name': name}
                    values = {}
                    if temperatures['success'] is True and temperatures['status'][sensor_id] is not None:
                        values['temp'] = temperatures['status'][sensor_id]
                    if humidities['success'] is True and humidities['status'][sensor_id] is not None:
                        values['hum'] = humidities['status'][sensor_id]
                    if brightnesses['success'] is True and brightnesses['status'][sensor_id] is not None:
                        values['bright'] = brightnesses['status'][sensor_id]
                    influx_data.append(self._build_command('sensor', data, values))
                if len(influx_data) > 0:
                    self._send(influx_data)
            except CommunicationTimedOutException:
                self.logger('Error getting sensor status: CommunicationTimedOutException')
            except Exception as ex:
                self.logger('Error getting sensor status: {0}'.format(ex))
            self._pause(start, interval, 'sensors')

    def _run_thermostats(self, interval):
        while True:
            start = time.time()
            try:
                thermostats = json.loads(self.webinterface.get_thermostat_status(None))
                if thermostats['success'] is False:
                    self.logger('Failed to get thermostat status')
                else:
                    influx_data = [self._build_command('thermostat',
                                                       {'id': 'G.0',
                                                        'name': 'Global\ configuration'},
                                                       {'on': str(thermostats['thermostats_on']),
                                                        'cooling': str(thermostats['cooling'])})]
                    for thermostat in thermostats['status']:
                        values = {'setpoint': '{0}i'.format(thermostat['setpoint']),
                                  'output0': thermostat['output0'],
                                  'output1': thermostat['output1'],
                                  'outside': thermostat['outside'],
                                  'mode': '{0}i'.format(thermostat['mode']),
                                  'type': '"tbs"' if thermostat['sensor_nr'] == 240 else '"normal"',
                                  'automatic': str(thermostat['automatic']),
                                  'current_setpoint': thermostat['csetp']}
                        if thermostat['sensor_nr'] != 240:
                            values['temperature'] = thermostat['act']
                        influx_data.append(self._build_command('thermostat',
                                                               {'id': '{0}.{1}'.format('C' if thermostats['cooling'] is True else 'H',
                                                                                       thermostat['id']),
                                                                'name': InfluxDB.clean_name(thermostat['name'])},
                                                               values))
                    self._send(influx_data)
            except CommunicationTimedOutException:
                self.logger('Error getting thermostat status: CommunicationTimedOutException')
            except Exception as ex:
                self.logger('Error getting thermostat status: {0}'.format(ex))
            self._pause(start, interval, 'thermostats')

    def _run_errors(self, interval):
        while True:
            start = time.time()
            try:
                errors = json.loads(self.webinterface.get_errors(None))
                if errors['success'] is False:
                    self.logger('Failed to get module errors')
                else:
                    influx_data = []
                    for error in errors['errors']:
                        module = error[0]
                        count = error[1]
                        types = {'i': 'Input',
                                 'I': 'Input',
                                 'T': 'Temperature',
                                 'o': 'Output',
                                 'O': 'Output',
                                 'd': 'Dimmer',
                                 'D': 'Dimmer',
                                 'R': 'Shutter',
                                 'C': 'CAN',
                                 'L': 'OLED'}
                        data = {'type': types[module[0]],
                                'id': module,
                                'name': '{0}\ {1}'.format(types[module[0]], module)}
                        influx_data.append(self._build_command('error', data, '{0}i'.format(count)))
                    self._send(influx_data)
            except CommunicationTimedOutException:
                self.logger('Error getting module errors: CommunicationTimedOutException')
            except Exception as ex:
                self.logger('Error getting module errors: {0}'.format(ex))
            self._pause(start, interval, 'errors')

    def _run_pulsecounters(self, interval):
        while True:
            start = time.time()
            counters_data = {}
            try:
                for counter_id, counter in self._environment['pulse_counters'].iteritems():
                    counters_data[counter_id] = {'name': counter['clean_name'],
                                                 'input': counter['input']}
            except Exception as ex:
                self.logger('Error getting pulse counter configuration: {0}'.format(ex))
            try:
                result = json.loads(self.webinterface.get_pulse_counter_status(None))
                if result['success'] is False:
                    self.logger('Failed to get pulse counter status')
                else:
                    counters = result['counters']
                    for counter_id in counters_data:
                        if len(counters) > counter_id:
                            counters_data[counter_id]['count'] = counters[counter_id]
            except CommunicationTimedOutException:
                self.logger('Error getting pulse counter status: CommunicationTimedOutException')
            except Exception as ex:
                self.logger('Error getting pulse counter status: {0}'.format(ex))
            influx_data = []
            for counter_id in counters_data:
                counter = counters_data[counter_id]
                if counter['name'] != '':
                    data = {'name': counter['name'],
                            'input': counter['input']}
                    influx_data.append(self._build_command('counter', data, counter['count']))
            self._send(influx_data)
            self._pause(start, interval, 'pulse counters')

    def _run_power_openmotics(self, interval):
        while True:
            start = time.time()
            mapping = {}
            power_data = {}
            try:
                result = json.loads(self.webinterface.get_power_modules(None))
                if result['success'] is False:
                    self.logger('Failed to get power modules')
                else:
                    for module in result['modules']:
                        device_id = '{0}.{{0}}'.format(module['address'])
                        mapping[str(module['id'])] = device_id
                        if module['version'] in [8, 12]:
                            for i in xrange(module['version']):
                                power_data[device_id.format(i)] = {'name': InfluxDB.clean_name(module['input{0}'.format(i)])}
                        else:
                            self.logger('Unknown power module version: {0}'.format(module['version']))
            except CommunicationTimedOutException:
                self.logger('Error getting power modules: CommunicationTimedOutException')
            except Exception as ex:
                self.logger('Error getting power modules: {0}'.format(ex))
            try:
                result = json.loads(self.webinterface.get_realtime_power(None))
                if result['success'] is False:
                    self.logger('Failed to get realtime power')
                else:
                    for module_id, device_id in mapping.iteritems():
                        if module_id in result:
                            for index, entry in enumerate(result[module_id]):
                                if device_id.format(index) in power_data:
                                    usage = power_data[device_id.format(index)]
                                    usage.update({'voltage': entry[0],
                                                  'frequency': entry[1],
                                                  'current': entry[2],
                                                  'power': entry[3]})
            except CommunicationTimedOutException:
                self.logger('Error getting realtime power: CommunicationTimedOutException')
            except Exception as ex:
                self.logger('Error getting realtime power: {0}'.format(ex))
            try:
                result = json.loads(self.webinterface.get_total_energy(None))
                if result['success'] is False:
                    self.logger('Failed to get total energy')
                else:
                    for module_id, device_id in mapping.iteritems():
                        if module_id in result:
                            for index, entry in enumerate(result[module_id]):
                                if device_id.format(index) in power_data:
                                    usage = power_data[device_id.format(index)]
                                    usage.update({'counter': entry[0] + entry[1],
                                                  'counter_day': entry[0],
                                                  'counter_night': entry[1]})
            except CommunicationTimedOutException:
                self.logger('Error getting total energy: CommunicationTimedOutException')
            except Exception as ex:
                self.logger('Error getting total energy: {0}'.format(ex))
            influx_data = []
            for device_id in power_data:
                device = power_data[device_id]
                if device['name'] != '':
                    try:
                        data = {'type': 'openmotics',
                                'id': device_id,
                                'name': device['name']}

                        tags = self._tags.get(device['name'], "")
                        data.update(tags)

                        values = {'voltage': device['voltage'],
                                  'current': device['current'],
                                  'frequency': device['frequency'],
                                  'power': device['power'],
                                  'counter': device['counter'],
                                  'counter_day': device['counter_day'],
                                  'counter_night': device['counter_night']}
                        influx_data.append(self._build_command('energy', data, values))
                    except Exception as ex:
                        self.logger('Error processing OpenMotics power device {0}: {1}'.format(device_id, ex))
            self._send(influx_data)
            self._pause(start, interval, 'power (OpenMotics)')

    def _run_power_openmotics_analytics(self, interval):
        while True:
            start = time.time()
            try:
                result = json.loads(self.webinterface.get_power_modules(None))
                if result['success'] is False:
                    self.logger('Failed to get power modules')
                else:
                    for module in result['modules']:
                        device_id = '{0}.{{0}}'.format(module['address'])
                        if module['version'] != 12:
                            if module['version'] != 8:
                                self.logger('Unknown power module version: {0}'.format(module['version']))
                            continue
                        result = json.loads(self.webinterface.get_energy_time(None, module['id']))
                        if result['success'] is False:
                            self.logger('Failed to get time data')
                            continue
                        base_timestamp = None
                        abort = False
                        for i in xrange(12):
                            if abort is True:
                                break
                            name = InfluxDB.clean_name(module['input{0}'.format(i)])
                            if name == '':
                                continue
                            timestamp = base_timestamp
                            length = min(len(result[str(i)]['current']), len(result[str(i)]['voltage']))
                            influx_data = []
                            for j in xrange(length):
                                data = self._build_command('energy_analytics',
                                                           {'type': 'time',
                                                            'id': device_id.format(i),
                                                            'name': name},
                                                           {'current': result[str(i)]['current'][j],
                                                            'voltage': result[str(i)]['voltage'][j]},
                                                           timestamp=timestamp)
                                if base_timestamp is not None:
                                    influx_data.append(data)
                                else:
                                    self._send(data)
                                    query = 'SELECT current FROM energy_analytics ORDER BY time DESC LIMIT 1'
                                    response = requests.get(url=self._query_endpoint,
                                                            params={'q': query},
                                                            headers=self._headers,
                                                            auth=self._auth,
                                                            verify=False)
                                    if response.status_code != 200:
                                        self.logger('Query time failed, received: {0} ({1})'.format(response.text, response.status_code))
                                        abort = True
                                        break
                                    base_timestamp = response.json()['results'][0]['series'][0]['values'][0][0]
                                    timestamp = base_timestamp
                                timestamp += 250000000  # Stretch actual data by 1000 for visualtisation purposes
                            self._send(influx_data)
                        result = json.loads(self.webinterface.get_energy_frequency(None, module['id']))
                        if result['success'] is False:
                            self.logger('Failed to get frequency data')
                            continue
                        base_timestamp = None
                        abort = False
                        for i in xrange(12):
                            if abort is True:
                                break
                            name = InfluxDB.clean_name(module['input{0}'.format(i)])
                            if name == '':
                                continue
                            timestamp = base_timestamp
                            length = min(len(result[str(i)]['current'][0]), len(result[str(i)]['voltage'][0]))
                            influx_data = []
                            for j in xrange(length):
                                data = self._build_command('energy_analytics',
                                                           {'type': 'frequency',
                                                            'id': device_id.format(i),
                                                            'name': name},
                                                           {'current_harmonics': result[str(i)]['current'][0][j],
                                                            'current_phase': result[str(i)]['current'][1][j],
                                                            'voltage_harmonics': result[str(i)]['voltage'][0][j],
                                                            'voltage_phase': result[str(i)]['voltage'][1][j]},
                                                           timestamp=timestamp)
                                if base_timestamp is not None:
                                    influx_data.append(data)
                                else:
                                    self._send(data)
                                    query = 'SELECT current_harmonics FROM energy_analytics ORDER BY time DESC LIMIT 1'
                                    response = requests.get(url=self._query_endpoint,
                                                            params={'q': query},
                                                            headers=self._headers,
                                                            auth=self._auth,
                                                            verify=False)
                                    if response.status_code != 200:
                                        self.logger('Query frequency failed, received: {0} ({1})'.format(response.text, response.status_code))
                                        abort = True
                                        break
                                    base_timestamp = response.json()['results'][0]['series'][0]['values'][0][0]
                                    timestamp = base_timestamp
                                timestamp += 250000000  # Stretch actual data by 1000 for visualtisation purposes
                            self._send(influx_data)
            except CommunicationTimedOutException:
                self.logger('Error getting power analytics: CommunicationTimedOutException')
            except Exception as ex:
                self.logger('Error getting power analytics: {0}'.format(ex))
            self._pause(start, interval, 'power analysis')

    def _run_power_fibaro(self, interval):
        while True:
            start = time.time()
            if self._has_fibaro_power is True:
                usage = self._get_fibaro_power()
                if usage is not None:
                    influx_data = []
                    for device_id in usage:
                        try:
                            device = usage[device_id]
                            name = InfluxDB.clean_name(device['name'])
                            if name == '':
                                return
                            data = {'type': 'fibaro',
                                    'id': device_id,
                                    'name': name}
                            values = {'power': device['power'],
                                      'counter': device['counter']}
                            influx_data.append(self._build_command('energy', data, values))
                        except Exception as ex:
                            self.logger('Error processing Fibaro power device {0}: {1}'.format(device_id, ex))
                    self._send(influx_data)
            self._pause(start, interval, 'power (Fibaro)')

    @staticmethod
    def _build_command(key, tags, value, timestamp=None):
        if isinstance(value, dict):
                values = ','.join('{0}={1}'.format(vname, vvalue)
                                  for vname, vvalue in value.iteritems())
        else:
            values = 'value={0}'.format(value)
        return '{0},{1} {2}{3}'.format(key,
                                       ','.join('{0}={1}'.format(tname, tvalue)
                                                for tname, tvalue in tags.iteritems()),
                                       values,
                                       '' if timestamp is None else ' {0}'.format(timestamp))

    def _send(self, data):
        try:
            if not isinstance(data, list) and not isinstance(data, basestring):
                raise RuntimeError('Invalid data passed in _send ({0})'.format(type(data)))
            if isinstance(data, basestring):
                data = [data]
            if len(data) == 0:
                return True, ''
            response = requests.post(url=self._endpoint,
                                     data='\n'.join(data),
                                     headers=self._headers,
                                     auth=self._auth,
                                     verify=False)
            if response.status_code != 204:
                self.logger('Send failed, received: {0} ({1})'.format(response.text, response.status_code))
                return False, 'Send failed, received: {0} ({1})'.format(response.text, response.status_code)
            return True, ''
        except Exception as ex:
            self.logger('Error sending: {0}'.format(ex))
            return False, 'Error sending: {0}'.format(ex)

    def _get_fibaro_power(self):
        try:
            response = requests.get(url='https://127.0.0.1/plugins/Fibaro/get_power_usage',
                                    params={'token': 'None'},
                                    verify=False)
            if response.status_code == 200:
                result = response.json()
                if result['success'] is True:
                    return result['result']
                else:
                    self.logger('Error loading Fibaro data: {0}'.format(result['msg']))
            else:
                self.logger('Error loading Fibaro data: {0}'.format(response.status_code))
            return None
        except Exception as ex:
            self.logger('Got unexpected error during Fibaro power load: {0}'.format(ex))
            return None

    @om_expose
    def send_data(self, key, tags, value):
        if self._enabled is True:
            tags = json.loads(tags)
            value = json.loads(value)
            success, result = self._send(self._build_command(key, tags, value))
            return json.dumps({'success': success, 'result' if success else 'error': result})
        else:
            return json.dumps({'success': False, 'error': 'InfluxDB plugin not enabled'})

    @om_expose
    def get_config_description(self):
        return json.dumps(InfluxDB.config_description)

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
        self._config = config
        self._read_config()
        if self._enabled:
            cthread = Thread(target=self._load_environment_configurations)
            cthread.start()
            fthread = Thread(target=self._check_fibaro_power)
            fthread.start()
        self.write_config(config)
        return json.dumps({'success': True})
