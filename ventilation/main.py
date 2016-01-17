"""
A ventilation plugin, using statistical humidity data to control the ventilation
"""

import time
import simplejson as json
from math import sqrt
from plugins.base import om_expose, receive_events, background_task, OMPluginBase, PluginConfigChecker
from serial_utils import CommunicationTimedOutException


class Ventilation(OMPluginBase):
    """
    A ventilation plugin, using statistical humidity data to control the ventilation
    """

    name = 'Ventilation'
    version = '0.1.31'
    interfaces = [('config', '1.0')]

    config_description = [{'name': 'outputs',
                           'type': 'str',
                           'description': 'A JSON formatted dict containing output parameters for 3 ventilation settings. See README.md for more details.'},
                          {'name': 'samples',
                           'type': 'int',
                           'description': 'The number of samples on which to calculate the statistical threshold. There is one sample per minute.'},
                          {'name': 'trigger',
                           'type': 'int',
                           'description': 'The numer of samples that must be above or below the threshold.'},
                          {'name': 'ignore_sensors',
                           'type': 'str',
                           'description': 'A JSON formatted list containing humidity sensor ids to be ignored.'}]

    default_config = {'outputs': '{}', 'samples': 60 * 24, 'trigger': 3, 'ignore_sensors': '[]'}

    def __init__(self, webinterface, logger):
        super(Ventilation, self).__init__(webinterface, logger)
        self.logger('Starting Ventilation plugin...')

        self._config = self.read_config(Ventilation.default_config)
        self._config_checker = PluginConfigChecker(Ventilation.config_description)

        self._entries = {}
        self._sensors = {}
        self._runtime_data = {}
        self._last_ventilation = None

        self._load_sensors()
        self._read_config()

        self.logger("Started Ventilation plugin")

    def _read_config(self):
        self._outputs = json.loads(self._config['outputs'])
        self._samples = self._config['samples']
        self._trigger = self._config.get('trigger', Ventilation.default_config['trigger'])
        self._ignore_sensors = json.loads(self._config.get('ignore_sensors', Ventilation.default_config['ignore_sensors']))
        self._enabled = len(self._sensors) > 0 and self._samples > 0 and '1' in self._outputs and '2' in self._outputs and '3' in self._outputs
        self.logger('Ventilation is {0}'.format('enabled' if self._enabled else 'disabled'))

    def _load_sensors(self):
        try:
            configs = json.loads(self.webinterface.get_sensor_configurations(None))
            if configs['success'] is False:
                self.logger('Failed to get sensor configurations')
            else:
                for sensor in configs['config']:
                    sensor_id = sensor['id']
                    self._sensors[sensor_id] = sensor['name']
        except CommunicationTimedOutException:
            self.logger('Error getting sensor status: CommunicationTimedOutException')
        except Exception as ex:
            self.logger('Error getting sensor status: {0}'.format(ex))

    @background_task
    def run(self):
        if self._enabled:
            self._runtime_data = {}
            while True:
                start = time.time()
                try:
                    # Fetch data
                    humidities = json.loads(self.webinterface.get_sensor_humidity_status(None))
                    if humidities['success'] is True:
                        for sensor_id in range(len(humidities['status'])):
                            if sensor_id in self._ignore_sensors:
                                continue
                            value = humidities['status'][sensor_id]
                            if value == 255:
                                continue
                            if sensor_id not in self._entries:
                                self._entries[sensor_id] = []
                            self._entries[sensor_id].append(value)
                            if len(self._entries[sensor_id]) > self._samples:
                                self._entries[sensor_id].pop(0)
                    # Calculate which sensors cause which ventilation change
                    ventilation = 1
                    trigger_sensors = {1: [],
                                       2: [],
                                       3: []}
                    for sensor_id in self._entries:
                        if sensor_id not in self._runtime_data:
                            self._runtime_data[sensor_id] = {'trigger': 0,
                                                            'ventilation': 1,
                                                            'difference': 0,
                                                            'stats': [0, 0, 0]}
                        current = self._entries[sensor_id][-1]
                        mean = Ventilation._mean(self._entries[sensor_id])
                        stddev = Ventilation._stddev(self._entries[sensor_id])
                        level_2 = mean + 2 * stddev
                        level_3 = mean + 3 * stddev
                        self._runtime_data[sensor_id]['stats'] = [current, level_2, level_3]
                        self._runtime_data[sensor_id]['difference'] = ''
                        this_ventilation = 1
                        if current > level_3:
                            this_ventilation = 3
                            self._runtime_data[sensor_id]['difference'] = '{0:.2f} > {1:.2f}'.format(current, level_3)
                        elif current > level_2:
                            this_ventilation = 2
                            self._runtime_data[sensor_id]['difference'] = '{0:.2f} > {1:.2f}'.format(current, level_2)
                        if this_ventilation != self._runtime_data[sensor_id]['ventilation']:
                            self._runtime_data[sensor_id]['trigger'] = 0
                        else:
                            self._runtime_data[sensor_id]['trigger'] += 1
                            if self._runtime_data[sensor_id]['trigger'] >= self._trigger:
                                trigger_sensors[this_ventilation].append(sensor_id)
                                ventilation = max(ventilation, this_ventilation)
                        self._runtime_data[sensor_id]['ventilation'] = this_ventilation
                    if ventilation != self._last_ventilation:
                        if self._last_ventilation is None:
                            self.logger('Updating ventilation to 1 (startup)')
                        elif ventilation == 1:
                            self.logger('Resetting ventilation back to 1')
                        else:
                            self.logger('Updating ventilation to {0} because of sensors: {1}'.format(
                                ventilation,
                                ', '.join(['{0} ({1})'.format(self._sensors[sensor_id],
                                                              self._runtime_data[sensor_id]['difference'])
                                           for sensor_id in trigger_sensors[ventilation]])
                            ))
                        # Set ventilation to new value
                        success = True
                        outputs = self._outputs[str(ventilation)]
                        for output_id, value in outputs.iteritems():
                            on = value > 0
                            if on is False:
                                value = None
                            result = json.loads(self.webinterface.set_output(None, int(output_id), is_on=str(on), dimmer=value, timer=None))
                            if result['success'] is False:
                                self.logger('Error setting output {0} to {1}: {2}'.format(output_id, value, result['msg']))
                                success = False
                        if success is True:
                            self.logger('Ventilation set to {0}'.format(ventilation))
                        else:
                            self.logger('Could not set ventilation to {0}'.format(ventilation))
                        self._last_ventilation = ventilation
                except CommunicationTimedOutException:
                    self.logger('Error getting sensor status: CommunicationTimedOutException')
                except Exception as ex:
                    self.logger('Error getting sensor status: {0}'.format(ex))
                sleep = 60 - (time.time() - start)
                if sleep < 0:
                    sleep = 1
                time.sleep(sleep)

    @staticmethod
    def _mean(entries):
        """
        Calculates mean
        """
        if len(entries) > 0:
            return sum(entries) * 1.0 / len(entries)
        return 0

    @staticmethod
    def _stddev(entries):
        """
        Calculates standard deviation
        """
        mean = Ventilation._mean(entries)
        variance = map(lambda e: (e - mean) ** 2, entries)
        return sqrt(Ventilation._mean(variance))

    @om_expose
    def get_debug(self):
        return json.dumps(self._runtime_data, indent=4)

    @om_expose
    def get_config_description(self):
        return json.dumps(Ventilation.config_description)

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
