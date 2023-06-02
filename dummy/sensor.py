import random
import time
from threading import Thread, Lock
import logging

logger = logging.getLogger(__name__)


class SensorDummy:
    STATUS_RANGES = {
        "temperature": (20, 25),
        "humidity": (0, 100),
        "brightness": (0, 100),
        "sound": (20, 120),
        "dust": (0, 50),
        "comfort_index": (0, 100),
        "aqi": (0, 100),
        "co2": (280, 2000),
        "voc": (0, 300),
        "electric_potential": (220, 240),
        "electric_current": (0, 16),
        "frequency": (47, 53),
        "energy": (0, 10**6),
        "power": (0, 10**4),
    }

    def __init__(self, sensor_dto, report_status, update_interval=5):
        self.sensor_dto = sensor_dto
        self.value = None
        self.report_status = report_status

        self.thread = Thread(target=self.simulation)
        self.update_interval = update_interval
        self._running = False
        self.lock = Lock()

    def start(self):
        logger.info("starting SensorDummy {}".format(self.sensor_dto))
        self._running = True
        self.thread.start()

    def stop(self):
        logger.info("stopping SensorDummy{}".format(self.sensor_dto))
        self._running = False

    def simulation(self):
        while self._running:
            changed = self.update_value()
            if changed:
                self.report_status(self.sensor_dto, self.value)
            time.sleep(self.update_interval)

    def update_value(self):
        previous_value = self.value
        range_min, range_max = SensorDummy.STATUS_RANGES.get(
            self.sensor_dto.physical_quantity, (20, 25)
        )
        if self.value is None:
            self.value = range_min + (range_max - range_min) / 2.0
        else:
            delta = (range_max - range_min) / 10.0
            new_value = self.value + round(random.uniform(-delta, delta), 1)
            self.value = min(max(range_min, new_value), range_max)
        return self.value != previous_value
