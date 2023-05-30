import random
import time
from threading import Thread, Lock
import logging

logger = logging.getLogger(__name__)


class HotWaterDummy:
    def __init__(self, hot_water_dto, report_status, update_interval=5):
        self.hot_water_dto = hot_water_dto

        self.steering_power = 0
        self.current_temperature = self.hot_water_dto.min_temp
        self.setpoint = self.hot_water_dto.max_temp
        self.state = "on"

        self.report_status = report_status

        self.thread = Thread(target=self.simulation)
        self.update_interval = update_interval
        self._running = False
        self.lock = Lock()

    def start(self):
        logger.info("starting HotWaterDummy")
        self._running = True
        self.thread.start()

    def stop(self):
        logger.info("stopping HotWaterDummy")
        self._running = False

    def simulation(self):
        while self._running:
            changed = self.update_steering_power()
            changed |= self.update_current_temperature()
            if changed:
                self.report_status(
                    self.hot_water_dto,
                    self.steering_power,
                    self.current_temperature,
                    self.setpoint,
                    self.state,
                )
            time.sleep(self.update_interval)

    def set_state(self, state):
        with self.lock:
            self.state = state

    def set_setpoint(self, setpoint):
        with self.lock:
            self.setpoint = setpoint

    def update_steering_power(self):
        if self.state == "on":
            if self.current_temperature >= self.setpoint:
                new_steering_power = 0
            elif self.current_temperature >= self.setpoint - 10:
                new_steering_power = self.steering_power  # keep going
            else:
                new_steering_power = 100
            # self.steering_power = int(
            #     (self.setpoint - self.current_temperature) / (self.max_temp - self.min_temp) * 100.0)
        else:
            new_steering_power = 0
        changed = self.steering_power != new_steering_power
        with self.lock:
            self.steering_power = new_steering_power
        return changed

    def update_current_temperature(self):
        previous_current_temperature = self.current_temperature
        delta_t = (
            random.randint(0, 1)
            if (self.state == "on" and self.steering_power > 0)
            else random.randint(-1, 0)
        )
        with self.lock:
            self.current_temperature = max(
                self.hot_water_dto.min_temp,
                min(self.current_temperature + delta_t, self.hot_water_dto.max_temp),
            )
        return previous_current_temperature != self.current_temperature
