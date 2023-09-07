import random
import time
from threading import Thread, Lock
import logging

logger = logging.getLogger(__name__)


class MeasurementCounterDummy:
    STATUS_RANGES = {
        "solar": (10, 15),
        "grid": (0, 100),
        "electric_vehicle": (0, 100),
        "hvac": (20, 120),
        "battery": (0, 50),
        "other": (0, 100),
    }

    CATEGORY_PARAMETER_ID_MAP = {
        "electric": [
            'peak_injection',
            'peak_consumption',
            'normal_injection',
            'normal_consumption',
        ],
        "water": ['water_volume'],
        "gas": ['gas_volume'],
    }

    def __init__(self, measurement_counter_dto, report_status, update_interval=5):
        self.measurement_counter_dto = measurement_counter_dto
        self.values = {k: 0 for k in MeasurementCounterDummy.CATEGORY_PARAMETER_ID_MAP[self.measurement_counter_dto.category]}
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
                changed = self.update_value()
                if changed:
                    for param_id, value in self.values.items():
                        logger.info("Report change: MeasurementCounter [{}]: value: [{}] = {}".format(self.measurement_counter_dto.name, param_id, value))
                        self.report_status(self.measurement_counter_dto, param_id, value)
            except Exception:
                logger.exception("An error in updating the measurement_counter simulation occurred")
            time.sleep(self.update_interval)

    def update_value(self):
        for key, value in self.values.items():
            range_min, range_max = MeasurementCounterDummy.STATUS_RANGES.get(
                self.measurement_counter_dto.type, (20, 25)
            )
            offset = random.randint(range_min, range_max)
            value += offset
            self.values[key] = value
        return True
