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
from contextlib import contextmanager
from six.moves.queue import Queue

from plugins.base import om_expose, background_task, output_status, thermostat_status, thermostat_group_status, OMPluginBase, PluginConfigChecker


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
                with self._process_message(command=command, identifier=identifier,
                                           regex=r'^automation\.(\d+)=execute$') as matches:
                    if matches is not None:
                        group_action_id = int(matches[0])
                        RTI._execute_api(function=self.webinterface.do_group_action,
                                         group_action_id=group_action_id)
                        continue
                with self._process_message(command=command, identifier=identifier,
                                           regex=r'^output\.(\d+)\.state=(on|off|toggle)$') as matches:
                    if matches is not None:
                        output_id = int(matches[0])
                        state = matches[1]
                        if state in ['on', 'off']:
                            RTI._execute_api(function=self.webinterface.set_output,
                                             id=output_id,
                                             is_on=state == 'on')
                        else:
                            RTI._execute_api(function=self.webinterface.do_basic_action,
                                             action_type=162,  # Toggle
                                             action_number=output_id)
                        continue
                with self._process_message(command=command, identifier=identifier,
                                           regex=r'^output\.(\d+)\.dimmer=(\d+)$') as matches:
                    if matches is not None:
                        output_id = int(matches[0])
                        value = min(100, max(0, int(matches[1])))
                        RTI._execute_api(function=self.webinterface.set_output,
                                         id=output_id,
                                         is_on=value > 0,
                                         dimmer=value)
                        continue
                with self._process_message(command=command, identifier=identifier,
                                           regex=r'^output=request_current_states$') as matches:
                    if matches is not None:
                        status = RTI._execute_api(function=self.webinterface.get_output_status).get('status', [])
                        for entry in status:
                            self.output_status({'id': entry['id'],
                                                'status': {'on': entry['status'] == 1,
                                                           'value': entry['dimmer']}})
                        continue
                with self._process_message(command=command, identifier=identifier,
                                           regex=r'^thermostat\.(\d+)\.preset=(away|party|vacation|auto)$') as matches:
                    if matches is not None:
                        thermostat_id = int(matches[0])
                        preset = matches[1]
                        RTI._execute_api(function=self.webinterface.set_thermostat,
                                         thermostat_id=thermostat_id,
                                         preset=preset)
                        continue
                with self._process_message(command=command, identifier=identifier,
                                           regex=r'^thermostat\.(\d+)\.setpoint=([\d.]+)$') as matches:
                    if matches is not None:
                        thermostat_id = int(matches[0])
                        setpoint = float(matches[1])
                        RTI._execute_api(function=self.webinterface.set_thermostat,
                                         thermostat_id=thermostat_id,
                                         temperature=setpoint)
                        continue
                with self._process_message(command=command, identifier=identifier,
                                           regex=r'^thermostat\.(\d+)\.state=(on|off)$') as matches:
                    if matches is not None:
                        thermostat_id = int(matches[0])
                        RTI._execute_api(function=self.webinterface.set_thermostat,
                                         thermostat_id=thermostat_id,
                                         state=matches[1])
                        continue
                with self._process_message(command=command, identifier=identifier,
                                           regex=r'^thermostat=request_current_states$') as matches:
                    if matches is not None:
                        status = RTI._execute_api(function=self.webinterface.get_thermostat_group_status).get('status', [])
                        for group_entry in status:
                            for entry in group_entry['thermostats']:
                                self.thermostat_status({'id': entry['id'],
                                                        'status': {'preset': entry['preset'],
                                                                   'state': entry['state'],
                                                                   'current_setpoint': entry['setpoint_temperature'],
                                                                   'actual_temperature': entry['actual_temperature']}})
                        continue
                with self._process_message(command=command, identifier=identifier,
                                           regex=r'^thermostat_group\.(\d+)\.mode=(cooling|heating)$') as matches:
                    if matches is not None:
                        thermostat_group_id = int(matches[0])
                        RTI._execute_api(function=self.webinterface.set_thermostat_group,
                                         thermostat_group_id=thermostat_group_id,
                                         mode=matches[1])
                        continue
                with self._process_message(command=command, identifier=identifier,
                                           regex=r'^thermostat_group=request_current_states$') as matches:
                    if matches is not None:
                        status = RTI._execute_api(function=self.webinterface.get_thermostat_group_status).get('status', [])
                        for group_entry in status:
                            self.thermostat_group_status({'id': group_entry['id'],
                                                          'status': {'mode': group_entry['mode']}})
                        continue
                self.logger('Unprocessed command: {0}'.format(command))
            except Exception as main_exception:
                self.logger('Unexpected exception while processing command {0}: {1}'.format(command, main_exception))

    @contextmanager
    def _process_message(self, command, identifier, regex):
        match = re.match(regex, command)
        if match is not None:
            try:
                yield match.groups()
            except Exception as ex:
                self._process_exception(identifier=identifier, exception=ex)
        else:
            yield None

    @thermostat_group_status(version=1)
    def thermostat_group_status(self, status):
        if self._enabled is False:
            return
        try:
            thermostat_group_id = status['id']
            self._write_serial('thermostat_group.{0}.mode={1}'.format(thermostat_group_id,
                                                                      status['status']['mode'].lower()))
        except Exception as ex:
            self.logger('Could not process thermostat group event {0}: {1}'.format(status, ex))

    @thermostat_status(version=1)
    def thermostat_status(self, status):
        if self._enabled is False:
            return
        try:
            thermostat_id = status['id']
            self._write_serial('thermostat.{0}.preset={1}'.format(thermostat_id, status['status']['preset'].lower()))
            self._write_serial('thermostat.{0}.setpoint={1}'.format(thermostat_id, status['status']['current_setpoint']))
            self._write_serial('thermostat.{0}.state={1}'.format(thermostat_id, status['status']['state'].lower()))
            self._write_serial('thermostat.{0}.temperature={1}'.format(thermostat_id, status['status']['actual_temperature']))
        except Exception as ex:
            self.logger('Could not process thermostat event {0}: {1}'.format(status, ex))

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
