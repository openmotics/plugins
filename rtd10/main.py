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
RTD10 plugin
"""

from threading import Thread
import simplejson as json
import six
import time

from plugins.base import om_expose, background_task, thermostat_status, OMPluginBase, PluginConfigChecker


class RTD10(OMPluginBase):
    """
    RTD10 plugin
    """

    name = 'RTD10'
    version = '0.1.4'
    interfaces = [('config', '1.0')]

    config_description = [{'name': 'thermostats',
                           'type': 'section',
                           'description': 'Thermostats',
                           'repeat': True,
                           'min': 1,
                           'content': [{'name': 'thermostat_id',
                                        'type': 'int',
                                        'description': 'OpenMotics thermostat ID'},
                                       {'name': 's1_output_id',
                                        'type': 'int',
                                        'description': 'Output connected to the S1 port (setpoint control)'},
                                       {'name': 's1_temperature_curve',
                                        'type': 'str',
                                        'description': 'Setpoint control temperature curve'},
                                       {'name': 's2_output_id',
                                        'type': 'int',
                                        'description': 'Output connected to the S2 port (ventilation control)'},
                                       {'name': 's2_value',
                                        'type': 'int',
                                        'description': 'Ventilation output value (0-100, in percent of 0-10V)'},
                                       {'name': 's3_output_id',
                                        'type': 'int',
                                        'description': 'Output connected to the S3 port (mode)'},
                                       {'name': 's4_output_id',
                                        'type': 'int',
                                        'description': 'Output connected to the S4 port (air direction)'},
                                       {'name': 's4_value',
                                        'type': 'int',
                                        'description': 'Air direction output value (0-100, in percent of 0-10V)'},
                                       {'name': 's5_output_id',
                                        'type': 'int',
                                        'description': 'Output connected to the S5 port (state)'}]}]
    default_config = {}

    def __init__(self, webinterface, logger):
        super(RTD10, self).__init__(webinterface, logger)
        self.logger('Starting RTD10 plugin...')

        self._config = self.read_config(RTD10.default_config)
        self._config_checker = PluginConfigChecker(RTD10.config_description)

        self._enabled = False
        self._syncing = False
        self._thermostats = {}
        self._s_values = {}

        self._read_config()

        self.logger("Started RTD10 plugin")

    def _read_config(self):
        self._enabled = False

        try:
            used_ids = []
            for thermostat in self._config.get('thermostats', []):
                thermostat_id = int(thermostat.get('thermostat_id'))
                config = {'s{0}_output_id'.format(i): int(thermostat.get('s{0}_output_id'.format(i)))
                          for i in range(1, 6)}
                temperature_curve = {float(key): int(value)
                                     for key, value in json.loads(thermostat.get('s1_temperature_curve')).items()}
                config.update({'s1_temperature_curve': temperature_curve,
                               's2_value': int(thermostat.get('s2_value')),
                               's4_value': int(thermostat.get('s4_value'))})
                self._thermostats[thermostat_id] = config
                used_ids.append(thermostat_id)
            for thermostat_id in list(self._thermostats.keys()):
                if thermostat_id not in used_ids:
                    self._thermostats.pop(thermostat_id, None)
            self._enabled = True
        except Exception as ex:
            self.logger('Could not read/process configuration: {0}'.format(ex))

        self.logger('RTD10 is {0}'.format('enabled' if self._enabled else 'disabled'))
        if self._enabled:
            thread = Thread(target=self._sync)
            thread.start()

    def _sync(self):
        if self._syncing:
            return
        self.logger('Performing initial sync...')
        try:
            self._syncing = True
            while True:
                try:
                    result = json.loads(self.webinterface.get_thermostat_group_status())
                    if result.get('success', False) is False:
                        raise RuntimeError(result.get('msg', 'Unknown error'))
                    for thermostat_group_status in result.get('status', []):
                        mode = thermostat_group_status['mode'].upper()  # COOLING / HEATING
                        for thermostat_status in thermostat_group_status['thermostats']:
                            thermostat_id = thermostat_status['id']
                            state = thermostat_status['state'].upper()  # ON / OFF
                            setpoint = thermostat_status['setpoint_temperature']
                            self._drive_device(thermostat_id=thermostat_id,
                                               mode=mode,
                                               state=state,
                                               setpoint=setpoint)
                    return
                except Exception as ex:
                    self.logger('Could not load thermostat group states: {0}'.format(ex))
                    time.sleep(30)
        finally:
            self.logger('Performing initial sync... Done')
            self._syncing = False

    @thermostat_status(version=1)
    def thermostat_status(self, status):
        thermostat_id = status['id']
        mode = status['status']['mode'].upper()  # COOLING / HEATING
        state = status['status']['state'].upper()  # ON / OFF
        setpoint = status['status']['current_setpoint']

        self._drive_device(thermostat_id=thermostat_id,
                           mode=mode,
                           state=state,
                           setpoint=setpoint)

    def _drive_device(self, thermostat_id, mode, state, setpoint):
        configuration = self._thermostats.get(thermostat_id)
        if configuration is None:
            return

        # S1 - Temperature curve: Map the current setpoint to a valve output value
        s1_value = 0
        output_id = configuration['s1_output_id']
        for temperature in sorted(configuration['s1_temperature_curve'].keys()):
            if setpoint >= temperature:
                s1_value = configuration['s1_temperature_curve'][temperature]
        self._set_output(output_id=output_id, output_value=s1_value, s_number=1, thermostat_id=thermostat_id)

        # S2 - Ventilation control: Set the ventilation value (hardcoded configured value)
        output_id = configuration['s2_output_id']
        s2_value = configuration['s2_value']
        self._set_output(output_id=output_id, output_value=s2_value, s_number=2, thermostat_id=thermostat_id)

        # S3 - Mode: Sets the system mode
        output_id = configuration['s3_output_id']
        s3_value = 32 if mode == 'HEATING' else 62
        self._set_output(output_id=output_id, output_value=s3_value, s_number=3, thermostat_id=thermostat_id)

        # S4 - Air direction: Sets the RTD10 air direction
        output_id = configuration['s4_output_id']
        s4_value = configuration['s4_value']
        self._set_output(output_id=output_id, output_value=s4_value, s_number=4, thermostat_id=thermostat_id)

        # S5 - State: Sets the RTD10 state
        output_id = configuration['s5_output_id']
        s5_value = 100 if state == 'ON' else 0
        self._set_output(output_id=output_id, output_value=s5_value, s_number=5, thermostat_id=thermostat_id)

        new_s_values = [s1_value, s2_value, s3_value, s4_value, s5_value]
        if new_s_values != self._s_values.get(thermostat_id):
            self.logger('New S-values for thermostat {0}: {1}'.format(
                thermostat_id,
                ', '.join(['S{0}={1:.1f}V'.format(i + 1, float(new_s_values[i]) / 10.0)
                           for i in range(5)])
            ))
            self._s_values[thermostat_id] = new_s_values

    def _set_output(self, output_id, output_value, s_number, thermostat_id):
        try:
            result = json.loads(self.webinterface.set_output(id=output_id,
                                                             is_on=output_value > 0,
                                                             dimmer=output_value))
            if result.get('success', False) is False:
                raise RuntimeError(result.get('msg', 'Unknown error'))
        except Exception as ex:
            self.logger('Could not set output {0} (S{1} for thermostat {2}) to {3}: {4}'.format(
                output_id, s_number, thermostat_id, output_value, ex
            ))

    @om_expose
    def get_config_description(self):
        return json.dumps(RTD10.config_description)

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
