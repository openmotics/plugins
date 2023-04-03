"""
Dummy plugin
"""

import json
import logging
import random
import time
import six
from collections import deque

from plugins.base import OMPluginBase, PluginConfigChecker, background_task, \
    om_expose, ventilation_status, om_metric_receive, om_metric_data, hot_water_status
    
logger = logging.getLogger(__name__)


class Dummy(OMPluginBase):
    """
    Dummy plugin
    """

    name = 'Dummy'
    version = '1.1.0'
    interfaces = [('config', '1.0')]

    default_config = {}
    TEMPERATURE = 'temperature'
    HUMIDITY = 'humidity'
    BRIGHTNESS = 'brightness'
    SOUND = 'sound'
    DUST = 'dust'
    COMFORT_INDEX = 'comfort_index'
    AQI = 'aqi'
    CO2 = 'co2'
    VOC = 'voc'
    ELECTRIC_POTENTIAL = 'electric_potential'
    ELECTRIC_CURRENT = 'electric_current'
    FREQUENCY = 'frequency'
    ENERGY = 'energy'
    POWER = 'power'
    HOTWATER = 'hot_water'

    STATUS_RANGES = {'temperature': (20, 25),
                     'humidity': (0, 100),
                     'brightness': (0, 100),
                     'sound': (20, 120),
                     'dust': (0, 50),
                     'comfort_index': (0, 100),
                     'aqi': (0, 100),
                     'co2': (280, 2000),
                     'voc': (0, 300),
                     'electric_potential': (220, 240),
                     'electric_current': (0, 16),
                     'frequency': (47, 53),
                     'energy': (0, 10**6),
                     'power': (0, 10**4)}

    def __init__(self, webinterface, connector):
        super(Dummy, self).__init__(webinterface=webinterface,
                                    connector=connector)
        logger.info('Starting Dummy plugin {0}...'.format(Dummy.version))
        self.config_description = [
            {'name': 'sensors',
             'type': 'section',
             'description': 'Add sensors here',
             'repeat': True,
             'min': 0,
             'content': [{'name': 'name',
                          'type': 'str',
                          'description': 'The name for the sensor'},
                         {'name': 'types',
                          'type': 'section',
                          'repeat': True,
                          'min': 1,
                          'content': [{'name': 'physical',
                                       'type': 'enum',
                                       'choices': self.connector.sensor.Enums.ALL_PHYSICAL_QUANTITIES},
                                      {'name': 'unit',
                                       'type': 'enum',
                                       'choices': self.connector.sensor.Enums.ALL_UNITS}
                                      ]}
                         ]
             },
            {'name': 'hot_water',
             'type': 'bool',
             'description': 'Register a dummy hot water unit'},
            {'name': 'ventilation',
             'type': 'bool',
             'description': 'Register a dummy ventilation unit'},
            {'name': 'notification',
             'type': 'bool',
             'description': 'Publish a cloud notification'}
        ]
        self._config = self.read_config(Dummy.default_config)
        self._config_checker = PluginConfigChecker(self.config_description)

        self.connector.ventilation.subscribe_status_event(Dummy.handle_ventilation_status, version=2)
        self.connector.ventilation.attach_set_auto(self.ventilation_set_auto, version=1)
        self.connector.ventilation.attach_set_manual(self.ventilation_set_manual, version=1)
        self.connector.sensor.subscribe_status_event(Dummy.handle_sensor_status, version=2)
        self.connector.hot_water.subscribe_status_event(self.handle_hot_water_status, version=1)
        self.connector.hot_water.attach_set_state(self.hot_water_state, version=1)
        self.connector.hot_water.attach_set_setpoint(self.hot_water_setpoint, version=1)

        self._metrics_queue = deque()
        self._sensor_dtos = []
        self._ventilation_id = None
        self._wants_registration = True
        self._hot_water = None


        logger.info('Started Dummy plugin {0}'.format(Dummy.version))

    @om_expose
    def get_config_description(self):
        logger.info('Fetching config description')
        return json.dumps(self.config_description)

    @om_expose
    def get_config(self):
        logger.info('Fetching configuration')
        return json.dumps(self._config)

    @om_expose
    def set_config(self, config):
        logger.info('Saving configuration...')
        data = json.loads(config)
        self._save_config(data)
        self._wants_registration = True
        logger.info('Saving configuration... Done')
        return json.dumps({'success': True})

    def _save_config(self, config):
        for key in config:
            if isinstance(config[key], six.string_types):
                config[key] = str(config[key])
        self._config_checker.check_config(config)
        self._config = config
        self.write_config(config)

    def _register_entities(self):
        self._sensor_dtos = []
        sensors = self._config.get('sensors', [])
        logger.info('Registering sensors...')
        for sensor in sensors:
            name = sensor['name']
            sensor_types = sensor['types']
            for sensor_type in sensor_types:
                try:
                    external_id = f"dummy/{name}"
                    sensor = self.connector.sensor.register(external_id=external_id,
                                                            physical_quantity=sensor_type['physical'],
                                                            unit=sensor_type['unit'],
                                                            name=f"{name}-{sensor_type['physical']}")
                    logger.info('Registered %s' % sensor)
                    self._sensor_dtos.append(sensor)
                except Exception:
                    logger.exception('Error registering sensor %s' % sensor)
        if self._config.get('ventilation', False):
            logger.info('Registering ventilation...')
            try:
                unit = self.connector.ventilation.register(external_id='111111',
                                                           name='Dummy',
                                                           amount_of_levels=3,
                                                           min_level=1,
                                                           max_level=3,
                                                           device_vendor='Vendor',
                                                           device_type='Type',
                                                           device_serial='type-111111')
                logger.info('Registered %s' % unit)
                self._ventilation_id = unit.external_id
                self.connector.ventilation.report_state(external_id=self._ventilation_id,
                                                        mode='automatic',
                                                        level=1,
                                                        remaining_time=None)
            except Exception:
                logger.exception('Error registering ventilation')
                self._ventilation_id = None
        else:
            self._ventilation_id = None
        # register a hot water unit
        if self._config.get('hot_water', False):
            logger.info('Registering hot water...')
            try:
                unit = self.connector.hot_water.register(
                        external_id="hotwater1",
                        name="boiler")
                logger.info('Registered %s' % unit)
                self._hot_water = unit
            except Exception:
                logger.exception('Error registering hot_water')
                self._hot_water = None

    def hot_water_publish_state(self):
        logger.info("publish hot_water state")
        steering_power = random.randint(0, 100)
        current_temperature = random.randint(0, 80)
        self.connector.hot_water.report_status(id=self._hot_water.id, steering_power=100, current_temperature=10)

    def hot_water_state(self, external_id, state):
        logger.info("set hot water of external_id {} with state {}".format(external_id, state))

    def hot_water_setpoint(self, external_id, setpoint):
        logger.info("set hot water of external_id {} to setpoint {}".format(external_id, setpoint))

    @hot_water_status(version=1)
    def hot_water_status(self, status):
        logger.info("new hot water status: {}".format(status))


    @background_task
    def loop(self):
        while True:
            try:
                for _ in range(30):
                    if self._wants_registration:
                        self._register_entities()
                        self._wants_registration = False
                    time.sleep(1)
            except Exception:
                logger.exception('Error while registrering entities')
            try:
                for sensor_dto in self._sensor_dtos:
                    range_min, range_max = self.STATUS_RANGES.get(sensor_dto.physical_quantity, (20, 25))
                    value = round(random.uniform(range_min, range_max), 1)
                    self.connector.sensor.report_state(sensor=sensor_dto,
                                                       value=value)
            except Exception:
                logger.exception('Error while reporting sensor state')
            try:
                self.hot_water_publish_state()
            except Exception:
                logger.exception('Error while reporting hot water state')
            try:
                if self._config.get('notification', False):
                    self.connector.notification.send(topic='dummy',
                                                     message='This is a test notification from the Dummy plugin')
                    self._config['notification'] = False  # Only send 1 notification
                    self.write_config(self._config)
            except Exception:
                logger.exception('Error while sending notification')

    def ventilation_set_auto(self, external_id):
        self.connector.ventilation.report_state(external_id=self._ventilation_id,
                                                mode='automatic',
                                                level=1,
                                                remaining_time=None)

    def ventilation_set_manual(self, external_id, level, timer):
        self.connector.ventilation.report_state(external_id=self._ventilation_id,
                                                mode='manual',
                                                level=level,
                                                remaining_time=timer)


    @staticmethod
    def handle_ventilation_status(event):
        logger.info('Received ventilation status from gateway: {0} {1} {2} {3}'.format(
            event.data['id'], event.data['mode'], event.data['level'], event.data['remaining_time']
        ))


    @staticmethod
    def handle_hot_water_status(event):
        logger.info('Received hot_water status from gateway: {0} {1} {2} {3} {4}'.format(
            event.data['id'], event.data['state'], event.data['setpoint'], event.data['steering_power'], event.data['current_temperature']
        ))

    @staticmethod
    def handle_sensor_status(event):
        logger.info('Received sensor status from gateway: {0} {1}'.format(
            event.data['id'], event.data['value']
        ))
