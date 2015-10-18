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
    version = '0.1.25'
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
                        thread = Thread(target=self._process_output, args=(output_id, False))
                        thread.start()
            except Exception as ex:
                self.logger('Error processing outputs: {0}'.format(ex))

    @background_task
    def run(self):
        while True:
            self.logger('Sending intermediate update')
            try:
                result = json.loads(self.webinterface.get_output_configurations(None, None))
                if result['success'] is False:
                    self.logger('Failed to get output configuration')
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
                self._process_output(output_id, False)
            self.logger('Sending intermediate update completed')
            time.sleep(60)

    def _process_input(self, input_id):
        try:
            if input_id not in self._inputs:
                self.logger('Loading input {0}'.format(input_id))
                result = self.webinterface.get_input_configuration(None, input_id)
                if result['success'] is False:
                    self.logger('Failed to load input information')
                self._inputs[input_id] = result['config']
            input_name = InfluxDB._clean_name(self._inputs[input_id]['name'])
            if input_name != '':
                data = {'id': input_id,
                        'name': input_name}
                self._send('input', data, 'true', False)
                time.sleep(1)
                self._send('input', data, 'false', False)
            else:
                self.logger('Not sending input {0}: Name is empty'.format(input_id))
        except CommunicationTimedOutException:
            self.logger('Error processing output: CommunicationTimedOutException')
        except Exception as ex:
            self.logger('Error processing input: {0}'.format(ex))

    def _process_output(self, output_id, log):
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
            self._send('output', data, '{0}i'.format(level), log)
        elif log is True:
            self.logger('Not sending output {0}: Name is empty'.format(output_id))

    def _send(self, key, tags, value, log):
        try:
            data = '{0},{1} value={2}'.format(key,
                                              ','.join('{0}={1}'.format(tname, tvalue)
                                                       for tname, tvalue in tags.iteritems()),
                                              value)
            if log is True:
                self.logger('Sending: {0}'.format(data))
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
