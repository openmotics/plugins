# Copyright (C) 2022 OpenMotics BV
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

"""
RTI plugin
"""

import re
import serial
import simplejson as json
import six
import time
from six.moves.queue import Queue

from plugins.base import om_expose, background_task, output_status, OMPluginBase, PluginConfigChecker


class RTI(OMPluginBase):
    """
    RTI plugin
    """

    name = 'RTI'
    version = '0.0.1'
    interfaces = [('config', '1.0')]

    config_description = [{'name': 'serial_device',
                           'type': 'str',
                           'description': 'The serial device to which the RTI device is connected. Defaults to /dev/ttyO2'},
                          {'name': 'serial_baud_rate',
                           'type': 'int',
                           'description': 'The baud rate of the RTI device. Defaults to 115200'}]
    default_config = {}

    def __init__(self, webinterface, logger):
        super(RTI, self).__init__(webinterface, logger)
        self.logger('Starting RTI plugin...')

        self._config = self.read_config(RTI.default_config)
        self._config_checker = PluginConfigChecker(RTI.config_description)

        self._command_queue = Queue()
        self._enabled = False
        self._serial = None
        self._read_config()

        self.logger("Started RTI plugin")

    def _read_config(self):
        self._serial = None
        try:
            try:
                self._serial = serial.Serial(self._config.get('serial_device', '/dev/ttyO2'),
                                             int(self._config.get('serial_baud_rate', 115200)))
            except Exception as ex:
                self._serial = None
                self.logger('Could not connect to serial port: {0}'.format(ex))
        except Exception as ex:
            self.logger('Could not read/process configuration: {0}'.format(ex))

        self._enabled = self._serial is not None
        self.logger('RTI is {0}'.format('enabled' if self._enabled else 'disabled'))

    @staticmethod
    def _execute_api(function, **kwargs):
        result = json.loads(function(**kwargs))
        if result.get('success') is not True:
            raise RuntimeError(result.get('msg', 'Unknown API error'))
        return result

    def _process_exception(self, identifier, exception):
        self._write_serial('{0}=error|{1}'.format(identifier, str(exception).replace('\r', '<cr>').replace('\n', '<lf>')))

    @background_task
    def _process_commands(self):
        while True:
            if self._enabled is False:
                time.sleep(1)
                continue
            command = None
            try:
                command = self._command_queue.get()
                if '=' not in command:
                    self.logger('Invalid command: {0}'.format(command))
                    continue
                identifier = command.split('=')[0]
                match = re.match(r'^automation\.(\d+)=execute$', command)
                if match is not None:
                    group_action_id = int(match.groups()[0])
                    try:
                        RTI._execute_api(function=self.webinterface.do_group_action,
                                         group_action_id=group_action_id)
                    except Exception as ex:
                        self._process_exception(identifier=identifier, exception=ex)
                    continue
                match = re.match(r'^output\.(\d+)\.state=(on|off|toggle)$', command)
                if match is not None:
                    matches = match.groups()
                    output_id = int(matches[0])
                    state = matches[1]
                    try:
                        if state in ['on', 'off']:
                            RTI._execute_api(function=self.webinterface.set_output,
                                             id=output_id,
                                             is_on=state == 'on')
                        else:
                            RTI._execute_api(function=self.webinterface.do_basic_action,
                                             action_type=162,  # Toggle
                                             action_number=output_id)
                    except Exception as ex:
                        self._process_exception(identifier=identifier, exception=ex)
                    continue
                match = re.match(r'^output\.(\d+)\.dimmer=(\d+)$', command)
                if match is not None:
                    matches = match.groups()
                    output_id = int(matches[0])
                    value = min(100, max(0, int(matches[1])))
                    try:
                        RTI._execute_api(function=self.webinterface.set_output,
                                         id=output_id,
                                         is_on=value > 0,
                                         dimmer=value)
                    except Exception as ex:
                        self._process_exception(identifier=identifier, exception=ex)
                    continue
                match = re.match(r'^output=request_current_states$', command)
                if match is not None:
                    try:
                        status = RTI._execute_api(function=self.webinterface.get_output_status).get('status', [])
                        for entry in status:
                            self.output_status({'id': entry['id'],
                                                'status': {'on': entry['status'] == 1,
                                                           'value': entry['dimmer']}})
                    except Exception as ex:
                        self._process_exception(identifier=identifier, exception=ex)
                    continue
                self.logger('Unprocessed command: {0}'.format(command))
            except Exception as main_exception:
                self.logger('Unexpected exception while processing command {0}: {1}'.format(command, main_exception))

    @output_status(version=2)
    def output_status(self, output_event):
        if self._enabled is False:
            return
        try:
            output_id = output_event['id']
            state = output_event['status'].get('on')
            dimmer_level = output_event['status'].get('value')
            self._write_serial('output.{0}.state={1}'.format(output_id, 'on'if state else 'off'))
            if dimmer_level is not None:
                self._write_serial('output.{0}.dimmer={1}'.format(output_id, dimmer_level))
        except Exception as ex:
            self.logger('Could not process output event {0}: {1}'.format(output_event, ex))

    def _write_serial(self, message):
        if self._serial is not None:
            self._serial.write('{0}\n'.format(message))
        self.logger('Write to serial: {0}'.format(message))

    @background_task
    def _read_serial(self):
        while True:
            if self._enabled is False or self._serial is None:
                time.sleep(1)
                continue
            try:
                command = self._serial.readline().strip()
                self.logger('Received command over serial: {0}'.format(command))
                self._command_queue.put(command)
            except Exception as ex:
                self.logger('Unexpected error while reading from serial device: {0}'.format(ex))

    @om_expose
    def command(self, command):
        self.logger('Received command over API: {0}'.format(command))
        self._command_queue.put(command)

    @om_expose
    def get_config_description(self):
        return json.dumps(RTI.config_description)

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
        self._config = config
        self._read_config()
        self.write_config(config)
        return json.dumps({'success': True})
