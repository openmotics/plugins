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
    version = '0.3.3'
    interfaces = [('config', '1.0')]

    config_description = [{'name': 'url',
                           'type': 'str',
                           'description': 'The enpoint for the InfluxDB using HTTP. E.g. http://1.2.3.4:8086'},
                          {'name': 'database',
                           'type': 'str',
                           'description': 'The InfluxDB database name to witch statistics need to be send.'}]

    default_config = {'url': '', 'database': 'openmotics'}

    def __init__(self, webinterface, logger):
        super(InfluxDB, self).__init__(webinterface, logger)
        self.logger('Starting InfluxDB plugin...')

        self._config = self.read_config(InfluxDB.default_config)
        self._config_checker = PluginConfigChecker(InfluxDB.config_description)
        self._outputs = {}
        self._inputs = {}
        self._sensors = {}
        self._errors = {}
        self._counters = {}

        self._read_config()

        self.logger("Started InfluxDB plugin")

    def _read_config(self):
        self._url = self._config['url']
        self._database = self._config['database']

        self._endpoint = '{0}/write?db={1}'.format(self._url, self._database)
        self._headers = {'X-Requested-With': 'OpenMotics plugin: InfluxDB'}

        self._enabled = self._url != '' and self._database != ''
        self.logger('InfluxDB is {0}'.format('enabled' if self._enabled else 'disabled'))

    @staticmethod
    def _clean_name(name):
        return name.replace(' ', '\ ')

    @input_status
    def input_status(self, status):
        if self._enabled is True:
            input_id = status[0]
            thread = Thread(target=self._process_input,
                            args=(input_id,))
            thread.start()

    @output_status
    def output_status(self, status):
        if self._enabled is True:
            try:
                on_outputs = {}
                for entry in status:
                    on_outputs[entry[0]] = entry[1]
                self.logger('Active outputs: {0}'.format(on_outputs.keys()))
                for output_id in self._outputs:
                    changed = False
                    if output_id in on_outputs:
                        if self._outputs[output_id]['status'] == 0:
                            changed = True
                            self._outputs[output_id]['status'] = 1
                            self.logger('Output {0} changed to ON'.format(output_id))
                        if self._outputs[output_id]['dimmer'] != on_outputs[output_id]:
                            changed = True
                            self._outputs[output_id]['dimmer'] = on_outputs[output_id]
                            self.logger('Output {0} changed to level {1}'.format(output_id, on_outputs[output_id]))
                    elif self._outputs[output_id]['status'] == 1:
                        changed = True
                        self._outputs[output_id]['status'] = 0
                        self.logger('Output {0} changed to OFF'.format(output_id))
                    if changed is True:
                        thread = Thread(target=self._process_output, args=(output_id,))
                        thread.start()
            except Exception as ex:
                self.logger('Error processing outputs: {0}'.format(ex))

    @background_task
    def run(self):
        while True:
            start = time.time()
            self.logger('Sending intermediate update')
            # Outputs
            try:
                result = json.loads(self.webinterface.get_output_configurations(None, None))
                if result['success'] is False:
                    self.logger('Failed to get output configuration')
                else:
                    for output in result['config']:
                        output_id = output['id']
                        if output_id not in self._outputs:
                            self._outputs[output_id] = {}
                        self._outputs[output_id]['name'] = InfluxDB._clean_name(output['name'])
                        self._outputs[output_id]['module_type'] = {'O': 'output',
                                                                   'D': 'dimmer'}[output['module_type']]
                        self._outputs[output_id]['floor'] = output['floor']
                        self._outputs[output_id]['type'] = 'relay' if output['type'] == 0 else 'light'
            except CommunicationTimedOutException:
                self.logger('Error getting output configuration: CommunicationTimedOutException')
            except Exception as ex:
                self.logger('Error getting output configuration: {0}'.format(ex))
            try:
                result = json.loads(self.webinterface.get_output_status(None))
                if result['success'] is False:
                    self.logger('Failed to get output status')
                else:
                    for output in result['status']:
                        output_id = output['id']
                        if output_id not in self._outputs:
                            self._outputs[output_id] = {}
                        self._outputs[output_id]['status'] = output['status']
                        self._outputs[output_id]['dimmer'] = output['dimmer']
            except CommunicationTimedOutException:
                self.logger('Error getting output status: CommunicationTimedOutException')
            except Exception as ex:
                self.logger('Error getting output status: {0}'.format(ex))
            for output_id in self._outputs:
                self._process_output(output_id)
            # Temperatures
            try:
                configs = json.loads(self.webinterface.get_sensor_configurations(None))
                temperatures = json.loads(self.webinterface.get_sensor_temperature_status(None))
                humidities = json.loads(self.webinterface.get_sensor_humidity_status(None))
                brightnesses = json.loads(self.webinterface.get_sensor_brightness_status(None))
                if configs['success'] is False:
                    self.logger('Failed to get sensor configurations')
                else:
                    for sensor in configs['config']:
                        sensor_id = sensor['id']
                        if sensor_id not in self._sensors:
                            self._sensors[sensor_id] = {'temperature': -1,
                                                        'humidity': -1,
                                                        'brightness': -1}
                        self._sensors[sensor_id]['name'] = InfluxDB._clean_name(sensor['name'])
                        if temperatures['success'] is True:
                            temperature = temperatures['status'][sensor_id]
                            self._sensors[sensor_id]['temperature'] = -1 if temperature == 95.5 else temperature
                        if humidities['success'] is True:
                            humidity = humidities['status'][sensor_id]
                            self._sensors[sensor_id]['humidity'] = -1 if humidity == 255 else humidity
                        if brightnesses['success'] is True:
                            brightness = brightnesses['status'][sensor_id]
                            self._sensors[sensor_id]['brightness'] = -1 if brightness == 255 else brightness
            except CommunicationTimedOutException:
                self.logger('Error getting sensor status: CommunicationTimedOutException')
            except Exception as ex:
                self.logger('Error getting sensor status: {0}'.format(ex))
            for sensor_id in self._sensors:
                self._process_sensor(sensor_id)
            # Errors
            try:
                errors = json.loads(self.webinterface.get_errors(None))
                if errors['success'] is False:
                    self.logger('Failed to get module errors')
                else:
                    for error in errors['errors']:
                        self._errors[error[0]] = error[1]
            except CommunicationTimedOutException:
                self.logger('Error getting module errors: CommunicationTimedOutException')
            except Exception as ex:
                self.logger('Error getting module errors: {0}'.format(ex))
            for module in self._errors:
                self._process_error(module)
            # Pulse counters
            try:
                result = json.loads(self.webinterface.get_pulse_counter_configurations(None, None))
                if result['success'] is False:
                    self.logger('Failed to get pulse counter configuration')
                else:
                    for counter in result['config']:
                        counter_id = counter['id']
                        if counter_id not in self._counters:
                            self._counters[counter_id] = {}
                        self._counters[counter_id]['name'] = InfluxDB._clean_name(counter['name'])
                        self._counters[counter_id]['input'] = counter['input']
            except CommunicationTimedOutException:
                self.logger('Error getting pulse counter configuration: CommunicationTimedOutException')
            except Exception as ex:
                self.logger('Error getting pulse counter configuration: {0}'.format(ex))
            try:
                result = json.loads(self.webinterface.get_pulse_counter_status(None))
                if result['success'] is False:
                    self.logger('Failed to get pulse counter status')
                else:
                    counters = result['counters']
                    for counter_id in self._counters:
                        if len(counters) > counter_id:
                            self._counters[counter_id]['count'] = counters[counter_id]
            except CommunicationTimedOutException:
                self.logger('Error getting pulse counter status: CommunicationTimedOutException')
            except Exception as ex:
                self.logger('Error getting pulse counter status: {0}'.format(ex))
            for counter_id in self._counters:
                self._process_counter(counter_id)
            self.logger('Sending intermediate update completed')
            sleep = 60 - (time.time() - start)
            if sleep < 0:
                sleep = 1
            time.sleep(sleep)

    def _process_input(self, input_id):
        try:
            if input_id not in self._inputs:
                self.logger('Loading input {0}'.format(input_id))
                result = json.loads(self.webinterface.get_input_configuration(None, input_id))
                if result['success'] is False:
                    self.logger('Failed to load input information')
                self._inputs[input_id] = result['config']
            input_name = InfluxDB._clean_name(self._inputs[input_id]['name'])
            if input_name != '':
                data = {'type': 'input',
                        'id': input_id,
                        'name': input_name}
                self._send('event', data, 'true')
            else:
                self.logger('Not sending input {0}: Name is empty'.format(input_id))
        except CommunicationTimedOutException:
            self.logger('Error processing output: CommunicationTimedOutException')
        except Exception as ex:
            self.logger('Error processing input: {0}'.format(ex))

    def _process_output(self, output_id):
        output_name = self._outputs[output_id].get('name')
        if output_name != '':
            level = self._outputs[output_id].get('dimmer', 0)
            if self._outputs[output_id].get('status', 0) == 0:
                level = 0
            data = {'id': output_id,
                    'name': output_name}
            for key in ['module_type', 'type', 'floor']:
                if key in self._outputs[output_id]:
                    data[key] = self._outputs[output_id][key]
            self._send('output', data, '{0}i'.format(level))

    def _process_sensor(self, sensor_id):
        sensor_name = self._sensors[sensor_id].get('name')
        if sensor_name != '':
            temperature = self._sensors[sensor_id]['temperature']
            humidity = self._sensors[sensor_id]['humidity']
            brightness = self._sensors[sensor_id]['brightness']
            data = {'id': sensor_id,
                    'name': sensor_name}
            values = {}
            if temperature != -1:
                values['temp'] = temperature
            if humidity != -1:
                values['hum'] = humidity
            if brightness != -1:
                values['bright'] = brightness
            self._send('sensor', data, values)

    def _process_error(self, module):
        count = self._errors[module]
        types = {'I': 'Input',
                 'T': 'Temperature',
                 'O': 'Output',
                 'D': 'Dimmer',
                 'R': 'Shutter',
                 'L': 'OLED'}
        data = {'type': types[module[0]],
                'id': module,
                'name': '{0}\ {1}'.format(types[module[0]], module)}
        self._send('error', data, '{0}i'.format(count))

    def _process_counter(self, counter_id):
        counter = self._counters[counter_id]
        if counter['name'] != '':
            data = {'name': counter['name'],
                    'input': counter['input']}
            self._send('counter', data, counter['count'])

    def _send(self, key, tags, value):
        try:
            if isinstance(value, dict):
                values = ','.join('{0}={1}'.format(vname, vvalue)
                                  for vname, vvalue in value.iteritems())
            else:
                values = 'value={0}'.format(value)
            data = '{0},{1} {2}'.format(key,
                                        ','.join('{0}={1}'.format(tname, tvalue)
                                                 for tname, tvalue in tags.iteritems()),
                                        values)
            response = requests.post(url=self._endpoint,
                                     data=data,
                                     headers=self._headers,
                                     verify=False)
            if response.status_code != 204:
                self.logger('Send failed, received: {0} ({1})'.format(response.text, response.status_code))
        except Exception as ex:
            self.logger('Error sending: {0}'.format(ex))

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
        self.write_config(config)
        return json.dumps({'success': True})
