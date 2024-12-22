"""
HealthboxBoostOnInput plugin
"""

import json
import logging
import time
from unittest.mock import MagicMock
import requests
import six
from threading import Event

logger = logging.getLogger(__name__)

from plugins.base import (
    OMPluginBase,
    PluginConfigChecker,
    background_task,
    om_expose,
    input_status,
)

POLL_INTERVAL = 30  # seconds


class HealthboxBoostOnInput(OMPluginBase):
    """
    Healthbox 3 boost on input plugin
    """

    name = "HealthboxBoostOnInput"
    version = "0.1.0"
    interfaces = [("config", "1.0")]

    default_config = {}

    def __init__(self, webinterface, connector):
        super(HealthboxBoostOnInput, self).__init__(
            webinterface=webinterface, connector=connector
        )
        logger.info(
            "Starting HealthboxBoostOnInput plugin {0}...".format(
                HealthboxBoostOnInput.version
            )
        )
        self.config_description = [
            {
                "name": "healthbox_warranty",
                "type": "str",
                "description": "Healthbox 3 warranty number",
            },
            {
                "name": "config",
                "type": "section",
                "description": "-------------------------------",
                "repeat": True,
                "min": 1,
                "content": [
                    {
                        "name": "input_nr",
                        "type": "int",
                        "description": "the input number to listen on",
                    },
                    {
                        "name": "healthbox_roomnr",
                        "type": "int",
                        "description": "the room number to boost",
                    },
                    {
                        "name": "boost_level",
                        "type": "int",
                        "description": "the level to boost (%)",
                    },
                    {
                        "name": "timeout",
                        "type": "int",
                        "description": "how long the boost should last",
                    },
                ],
            },
        ]
        self._config = self.read_config(HealthboxBoostOnInput.default_config)
        self._config_checker = PluginConfigChecker(self.config_description)

        self._ip = None
        self._last_successful_network_discovery = 0
        self._wait_event = Event()
        self._boosts_activated = set()

        logger.info(
            "Started HealthboxBoostOnInput plugin {0}".format(
                HealthboxBoostOnInput.version
            )
        )

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
                config[key] = str(config[key]).strip()
        self._config_checker.check_config(config)
        self._config = config
        self.write_config(config)

    def get_healthbox_ip(self):
        if time.time() - self._last_successful_network_discovery < 300:
            # cache the result
            return self._ip

        try:
            devices = self.webinterface.network_discovery()["devices"]
            warranty = self._config.get("healthbox_warranty", "")
            device = next(
                filter(
                    lambda d: d["Device"] == "HEALTHBOX3"
                    and d["warranty_number"] == warranty,
                    devices,
                ),
                None,
            )
            if device is not None:
                if self._ip != device["IP"]:
                    logger.info(
                        f"Found Healthbox 3 device {device["warranty_number"]} - IP {device["IP"]}"
                    )
                    self._ip = device["IP"]
                return self._ip
        except Exception:
            logger.error("Network discovery failed!")

        return None

    def get_boost_status(self, room_id):
        ip = self.get_healthbox_ip()
        boost = requests.get(
            f"https://{ip}/v1/api/boost/{room_id}", verify=False
        ).json()
        return boost["enable"]

    def activate_boost(self, room_id, level, timeout):
        ip = self.get_healthbox_ip()
        json = {"enable": True, "level": level, "timeout": timeout}
        requests.put(
            f"https://{ip}/v1/api/boost/{room_id}", json=json, verify=False
        ).json()

    def stop_boost(self, room_id):
        ip = self.get_healthbox_ip()
        json = {"enable": False}
        requests.put(
            f"https://{ip}/v1/api/boost/{room_id}", json=json, verify=False
        ).json()

    def poll_inputs(self):
        if self._config.get("healthbox_warranty", ""):
            status = {
                s["id"]: s["status"]
                for s in self.webinterface.get_input_status()["status"]
            }
            for item in self._config.get("config", []):
                if status.get(item["input_nr"]) == 1:
                    # only activate boost once, not repeatedly
                    if not item["healthbox_roomnr"] in self._boosts_activated:
                        logger.info(
                            f"Activating boost on room {item["healthbox_roomnr"]}"
                        )
                        self.activate_boost(
                            item["healthbox_roomnr"],
                            item["boost_level"],
                            item["timeout"],
                        )
                        self._boosts_activated.add(item["healthbox_roomnr"])
                elif item["healthbox_roomnr"] in self._boosts_activated:
                    logger.info(f"Stopping boost on room {item["healthbox_roomnr"]}")
                    self.stop_boost(item["healthbox_roomnr"])
                    self._boosts_activated.remove(item["healthbox_roomnr"])

    @background_task
    def loop(self):
        while True:
            now = time.time()
            try:
                self.poll_inputs()
            except Exception:
                logger.exception("Error in task!")
            timeout = POLL_INTERVAL - ((time.time() - now) % POLL_INTERVAL)
            self._wait_event.wait(timeout=timeout)
            self._wait_event.clear()

    @input_status
    def input_status_changed(self, input_status):
        """When the inputs change, trigger the loop now"""
        self._wait_event.set()


if __name__ == "__main__":
    logging.basicConfig(level="INFO")

    # setup plumbing with the correct signatures
    from plugin_runtime.web import WebInterfaceDispatcher
    from plugin_runtime.connectors.connector import Connector
    from gateway.utilities.event_loop import EventLoop

    eventloop = EventLoop(name="plugin_event_loop")
    connector = Connector(
        forward_callback_actions=lambda *args, **kwargs: None,
        forward_status_event_subscriptions=lambda *args, **kwargs: None,
        event_loop=eventloop,
    )
    web_dispatcher = WebInterfaceDispatcher("HealthboxBoostOnInput")

    # replace by actual key for local development
    HealthboxBoostOnInput.read_config = MagicMock(
        return_value={
            "healthbox_warranty": "BLO026100001015",
            "config": [
                {
                    "input_nr": 0,
                    "healthbox_roomnr": 9,
                    "boost_level": 100,
                    "timeout": 24 * 60 * 60,
                }
            ],
        }
    )
    web_dispatcher.get_input_status = MagicMock(
        return_value={
            "success": True,
            "status": [
                {"id": 0, "status": 1},
                {"id": 1, "status": 0},
                {"id": 2, "status": 0},
                {"id": 3, "status": 0},
                {"id": 4, "status": 0},
                {"id": 5, "status": 0},
                {"id": 6, "status": 0},
                {"id": 7, "status": 0},
            ],
        }
    )
    web_dispatcher.network_discovery = MagicMock(
        return_value={
            "success": True,
            "devices": [
                {
                    "Description": "Healtbox 3.0",
                    "Device": "HEALTHBOX3",
                    "Firmwareversion": "2.3.1",
                    "IP": "192.168.0.135",
                    "MAC": "50:8c:b1:e4:4f:01",
                    "scope": "HEALTHBOX3",
                    "serial": "171207P0024",
                    "subtype": "",
                    "warranty_number": "BLO026100001015",
                }
            ],
        }
    )
    plugin = HealthboxBoostOnInput(webinterface=web_dispatcher, connector=connector)
    plugin.poll_inputs()
