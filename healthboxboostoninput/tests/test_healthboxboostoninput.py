from unittest import TestCase
from unittest.mock import MagicMock, patch

from plugin_runtime.web import WebInterfaceDispatcher
from plugin_runtime.connectors.connector import Connector
from gateway.utilities.event_loop import EventLoop

from healthboxboostoninput.main import HealthboxBoostOnInput

import logging

logger = logging.getLogger(__name__)

class TestHealthboxBoostOnInput(TestCase):

    def setUp(self) -> None:
        eventloop = EventLoop(name='plugin_event_loop')
        connector = Connector(forward_callback_actions=lambda *args, **kwargs: None, forward_status_event_subscriptions=lambda *args, **kwargs: None, event_loop=eventloop)
        self.web_dispatcher = WebInterfaceDispatcher("HealthboxBoostOnInput")

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
        self.plugin = HealthboxBoostOnInput(webinterface=self.web_dispatcher, connector=connector)

    def test_poll_HealthboxBoostOnInput(self):
          # replace by actual key for local development
        self.web_dispatcher.get_input_status = MagicMock(
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
        self.web_dispatcher.network_discovery = MagicMock(
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

        self.plugin.activate_boost = MagicMock()
        self.plugin.poll_inputs()
        self.plugin.activate_boost.assert_any_call(9, 100, 24*60*60)


    def tearDown(self) -> None:
        pass
