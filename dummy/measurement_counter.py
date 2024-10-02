from enum import Enum
import random
import time
from threading import Thread, Lock
import logging

logger = logging.getLogger(__name__)


class ExtendedEnum(Enum):
    @classmethod
    def list_values(cls):
        return list(map(lambda x: x.value, cls))
    
    
class MeasurementEnums(object):
    class Category(ExtendedEnum):
        ELECTRIC = 'electric'
        HEAT = 'heat'
        WATER = 'water'
        GAS = 'gas'


    class Type(ExtendedEnum):
        GRID = 'grid'
        SOLAR = 'solar'
        BATTERY = 'battery'
        ELECTRIC_VEHICLE = 'electric_vehicle'
        HEATPUMP = 'heatpump'
        VENTILATION = 'ventilation'
        OVEN = 'oven'
        STOVE = 'stove'
        FRIDGE = 'fridge'
        FREEZER = 'freezer'
        KITCHEN_APPLIANCES = 'kitchen_appliances'
        DISHWASHER = 'dishwasher'
        WASHER = 'washer'
        DRYER = 'dryer'
        BOILER = 'boiler'
        LIGHTS = 'lights'
        WALL_OUTLETS = 'wall_outlets'
        OTHER = 'other'


    class CallbackAction(object):
        REGISTER = "register"
        REPORT_COUNTER_STATUS = "report_counter_status"
        REPORT_REALTIME_STATUS = "report_realtime_status"


class MeasurementCounterDummy:
    STATUS_RANGES = {
        "solar": (10, 15),
        "grid": (0, 100),
        "electric_vehicle": (0, 100),
        "hvac": (20, 120),
        "battery": (0, 50),
        "other": (0, 100),
    }

    CATEGORY_VALUE_MAP = {
        "electric": [
            'total_consumed',
            'total_injected',
            'realtime'
        ],
        "water": ['total_consumed', 'realtime'],
        "gas": ['total_consumed', 'realtime'],
    }

    def __init__(self, measurement_counter_dto, report_status, update_interval=5):
        self.measurement_counter_dto = measurement_counter_dto
        self.values = {k: 0 for k in MeasurementCounterDummy.CATEGORY_VALUE_MAP[self.measurement_counter_dto.category]}
        self.report_status = report_status

        self.thread = Thread(target=self.simulation)
        self.update_interval = update_interval
        self._running = False
        self.lock = Lock()

    def start(self):
        logger.info("starting MeasurementCounter Dummy {}".format(self.measurement_counter_dto))
        self._running = True
        self.thread.start()

    def stop(self):
        logger.info("stopping MeasurementCounter Dummy{}".format(self.measurement_counter_dto))
        self._running = False

    def simulation(self):
        while self._running:
            try:
                changed = self.update_values()
                if changed:
                    consumed = self.values.get('total_consumed', 0)
                    injected = self.values.get('total_injected', 0)
                    realtime = self.values.get('realtime', 0)
                    # logger.info("Report change: MeasurementCounter [{}]: consumed = {}; injected = {}; realtime = {}".format(self.measurement_counter_dto.name, consumed, injected, realtime))
                    self.report_status(self.measurement_counter_dto, consumed, injected, realtime)
            except Exception:
                logger.exception("An error in updating the measurement_counter simulation occurred")
            time.sleep(self.update_interval)

    def update_values(self):
        for key, value in self.values.items():
            if key != 'realtime':
                range_min, range_max = MeasurementCounterDummy.STATUS_RANGES.get(
                    self.measurement_counter_dto.type, (20, 25)
                )
                offset = random.randint(range_min, range_max)
                value += offset
                self.values[key] = value
            else:
                range_min, range_max = MeasurementCounterDummy.STATUS_RANGES.get(
                    self.measurement_counter_dto.type, (20, 25)
                )
                value = random.randint(range_min, range_max)
                self.values[key] = value
        return True
