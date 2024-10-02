"""
Dummy plugin
"""

import json
import logging
import time
import six
from collections import deque
from .hotwater import HotWaterDummy
from .sensor import SensorDummy
from .ventilation import VentilationDummy
from .measurement_counter import MeasurementCounterDummy, MeasurementEnums

from plugins.base import (
    OMPluginBase,
    PluginConfigChecker,
    background_task,
    om_expose,
    ventilation_status,
    sensor_status,
    measurement_counter_status,
    hot_water_status,
    om_metric_receive,
    om_metric_data,
)

logger = logging.getLogger(__name__)


class Dummy(OMPluginBase):
    """
    Dummy plugin
    """

    name = "Dummy"
    version = "2.1.1"
    interfaces = [("config", "1.0")]

    default_config = {}

    def __init__(self, webinterface, connector):
        super(Dummy, self).__init__(webinterface=webinterface, connector=connector)
        logger.info("Starting Dummy plugin {0}...".format(Dummy.version))
        self.config_description = [
            {
                "name": "sensors",
                "type": "section",
                "description": "Add sensors here",
                "repeat": True,
                "min": 0,
                "content": [
                    {
                        "name": "name",
                        "type": "str",
                        "description": "The name for the sensor",
                    },
                    {
                        "name": "types",
                        "type": "section",
                        "repeat": True,
                        "min": 1,
                        "content": [
                            {
                                "name": "physical",
                                "type": "enum",
                                "choices": list(self.connector.sensor.Enums.UNIT_MAPPING.keys()),
                            },
                            {
                                "name": "unit",
                                "type": "enum",
                                "choices": list(set([item for sublist in self.connector.sensor.Enums.UNIT_MAPPING.values() for item in sublist])),
                            },
                        ],
                    },
                ],
            },
            {
                "name": "hot_water",
                "type": "bool",
                "description": "Register a dummy hot water unit",
            },
            {
                "name": "measurement_counters",
                "type": "section",
                "description": "Add measurement counters here",
                "repeat": True,
                "min": 0,
                "content": [
                    {
                        "name": "name",
                        "type": "str",
                        "description": "The name for the measurement counter",
                    },
                    {
                        "name": "type",
                        "type": "enum",
                        "choices": self.connector.measurement_counter.Enums.Types.list_values(),
                    },
                    {
                        "name": "category",
                        "type": "enum",
                        "choices": self.connector.measurement_counter.Enums.Categories.list_values(),
                    },
                ],
            },
            {
                "name": "ventilation",
                "type": "bool",
                "description": "Register a dummy ventilation unit",
            },
            {
                "name": "notification",
                "type": "bool",
                "description": "Publish a cloud notification",
            },
        ]
        self._config = self.read_config(Dummy.default_config)
        self._config_checker = PluginConfigChecker(self.config_description)

        self.connector.sensor.subscribe_status_event(
            self.handle_sensor_status, version=2
        )
        self.connector.ventilation.subscribe_status_event(
            self.handle_ventilation_status, version=2
        )
        self.connector.ventilation.attach_set_auto(self.ventilation_set_auto, version=1)
        self.connector.ventilation.attach_set_manual(
            self.ventilation_set_manual, version=1
        )
        self.connector.hot_water.subscribe_status_event(
            self.handle_hot_water_status, version=1
        )
        self.connector.hot_water.attach_set_state(
            self.handle_hot_water_set_state, version=1
        )
        self.connector.hot_water.attach_set_setpoint(
            self.handle_hot_water_set_setpoint, version=1
        )

        self.connector.measurement_counter.subscribe_status_event(
            self.handle_measurement_counter_status, version=2
        )

        self._metrics_queue = deque()
        self._wants_registration = True
        self._sensor_dtos = []
        self._mc_dtos = []
        self._sensor_dummies = {}
        self._mc_dummies = {}
        self._ventilation_dto = None
        self._ventilation_dummy = None
        self._hot_water_dto = None
        self._hot_water_dummy = None

        logger.info("Started Dummy plugin {0}".format(Dummy.version))

    @om_expose
    def get_config_description(self):
        logger.info("Fetching config description")
        return json.dumps(self.config_description)

    @om_expose
    def get_config(self):
        logger.info("Fetching configuration")
        return json.dumps(self._config)

    @om_expose
    def set_config(self, config):
        logger.info("Saving configuration...")
        data = json.loads(config)
        self._save_config(data)
        self._wants_registration = True
        logger.info("Saving configuration... Done")
        return json.dumps({"success": True})

    def _save_config(self, config):
        for key in config:
            if isinstance(config[key], six.string_types):
                config[key] = str(config[key])
        self._config_checker.check_config(config)
        self._config = config
        self.write_config(config)

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
                logger.exception("Error while registering entities")
            try:
                if self._config.get("notification", False):
                    self.connector.notification.send(
                        topic="dummy",
                        message="This is a test notification from the Dummy plugin",
                    )
                    self._config["notification"] = False  # Only send 1 notification
                    self.write_config(self._config)
            except Exception:
                logger.exception("Error while sending notification")

    def _register_entities(self):
        self._sensor_dtos = []
        sensors = self._config.get("sensors", [])
        logger.info("Registering sensors...")
        for sensor in sensors:
            name = sensor["name"]
            sensor_types = sensor["types"]
            for sensor_type in sensor_types:
                try:
                    external_id = f"dummy/{name}"
                    sensor_dto = self.connector.sensor.register(
                        external_id=external_id,
                        physical_quantity=sensor_type["physical"],
                        unit=sensor_type["unit"],
                        name=f"{name}-{sensor_type['physical']}",
                    )
                    logger.info("Registered %s" % sensor_dto)
                    self._sensor_dtos.append(sensor_dto)
                    sensor_dummy = self._sensor_dummies.get(sensor_dto.external_id)
                    if sensor_dummy is not None:
                        sensor_dummy.stop()
                    sensor_dummy = SensorDummy(
                        sensor_dto,
                        report_status=self.report_sensor_status,
                        update_interval=30,
                    )
                    self._sensor_dummies[sensor_dto.external_id] = sensor_dummy
                    sensor_dummy.start()
                except Exception:
                    logger.exception("Error registering sensor %s" % sensor)
        if self._config.get("ventilation", False):
            logger.info("Registering ventilation...")
            try:
                ventilation_dto = self.connector.ventilation.register(
                    external_id="111111",
                    name="Dummy",
                    amount_of_levels=3,
                    min_level=1,
                    max_level=3,
                    device_vendor="Vendor",
                    device_type="Type",
                    device_serial="type-111111",
                )
                logger.info("Registered %s" % ventilation_dto)
                self._ventilation_dto = ventilation_dto
                if self._ventilation_dummy is not None:
                    self._ventilation_dummy.stop()
                self._ventilation_dummy = VentilationDummy(
                    ventilation_dto, report_status=self.report_ventilation_status
                )
                self._ventilation_dummy.start()
            except Exception:
                logger.exception("Error registering ventilation")
                self._ventilation_dto = None
        else:
            self._ventilation_dto = None
        # register a hot water
        if self._config.get("hot_water", False):
            logger.info("Registering hot water...")
            try:
                hot_water_dto = self.connector.hot_water.register(
                    external_id="hotwater1", name="boiler", min_temp=30.0, max_temp=70.0
                )
                logger.info("Registered %s" % hot_water_dto)
                self._hot_water_dto = hot_water_dto
                if self._hot_water_dummy is not None:
                    self._hot_water_dummy.stop()
                self._hot_water_dummy = HotWaterDummy(
                    hot_water_dto, report_status=self.report_hot_water_status
                )
                self._hot_water_dummy.start()
            except Exception:
                logger.exception("Error registering hot_water")
                self._hot_water_dto = None
        else:
            self._hot_water_dto = None
        # register measurement counters
        mcs = self._config.get("measurement_counters", [])
        logger.info("Registering measurement counters...")
        for mc in mcs:
            mc_name = mc["name"]
            mc_type = MeasurementEnums.Type(mc["type"])
            mc_category = MeasurementEnums.Category(mc['category'])
            try:
                external_id = f"dummy/{mc_name}"
                mc_dto = self.connector.measurement_counter.register(
                    external_id=external_id,
                    name=f"{mc_name}",
                    type=mc_type,
                    category=mc_category,
                    has_realtime=True
                )
                logger.info("Registered %s" % mc_dto)
                self._mc_dtos.append(mc_dto)
                mc_dummy = self._mc_dummies.get(mc_dto.external_id)
                if mc_dummy is not None:
                    mc_dummy.stop()
                mc_dummy = MeasurementCounterDummy(
                    mc_dto,
                    report_status=self.report_mc_status,
                    update_interval=30
                )
                self._mc_dummies[mc_dto.external_id] = mc_dummy
                mc_dummy.start()
            except Exception:
                logger.exception("Error registering sensor %s" % mc)

    # sensors

    def report_sensor_status(self, sensor_dto, value):
        logger.info("publish sensor value for {}: {}".format(sensor_dto, value))
        self.connector.sensor.report_state(sensor=sensor_dto, value=value)

    @sensor_status(version=1)
    def sensor_status(self, status):
        logger.info("new sensor status from gateway: {}".format(status))

    @staticmethod
    def handle_sensor_status(event):
        logger.info(
            "Received sensor status from gateway: {0} {1}".format(
                event.data["id"], event.data["value"]
            )
        )

    # Measurement Counters
    def report_mc_status(self, mc_dto, total_consumed, total_injected, realtime):
        logger.info("publish measurementCounter value for {}: consumed = {}; injected = {}; realtime={}".format(mc_dto, total_consumed, total_injected, realtime))
        self.connector.measurement_counter.report_counter_state(measurement_counter=mc_dto, total_consumed=total_consumed, total_injected=total_injected)
        self.connector.measurement_counter.report_realtime_state(measurement_counter=mc_dto, value=realtime)

    @measurement_counter_status(version=1)
    def measurement_counter_status(self, status):
        logger.info("new measurement counter status from gateway: {}".format(status))

    @staticmethod
    def handle_measurement_counter_status(event):
        logger.info(
            "Received measurement status from gateway: {0} {1}".format(
                event.data["id"], event.data["value"]
            )
        )

    # ventilation units

    def report_ventilation_status(self, ventilation_dto, mode, level, remaining_time):
        logger.info(
            "publish ventilation state for {}: {} {} {}".format(
                ventilation_dto, mode, level, remaining_time
            )
        )
        self.connector.ventilation.report_status(
            ventilation=ventilation_dto,
            mode=mode,
            level=level,
            remaining_time=remaining_time,
        )

    def ventilation_set_auto(self, external_id):
        logger.info("set ventilation of external_id {} with auto".format(external_id))
        self._ventilation_dummy.set_auto()

    def ventilation_set_manual(self, external_id, level, timer):
        logger.info(
            "set ventilation of external_id {} with {} {}".format(
                external_id, level, timer
            )
        )
        self._ventilation_dummy.set_manual(level, timer)

    @ventilation_status(version=1)
    def ventilation_status(self, status):
        logger.info("new ventilation status from gateway: {}".format(status))

    @staticmethod
    def handle_ventilation_status(event):
        logger.info(
            "Received ventilation status from gateway: {0} {1} {2} {3}".format(
                event.data["id"],
                event.data["mode"],
                event.data["level"],
                event.data["remaining_time"],
            )
        )

    # hot water units

    def report_hot_water_status(
        self, hot_water_dto, steering_power, current_temperature, setpoint, state
    ):
        logger.info(
            "publish hot_water state for {}: {} {} {} {}".format(
                hot_water_dto, steering_power, current_temperature, setpoint, state
            )
        )
        self.connector.hot_water.report_status(
            hot_water=hot_water_dto,
            steering_power=steering_power,
            current_temperature=current_temperature,
            setpoint=setpoint,
            state=state,
        )

    def handle_hot_water_set_setpoint(self, external_id, setpoint):
        logger.info(
            "set hot water of external_id {} to setpoint {}".format(
                external_id, setpoint
            )
        )
        self._hot_water_dummy.set_setpoint(setpoint)

    def handle_hot_water_set_state(self, external_id, state):
        logger.info(
            "set hot water of external_id {} with state {}".format(external_id, state)
        )
        self._hot_water_dummy.set_state(state)

    @hot_water_status(version=1)
    def hot_water_status(self, status):
        logger.info("new hot water status from gateway: {}".format(status))

    @staticmethod
    def handle_hot_water_status(event):
        logger.info(
            "Received hot_water status from gateway: {0} {1} {2} {3} {4}".format(
                event.data["id"],
                event.data["state"],
                event.data["setpoint"],
                event.data["steering_power"],
                event.data["current_temperature"],
            )
        )
