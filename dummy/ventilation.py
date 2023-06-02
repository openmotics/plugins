import random
import time
from threading import Thread, Lock
import logging

logger = logging.getLogger(__name__)


class VentilationDummy:
    def __init__(self, ventilation_dto, report_status, update_interval=5):
        self.ventilation_dto = ventilation_dto

        self.mode = "auto"
        self.level = self.ventilation_dto.min_level
        self.remaining_time = None
        self._expiry = None

        self.report_status = report_status

        self.thread = Thread(target=self.simulation)
        self.update_interval = update_interval
        self._running = False
        self.lock = Lock()

    def start(self):
        logger.info("starting VentilationDummy {}".format(self.ventilation_dto))
        self._running = True
        self.thread.start()

    def stop(self):
        logger.info("stopping VentilationDummy {}".format(self.ventilation_dto))
        self._running = False

    def simulation(self):
        while self._running:
            changed = self.update()
            if changed:
                self.report_status(
                    self.ventilation_dto, self.mode, self.level, self.remaining_time
                )
            time.sleep(self.update_interval)

    def set_auto(self):
        with self.lock:
            self.mode = "auto"

    def set_manual(self, level, timer):
        with self.lock:
            self.mode = "manual"
            self.level = level
            self._expiry = time.time() + timer

    def update(self):
        if self.mode == "auto":
            new_remaining_time = None
            new_expiry = None
            new_mode = self.mode
            new_level = random.randint(
                self.ventilation_dto.min_level, self.ventilation_dto.max_level
            )
        else:
            now = time.time()
            new_remaining_time = (
                self._expiry - now if self._expiry and now <= self._expiry else None
            )
            if new_remaining_time >= 0:
                new_expiry = self._expiry
                new_mode = self.mode
            else:
                new_expiry = None
                new_mode = "auto"
            new_level = self.level
        changed = (
            self.remaining_time != new_remaining_time
            or self._expiry != new_expiry
            or self.mode != new_mode
            or self.level != new_level
        )
        with self.lock:
            self.remaining_time = new_remaining_time
            self._expiry = new_expiry
            self.mode = new_mode
            self.level = new_level
        return changed
