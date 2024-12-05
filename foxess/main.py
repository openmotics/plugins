"""
FoxEss plugin
"""

import json
import logging
import time
import sys
from pathlib import Path
import six
from unittest.mock import MagicMock


logger = logging.getLogger(__name__)
try:
    from . import openapi as f
except ImportError:
    # try relative
    root = Path(__file__).parent.resolve()
    sys.path.insert(0, root)
    import openapi as f


try:
    from plugins.base import (
        OMPluginBase,
        PluginConfigChecker,
        background_task,
        om_expose,
        sensor_status,
        measurement_counter_status,
    )
except ImportError:
    """
    Construct a mock of the imports
    """

    class OMPluginBase:
        def __init__(self, webinterface, connector) -> None:
            self.connector = connector
            pass

        def read_config(self, config):
            return {}

    class PluginConfigChecker:
        def __init__(self, description) -> None:
            pass

        pass

    def om_expose(method=None, auth=True, content_type="application/json", version=1):
        def wrapper(_method):
            _method.om_expose = {
                "method": _method,
                "auth": auth,
                "content_type": content_type,
                "version": version,
            }
            return _method

        if method is not None:
            return wrapper(method)
        return wrapper

    def _fill_version(field, version, method=None):
        def wrapper(_method):
            setattr(_method, field, {"version": version})
            return _method

        if method is not None:
            return wrapper(method)
        return wrapper

    def background_task(method=None, version=1):
        return _fill_version(field="background_task", version=version, method=method)

    def sensor_status(method=None, version=1):
        return _fill_version(field="sensor_status", version=version, method=method)

    def measurement_counter_status(method=None, version=1):
        return _fill_version(
            field="measurement_counter_status", version=version, method=method
        )


POLL_INTERVAL = 60


class FoxEss(OMPluginBase):
    """
    FoxEss plugin
    """

    name = "FoxEss"
    version = "0.1.2"
    interfaces = [("config", "1.0")]

    default_config = {}

    def __init__(self, webinterface, connector):
        super(FoxEss, self).__init__(webinterface=webinterface, connector=connector)
        logger.info("Starting FoxEss plugin {0}...".format(FoxEss.version))
        self.config_description = [
            {
                "name": "api_key",
                "type": "str",
                "description": "API key of foxesscloud.com",
            },
            {
                "name": "device_sn",
                "type": "str",
                "description": "Device serial of foxesscloud.com (leave empty to use default)",
            },
        ]
        self._config = self.read_config(FoxEss.default_config)
        self._config_checker = PluginConfigChecker(self.config_description)

        self._mc_battery = (
            self.connector.measurement_counter.register_counter_electricity_wh(
                external_id="foxess/battery",
                name="Battery",
                type=connector.measurement_counter.Enums.Types.BATTERY,
                has_realtime=True,
            )
        )

        self._mc_solar = (
            self.connector.measurement_counter.register_counter_electricity_wh(
                external_id="foxess/solar",
                name="Solar",
                type=connector.measurement_counter.Enums.Types.SOLAR,
                has_realtime=True,
            )
        )
        self._battery_full_sent = False
        logger.info("Started FoxEss plugin {0}".format(FoxEss.version))

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
        logger.info("Saving configuration... Done")
        return json.dumps({"success": True})

    def _save_config(self, config):
        for key in config:
            if isinstance(config[key], six.string_types):
                config[key] = str(config[key])
        self._config_checker.check_config(config)
        self._config = config
        self.write_config(config)

    def get_timezone(self):
        try:
            return self.webinterface.get_timezone()["timezone"]
        except Exception:
            return "Europe/Brussels"

    def poll_foxess(self):
        f.api_key = self._config.get("api_key")
        if self._config.get("device_sn"):
            f.device_sn = self._config.get("device_sn")
        f.time_zone = self.get_timezone()
        f.residual_handling = 1
        site = f.get_site()
        if site is None:
            logger.error("Error calling Fox Ess API: do you have a valid token?")
            return

        f.get_logger()
        f.get_device()
        battery = f.get_battery()
        generation = f.get_generation()
        real = f.get_real()
        bat_consumption = battery["residual"]
        bat_charge = next(
            filter(lambda v: v["variable"] == "batChargePower", real), {}
        ).get("value")
        bat_discharge = next(
            filter(lambda v: v["variable"] == "batDischargePower", real), {}
        ).get("value")
        bat_real = bat_charge - bat_discharge
        solar_injection = -generation["cumulative"]
        solar_real = -next(
            filter(lambda v: v["variable"] == "pvPower", real), {}
        ).get("value")

        logger.info(f"Solar: tot {solar_injection} kWh, real {solar_real} kW")
        logger.info(f"Battery: energy {bat_consumption} kWh, real {bat_real} kW")
        self.report_mc_status(
            self._mc_battery, bat_consumption * 1000, 0, bat_real * 1000
        )
        self.report_mc_status(
            self._mc_solar, 0, solar_injection * 1000, solar_real * 1000
        )

        # send a notification when the battery is full
        if battery["soc"] > 99:
            if not self._battery_full_sent:
                self.connector.notification.send(
                    topic="FoxEss",
                    message="Battery is full again",
                )
                self._battery_full_sent = True
        else:
            self._battery_full_sent = False

    @background_task
    def loop(self):
        while True:
            now = time.time()
            try:
                self.poll_foxess()
            except Exception:
                logger.exception("Error while polling Fox Ess")
            time.sleep(POLL_INTERVAL - (time.time() - now) % POLL_INTERVAL)

    # Measurement Counters
    def report_mc_status(self, mc_dto, total_consumed, total_injected, realtime):
        logger.debug(
            "publish measurementCounter value for {}: consumed = {}; injected = {}; realtime={}".format(
                mc_dto, total_consumed, total_injected, realtime
            )
        )
        self.connector.measurement_counter.report_counter_state(
            measurement_counter=mc_dto,
            total_consumed=total_consumed,
            total_injected=total_injected,
        )
        self.connector.measurement_counter.report_realtime_state(
            measurement_counter=mc_dto, value=realtime
        )


if __name__ == "__main__":
    logging.basicConfig(level="INFO")

    # replace by actual key for local development
    FoxEss.read_config = MagicMock(
        return_value={"api_key": "<API_KEY>"}
    )
    plugin = FoxEss(MagicMock(), MagicMock())
    plugin.poll_foxess()
