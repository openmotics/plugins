"""
A ventilation plugin, using statistical humidity data or the dew point to control the ventilation
"""

import six
import time
import math
import traceback
import json
from math import sqrt
from collections import deque
from plugins.base import om_expose, background_task, OMPluginBase, PluginConfigChecker, om_metric_data
from serial_utils import CommunicationTimedOutException
import logging

logger = logging.getLogger(__name__)


class Ventilation(OMPluginBase):
    """
    A ventilation plugin, using statistical humidity or the dew point data to control the ventilation
    """

    name = 'Ventilation'
    version = '2.0.18'
    interfaces = [('config', '1.0'),
                  ('metrics', '1.0')]

    config_description = [{'name': 'low',
                           'type': 'section',
                           'description': 'Output configuration for "low" ventilation',
                           'repeat': True,
                           'min': 1,
                           'content': [{'name': 'output_id', 'type': 'int'},
                                       {'name': 'value', 'type': 'int'}]},
                          {'name': 'medium',
                           'type': 'section',
                           'description': 'Output configuration for "medium" ventilation',
                           'repeat': True,
                           'min': 1,
                           'content': [{'name': 'output_id', 'type': 'int'},
                                       {'name': 'value', 'type': 'int'}]},
                          {'name': 'high',
                           'type': 'section',
                           'description': 'Output configuration for "high" ventilation',
                           'repeat': True,
                           'min': 1,
                           'content': [{'name': 'output_id', 'type': 'int'},
                                       {'name': 'value', 'type': 'int'}]},
                          {'name': 'sensors',
                           'type': 'section',
                           'description': 'Sensors to use for ventilation control.',
                           'repeat': True,
                           'min': 1,
                           'content': [{'name': 'sensor_id', 'type': 'int'}]},
                          {'name': 'mode',
                           'type': 'nested_enum',
                           'description': 'The mode of the ventilation control',
                           'choices': [{'value': 'statistical', 'content': [{'name': 'samples',
                                                                             'type': 'int'},
                                                                            {'name': 'trigger',
                                                                             'type': 'int'}]},
                                       {'value': 'dew_point', 'content': [{'name': 'outside_sensor_id',
                                                                           'type': 'int'},
                                                                          {'name': 'target_lower',
                                                                           'type': 'int'},
                                                                          {'name': 'target_upper',
                                                                           'type': 'int'},
                                                                          {'name': 'offset',
                                                                           'type': 'int'},
                                                                          {'name': 'trigger',
                                                                           'type': 'int'}]}]}]
    metric_definitions = [{'type': 'ventilation',
                           'tags': ['name', 'id'],
                           'metrics': [{'name': 'dewpoint',
                                        'description': 'Dew point',
                                        'type': 'gauge', 'unit': 'degree C'},
                                       {'name': 'absolute_humidity',
                                        'description': 'Absolute humidity',
                                        'type': 'gauge', 'unit': 'g/m3'},
                                       {'name': 'level',
                                        'description': 'Ventilation level',
                                        'type': 'gauge', 'unit': ''},
                                       {'name': 'medium',
                                        'description': 'Medium ventilation limit',
                                        'type': 'gauge', 'unit': '%'},
                                       {'name': 'high',
                                        'description': 'High ventilation limit',
                                        'type': 'gauge', 'unit': '%'},
                                       {'name': 'mean',
                                        'description': 'Average relative humidity level',
                                        'type': 'gauge', 'unit': '%'},
                                       {'name': 'stddev',
                                        'description': 'Stddev relative humidity level',
                                        'type': 'gauge', 'unit': '%'},
                                       {'name': 'samples',
                                        'description': 'Amount of samples',
                                        'type': 'gauge', 'unit': ''}]}]

    default_config = {}

    def __init__(self, webinterface, connector):
        super(Ventilation, self).__init__(webinterface=webinterface,
                                            connector=connector)

        logger.info('Starting Ventilation plugin...')

        self._config = self.read_config(Ventilation.default_config)
        self._config_checker = PluginConfigChecker(Ventilation.config_description)
        self._used_sensors = []

        self._samples = {}
        self._sensors = {}
        self._runtime_data = {}
        self._settings = {}
        self._last_ventilation = None
        self._metrics_queue = deque()

        self._read_config()

        logger.info("Started Ventilation plugin")

    def _read_config(self):
        self._outputs = {1: self._config.get('low', []),
                         2: self._config.get('medium', []),
                         3: self._config.get('medium', [])}
        self._used_sensors = [sensor['sensor_id'] for sensor in self._config.get('sensors', [])]
        self._mode, self._settings = self._config.get('mode', ['disabled', {}])
        self._enabled = len(self._used_sensors) > 0 and self._mode in ['dew_point', 'statistical']
        logger.info('Ventilation is {0}'.format('enabled' if self._enabled else 'disabled'))

    def _load_sensors(self):
        try:
            configs = json.loads(self.webinterface.get_sensor_configurations())
            if configs['success'] is False:
                logger.error('Failed to get sensor configurations: {0}'.format(configs.get('msg', 'Unknown error')))
            else:
                sensor_ids = []
                for sensor in configs['config']:
                    sensor_id = sensor['id']
                    if sensor_id in self._used_sensors or sensor_id == self._settings.get('outside_sensor_id'):
                        sensor_ids.append(sensor_id)
                        self._samples[sensor_id] = []
                        self._sensors[sensor_id] = sensor['name'] if sensor['name'] != '' else sensor_id
                for sensor_id in self._sensors.keys():
                    if sensor_id not in sensor_ids:
                        self._sensors.pop(sensor_id, None)
                        self._samples.pop(sensor_id, None)
        except CommunicationTimedOutException:
            logger.exception('Error getting sensor status: CommunicationTimedOutException')
        except Exception as ex:
            logger.exception('Error getting sensor status: {0}'.format(ex))

    @background_task
    def run(self):
        self._runtime_data = {}
        while True:
            if self._enabled:
                start = time.time()
                self._load_sensors()
                if self._mode == 'statistical':
                    self._process_statistics()
                elif self._mode == 'dew_point':
                    self._process_dew_point()
                # This loop should run approx. every minute.
                sleep = 60 - (time.time() - start)
                if sleep < 0:
                    sleep = 1
                time.sleep(sleep)
            else:
                time.sleep(5)

    def _process_dew_point(self):
        try:
            dew_points = {}
            abs_humidities = {}
            humidities = {}
            sensor_temperatures = {}
            outdoor_abs_humidity = None
            outdoor_dew_point = None
            outdoor_sensor_id = self._settings['outside_sensor_id']
            # Fetch data
            data_humidities = json.loads(self.webinterface.get_sensor_humidity_status())
            if data_humidities['success'] is False:
                logger.error('Failed to read humidities: {0}'.format(data_humidities.get('msg', 'Unknown error')))
                return
            data_temperatures = json.loads(self.webinterface.get_sensor_temperature_status())
            if data_temperatures['success'] is False:
                logger.error('Failed to read temperatures: {0}'.format(data_temperatures.get('msg', 'Unknown error')))
                return
            for sensor_id in range(len(data_humidities['status'])):
                if sensor_id not in self._used_sensors + [outdoor_sensor_id]:
                    continue
                humidity = data_humidities['status'][sensor_id]
                if humidity is None:
                    continue
                temperature = data_temperatures['status'][sensor_id]
                if temperature is None:
                    continue
                humidities[sensor_id] = humidity
                if sensor_id == outdoor_sensor_id:
                    outdoor_dew_point = Ventilation._dew_point(temperature, humidity)
                    outdoor_abs_humidity = Ventilation._abs_humidity(temperature, humidity)
                else:
                    sensor_temperatures[sensor_id] = temperature
                    dew_points[sensor_id] = Ventilation._dew_point(temperature, humidity)
                    abs_humidities[sensor_id] = Ventilation._abs_humidity(temperature, humidity)
            if outdoor_abs_humidity is None or outdoor_dew_point is None:
                logger.error('Could not load outdoor humidity or temperature')
                return
            # Calculate required ventilation based on sensor information
            target_lower = self._settings['target_lower']
            target_upper = self._settings['target_upper']
            offset = self._settings['offset']
            ventilation = 1
            trigger_sensors = {1: [],
                               2: [],
                               3: []}
            for sensor_id in dew_points:
                if sensor_id not in self._sensors:
                    continue
                if sensor_id not in self._runtime_data:
                    self._runtime_data[sensor_id] = {'trigger': 0,
                                                     'ventilation': 1,
                                                     'candidate': 1,
                                                     'reason': '',
                                                     'name': self._sensors[sensor_id],
                                                     'stats': [0, 0, 0, 0]}
                humidity = humidities[sensor_id]
                dew_point = dew_points[sensor_id]
                abs_humidity = abs_humidities[sensor_id]
                temperature = sensor_temperatures[sensor_id]
                self._runtime_data[sensor_id]['stats'] = [temperature, dew_point, abs_humidity, outdoor_abs_humidity]
                reason = 'RH {0:.2f} <= {1:.2f} <= {2:.2f}'.format(target_lower, humidity, target_upper)
                wanted_ventilation = 1
                # First, try to get the dew point inside the target range - increasing comfort
                if humidity < target_lower or humidity > target_upper:
                    if humidity < target_lower and outdoor_abs_humidity > abs_humidity:
                        wanted_ventilation = 2
                        reason = 'RH {0:.2f} < {1:.2f} and AH {2:.5f} > {3:.5f}'.format(humidity, target_lower, outdoor_abs_humidity, abs_humidity)
                    if humidity > target_upper and outdoor_abs_humidity < abs_humidity:
                        wanted_ventilation = 2
                        reason = 'RH {0:.2f} > {1:.2f} and AH {2:.5f} < {3:.5f}'.format(humidity, target_upper, outdoor_abs_humidity, abs_humidity)
                # Second, prevent actual temperature from hitting the dew point - make sure we don't have condense
                if outdoor_abs_humidity < abs_humidity:
                    if dew_point > temperature - offset:
                        wanted_ventilation = 3
                        reason = 'DP {0:.2f} > {1:.2f} - ({2:.2f})'.format(dew_point, temperature - offset, temperature)
                    elif dew_point > temperature - 2 * offset:
                        wanted_ventilation = 2
                        reason = 'DP {0:.2f} > {1:.2f} - ({2:.2f})'.format(dew_point, temperature - 2 * offset, temperature)
                self._runtime_data[sensor_id]['candidate'] = wanted_ventilation
                current_ventilation = self._runtime_data[sensor_id]['ventilation']
                if current_ventilation != wanted_ventilation:
                    self._runtime_data[sensor_id]['trigger'] += 1
                    self._runtime_data[sensor_id]['reason'] = reason
                    if self._runtime_data[sensor_id]['trigger'] >= self._settings['trigger']:
                        self._runtime_data[sensor_id]['ventilation'] = wanted_ventilation
                        self._runtime_data[sensor_id]['trigger'] = 0
                        current_ventilation = wanted_ventilation
                        trigger_sensors[wanted_ventilation].append(sensor_id)
                else:
                    self._runtime_data[sensor_id]['reason'] = ''
                    self._runtime_data[sensor_id]['trigger'] = 0
                ventilation = max(ventilation, self._runtime_data[sensor_id]['ventilation'])
                self._enqueue_metrics(tags={'id': sensor_id,
                                            'name': self._sensors[sensor_id]},
                                      values={'dewpoint': float(dew_point),
                                              'absolute_humidity': float(abs_humidity),
                                              'level': int(current_ventilation)})
            self._enqueue_metrics(tags={'id': outdoor_sensor_id,
                                        'name': self._sensors[outdoor_sensor_id]},
                                  values={'dewpoint': float(outdoor_dew_point),
                                          'absolute_humidity': float(outdoor_abs_humidity),
                                          'level': 0})
            if ventilation != self._last_ventilation:
                if self._last_ventilation is None:
                    logger.info('Updating ventilation to 1 (startup)')
                else:
                    logger.info('Updating ventilation to {0} because of sensors: {1}'.format(
                        ventilation,
                        ', '.join(['{0} ({1})'.format(self._sensors[sensor_id],
                                                      self._runtime_data[sensor_id]['reason'])
                                   for sensor_id in trigger_sensors[ventilation]])
                    ))
                self._set_ventilation(ventilation)
                self._last_ventilation = ventilation
        except CommunicationTimedOutException:
            logger.exception('Error getting sensor status: CommunicationTimedOutException')
        except Exception as ex:
            logger.exception('Error calculating ventilation: {0}'.format(ex))
            # logger.exception('Stacktrace: {0}'.format(traceback.format_exc()))

    def _process_statistics(self):
        try:
            # Fetch data
            humidities = json.loads(self.webinterface.get_sensor_humidity_status())
            if humidities['success'] is True:
                for sensor_id in range(len(humidities['status'])):
                    if sensor_id not in self._samples:
                        continue
                    value = humidities['status'][sensor_id]
                    if value == 255:
                        continue
                    self._samples[sensor_id].append(value)
                    if len(self._samples[sensor_id]) > self._settings.get('samples', 1440):
                        self._samples[sensor_id].pop(0)
            # Calculate required ventilation based on sensor information
            ventilation = 1
            trigger_sensors = {1: [],
                               2: [],
                               3: []}
            for sensor_id in self._samples:
                if sensor_id not in self._sensors:
                    continue
                if sensor_id not in self._runtime_data:
                    self._runtime_data[sensor_id] = {'trigger': 0,
                                                     'ventilation': 1,
                                                     'candidate': 1,
                                                     'difference': '',
                                                     'name': self._sensors[sensor_id],
                                                     'stats': [0, 0, 0]}
                current = self._samples[sensor_id][-1]
                mean = Ventilation._mean(self._samples[sensor_id])
                stddev = Ventilation._stddev(self._samples[sensor_id])
                level_2 = mean + 2 * stddev
                level_3 = mean + 3 * stddev
                self._runtime_data[sensor_id]['stats'] = [current, level_2, level_3]
                if current > level_3:
                    wanted_ventilation = 3
                    difference = '{0:.2f} > {1:.2f}'.format(current, level_3)
                elif current > level_2:
                    wanted_ventilation = 2
                    difference = '{0:.2f} > {1:.2f}'.format(current, level_2)
                else:
                    wanted_ventilation = 1
                    difference = '{0:.2f} <= {1:.2f}'.format(current, level_2)
                self._runtime_data[sensor_id]['candidate'] = wanted_ventilation
                current_ventilation = self._runtime_data[sensor_id]['ventilation']
                if current_ventilation != wanted_ventilation:
                    self._runtime_data[sensor_id]['trigger'] += 1
                    self._runtime_data[sensor_id]['difference'] = difference
                    if self._runtime_data[sensor_id]['trigger'] >= self._settings['trigger']:
                        self._runtime_data[sensor_id]['ventilation'] = wanted_ventilation
                        self._runtime_data[sensor_id]['trigger'] = 0
                        current_ventilation = wanted_ventilation
                        trigger_sensors[wanted_ventilation].append(sensor_id)
                else:
                    self._runtime_data[sensor_id]['difference'] = ''
                    self._runtime_data[sensor_id]['trigger'] = 0
                ventilation = max(ventilation, self._runtime_data[sensor_id]['ventilation'])
                self._enqueue_metrics(tags={'id': sensor_id,
                                            'name': self._sensors[sensor_id]},
                                      values={'medium': float(level_2),
                                              'high': float(level_3),
                                              'mean': float(mean),
                                              'stddev': float(stddev),
                                              'samples': len(self._samples[sensor_id]),
                                              'level': int(current_ventilation)})
            if ventilation != self._last_ventilation:
                if self._last_ventilation is None:
                    logger.info('Updating ventilation to 1 (startup)')
                else:
                    logger.info('Updating ventilation to {0} because of sensors: {1}'.format(
                        ventilation,
                        ', '.join(['{0} ({1})'.format(self._sensors[sensor_id],
                                                      self._runtime_data[sensor_id]['difference'])
                                   for sensor_id in trigger_sensors[ventilation]])
                    ))
                self._set_ventilation(ventilation)
                self._last_ventilation = ventilation
        except CommunicationTimedOutException:
            logger.exception('Error getting sensor status: CommunicationTimedOutException')
        except Exception as ex:
            logger.exception('Error calculating ventilation')

    def _set_ventilation(self, level):
        success = True
        for setting in self._outputs[level]:
            output_id = int(setting['output_id'])
            value = setting['value']
            on = value > 0
            if on is False:
                value = None
            result = json.loads(self.webinterface.set_output(id=output_id, is_on=str(on), dimmer=value, timer=None))
            if result['success'] is False:
                logger.error('Error setting output {0} to {1}: {2}'.format(output_id, 'OFF' if value is None else value, result['msg']))
                success = False
        if success is True:
            logger.info('Ventilation set to {0}'.format(level))
        else:
            logger.error('Could not set ventilation to {0}'.format(level))
            success = False
        return success

    def _enqueue_metrics(self, tags, values):
        try:
            now = time.time()
            self._metrics_queue.appendleft({'type': 'ventilation',
                                            'timestamp': now,
                                            'tags': tags,
                                            'values': values})
        except Exception as ex:
            logger.exception('Got unexpected error while enqueing metrics: {0}'.format(ex))

    @om_metric_data(interval=5)
    def collect_metrics(self):
        # Yield all metrics in the Queue
        try:
            while True:
                yield self._metrics_queue.pop()
        except IndexError:
            pass

    @staticmethod
    def _abs_humidity(temperature, humidity):
        """
        Calculate the absolute humidity (kg/m3) based on temperature and relative humidity.
        Formula was taken from http://www.aprweather.com/pages/calc.htm and should be good-enough for this purpose
        """
        dew_point = Ventilation._dew_point(temperature, humidity)
        return ((6.11 * 10.0 ** (7.5 * dew_point / (237.7 + dew_point))) * 100) / ((temperature + 273.16) * 461.5)

    @staticmethod
    def _dew_point(temperature, humidity):
        """
        Calculates the dew point for a given temperature and humidity
        """
        a = 17.27
        b = 237.7

        def gamma(_temperature, _humidity):
            return ((a * _temperature) / (b + _temperature)) + math.log(_humidity / 100.0)
        return (b * gamma(temperature, humidity)) / (a - gamma(temperature, humidity))

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
        return json.dumps({'runtime_data': self._runtime_data,
                           'ventilation': self._last_ventilation}, indent=4)

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
            if isinstance(config[key], six.string_types):
                config[key] = str(config[key])
        self._config_checker.check_config(config)
        self._config = config
        self._read_config()
        self.write_config(config)
        return json.dumps({'success': True})
