"""
A plugin to let two Gateways work together
"""

import six
import copy
import time
import requests
import json
from plugins.base import om_expose, output_status, OMPluginBase, PluginConfigChecker, background_task
from threading import Thread
import logging

logger = logging.getLogger(__name__)


class Syncer(OMPluginBase):
    """
    A syncer plugin to let a GW work together with n other GWs. Depending on the config, this GW will follow/set values
    (shutters, outputs, sensors) of other linked GWs.
    """

    name = 'Syncer'
    version = '0.0.7'
    interfaces = [('config', '1.0')]

    config_description = [{
        'name': 'local_name',
        'type': 'str',
        'description': 'Optional name field of the local GW.'
    },
        {
            'name': 'polling_interval',
            'type': 'int',
            'description': 'Interval (in seconds) to check remote sensor changes. (default 60)'
        },
        {
            'name': 'gateways',
            'type': 'section',
            'description': 'Other Gateways to sync.',
            'repeat': True,
            'min': 1,
            'content': [{
                'name': 'gateway_ip',
                'type': 'str',
                'description': 'The IP address of the other Gateway.'
            },
                {
                    'name': 'remote_name',
                    'type': 'str',
                    'description': 'Optional name field of the remote GW.'
                },
                {
                    'name': 'username',
                    'type': 'str',
                    'description': 'The (local) username for the other Gateway.'
                },
                {
                    'name': 'password',
                    'type': 'str',
                    'description': 'The (local) password for the other Gateway.'
                },
                {
                    'name': 'sensors',
                    'type': 'section',
                    'description': "Mapping between local sensors and remote sensors. \nThe "
                                   "remote sensor should exist.\n Remote updates local.",
                    'repeat': True,
                    'min': 0,
                    'content': [
                        {
                            'name': 'remote_sensor_id',
                            'type': 'int'
                        }
                    ]
                },
                {
                    'name': 'outputs',
                    'type': 'section',
                    'description': 'Mapping between local outputs and remote outputs.\nLocal updates remote.',
                    'repeat': True,
                    'min': 0,
                    'content': [{
                        'name': 'local_output_id',
                        'type': 'int'
                    },
                        {
                            'name': 'remote_output_id',
                            'type': 'int'
                        }]
                },
                {
                    'name': 'shutters',
                    'type': 'section',
                    'description': 'Mapping between local shutters and remote shutter. \nLocal updates remote.',
                    'repeat': True,
                    'min': 0,
                    'content': [{
                        'name': 'local_shutter_id',
                        'type': 'int'
                    },
                        {
                            'name': 'remote_shutter_id',
                            'type': 'int'
                        },
                        {
                            'name': 'is_shutter_group',
                            'type': 'bool',
                            'description': 'True => remote_shutter_id refers to the id of a shutter group\nFalse => remote_shutter_id refers to the id of a shutter (default False)'
                        },
                        {
                            'name': 'reversed',
                            'type': 'bool',
                            'description': 'True => up=up, down=down\nFalse => up=down, down=up (default True)'
                        }]
                }]
        }]

    default_config = {
        "polling_interval": 60
    }

    def __init__(self, webinterface, connector):
        super(Syncer, self).__init__(webinterface=webinterface, connector=connector)
        logger.info('Starting Syncer plugin...')

        self._config = self.read_config(Syncer.default_config)
        self._config_checker = PluginConfigChecker(Syncer.config_description)

        self._polling_interval = 60
        self._gateways = {}
        self._name = ''
        self._output_mapping = {}
        self._shutter_mapping = {}
        self._enabled = False
        thread = Thread(target=self._process_config)
        thread.start()

        self.connector.output.subscribe_status_event(handler=self.handle_output_status, version=2)
        self.connector.shutter.subscribe_status_event(handler=self.handle_shutter_status, version=2)

        logger.info("Started Syncer plugin")

    def _process_config(self):
        self._enabled = False
        self._polling_interval = self._config.get('polling_interval', 60)
        self._name = self._config.get('local_name', '')
        self._gateways = {}
        output_mapping = {}
        shutter_mapping = {}
        _enabled = False
        for gateway in self._config.get('gateways', ''):

            ip = gateway.get('gateway_ip', '')
            username = gateway.get('username', '')
            password = gateway.get('password', '')

            gw_name = gateway.get('remote_name')

            if gw_name in ['', None]:
                gw_name = ip


            headers = {
                'X-Requested-With': 'OpenMotics plugin: Syncer'
            }
            endpoint = 'https://{0}'.format(ip)

            enabled = '' not in [ip, username, password]
            # If one GW is enabled, then the plugin will be enabled as well. But this is done after gathering all the
            # config of the other GWs.
            if enabled:
                _enabled = True
            self._gateways[ip] = {
                'ip': ip,
                'name': gw_name,
                'username': username,
                'password': password,
                'headers': headers,
                'endpoint': endpoint,
                'enabled': enabled
            }
            try:
                self._call_remote("get_status", self._gateways[ip])
            except Exception as ex:
                logger.info(f"Could not connect to GW {ip}: {ex}")

            if 'sensors' in gateway:
                self.process_sensor_config(gateway)
            if 'outputs' in gateway:
                output_mapping = self.process_output_config(gateway, output_mapping)
            if 'shutters' in gateway:
                shutter_mapping = self.process_shutter_config(gateway, shutter_mapping)

        self._output_mapping = output_mapping
        logger.debug(f"Output  mapping: {self._output_mapping}")
        self._shutter_mapping = shutter_mapping
        logger.debug(f"Shutter mapping: {self._shutter_mapping}")
        _gateways = copy.deepcopy(self._gateways)
        for gateway in _gateways.values():
            gateway.pop("headers")
        logger.debug(f"Gateways: {_gateways}")
        del _gateways

        self._enabled = _enabled
        logger.info('Syncer is {0}'.format('enabled' if self._enabled else 'disabled'))

    def process_sensor_config(self, gateway):
        ip = gateway.get('gateway_ip')
        gw_name = gateway.get('name')
        remote_sensor_conf = self._call_remote('get_sensor_configurations', self._gateways[ip]).get('config')

        # Specific for each remote GW as this is remote 2 local. A loop over every remote GW will occur and this
        # will give our local sensor_dto if a value has changed.
        sensor_mapping = {}
        for entry in gateway.get('sensors', []):
            try:
                remote_sensor_id = entry.get('remote_sensor_id', -1)
                if remote_sensor_id < 0:
                    raise RuntimeError("Please give valid sensor ids")
                external_id = f"syncer/{ip}/{remote_sensor_id}"
                for remote_sensor in remote_sensor_conf:
                    if remote_sensor.get('id') == remote_sensor_id:
                        sensor = self.connector.sensor.register(external_id=external_id,
                                                                physical_quantity=remote_sensor.get(
                                                                    'physical_quantity'),
                                                                unit=remote_sensor.get('unit'),
                                                                name=f"{gw_name}/{remote_sensor.get('name')}")
                        sensor_mapping[remote_sensor_id] = sensor
            except Exception as ex:
                logger.exception(f'Could not load sensor mapping for GW with ip {ip}: {ex}')
        self._gateways[ip]["sensor_mapping"] = sensor_mapping

    def process_output_config(self, gateway, output_mapping):
        ip = gateway.get('gateway_ip')
        remote_output_conf = self._call_remote('get_output_configurations', self._gateways[ip]).get('config')

        # Global output_mapping variable because this is local 2 remote, thus if local output changes -> mapping to
        # remote outputs will happen. One specific local output changes to different remote output changes
        local_output_conf = json.loads(self.webinterface.get_output_configurations()).get('config')

        for entry in gateway.get('outputs', []):
            try:
                # Organise local output data and their mapping with one or more remote outputs by making use of a dict
                local_id = int(entry.get('local_output_id', -1))
                remote_id = int(entry.get('remote_output_id', -1))
                if local_id < 0 or remote_id < 0:
                    raise RuntimeError("Please give valid output ids")
                if local_output_conf[local_id].get("type") == 127:
                    raise RuntimeError(
                        f"Skipped because {local_id} is a shutter, please include it in the shutter config instead")

                state = json.loads(self.webinterface.get_output_status()).get("status")[local_id]
                config = local_output_conf[local_id]
                if local_id not in output_mapping.keys():
                    output_mapping[local_id] = {
                        'remote_outputs': [],
                        'config': config,
                        'state': state
                    }
                local_name = config.get('name') if config.get("name") != "" else local_id

                output_mapping[local_id]['remote_outputs'].append({
                    'remote': remote_id,
                    'gw': ip,
                    'name': f"{self._name}/{local_name}"
                })

            except Exception as ex:
                logger.exception(f'Could not load output mapping for GW with ip {ip}: {ex}')
                continue

            try:
                self.update_remote_output_config_and_state(ip, remote_id, state, remote_output_conf=remote_output_conf,
                                                           local_output_name=local_name)
            except Exception as ex:
                logger.exception(f"Error while updating remote output config and state: {ex}")
                continue

        return output_mapping

    def process_shutter_config(self, gateway, shutter_mapping):
        ip = gateway.get("gateway_ip")
        remote_shutter_conf = self._call_remote('get_shutter_configurations', self._gateways[ip]).get('config')

        # Global shutter mapping
        local_shutter_confs = json.loads(self.webinterface.get_shutter_configurations()).get('config')
        local_output_conf = json.loads(self.webinterface.get_output_configurations()).get('config')

        for entry in gateway.get('shutters', []):
            # Organise local shutter data and their mapping with one or more remote shutters by making use of a dict
            try:
                local_id = int(entry.get('local_shutter_id', -1))
                remote_id = int(entry.get('remote_shutter_id', -1))
                is_shutter_group = bool(entry.get('is_shutter_group', False))
                if local_id < 0 or remote_id < 0:
                    raise RuntimeError("Please give valid shutter ids")
                if local_output_conf[local_id * 2].get("type") != 127 or local_output_conf[local_id * 2 + 1].get(
                        "type") != 127:
                    raise RuntimeError(
                        f"Skipped because {local_id} is not a shutter, please include it in the output config instead")

                config = local_shutter_confs[local_id]
                local_state = json.loads(self.webinterface.get_shutter_status()).get("status")[local_id]
                if local_id not in shutter_mapping.keys():
                    shutter_mapping[local_id] = {
                        'remote_shutters': [],
                        'config': config,
                        'state': local_state
                    }

                local_name = config.get("name") if config.get("name") != "" else local_id

                shutter_mapping[local_id]['remote_shutters'].append({
                    'remote': remote_id,
                    'gw': ip,
                    'name': f"{self._name}/{local_name}",
                    'reversed': entry.get("reversed"),
                    'is_shutter_group': is_shutter_group
                })
            except Exception as ex:
                logger.exception(f'Could not load shutter mapping for GW with ip {ip}: {ex}')
                continue

            try:
                self.update_remote_shutter_config_and_state(ip, local_name, remote_shutter_conf, remote_id,
                                                            is_shutter_group, local_state, entry.get("reverse"))
            except Exception as ex:
                logger.exception(f"Error while updating remote shutter config and state: {ex}")
                continue

        return shutter_mapping

    def update_remote_output_config_and_state(self, ip, remote_id, state, state_only=False, remote_output_conf=None, local_output_name=None):
        # Set configuration and state of remote output according to local output
        if not state_only:
            try:
                old_name = remote_output_conf[remote_id]['name']
                if ' (also controlled by syncer plugin ' in old_name:
                    old_name = old_name.split(' (also controlled by syncer plugin ')[0]
                remote_output_conf[remote_id][
                    'name'] = f"{old_name} (also controlled by syncer plugin {self._name}/{local_output_name})"
                self._call_remote(f"set_output_configuration?config={json.dumps(remote_output_conf[remote_id])}",
                                  gateway=self._gateways[ip])
            except Exception as ex:
                raise RuntimeError(f'Could not set configuration of remote output {ip}/{remote_id}: {ex}')
        try:
            self._call_remote(api_call="set_output", params={
                "id": remote_id,
                "is_on": state.get('status'),
                "dimmer": state.get('dimmer', ""),
                "timer": state.get('ctimer', "")
            }, gateway=self._gateways[ip])
            logger.info(f"Updated remote output {remote_id} on GW {self._gateways[ip].get('name')} to {'on' if state.get('status') == 1 else 'off'} {'(' + str(state.get('dimmer')) + '%)' if state.get('dimmer') != '' else ''}")
        except Exception as ex:
            raise RuntimeError(f"Could not set state of remote output {self._gateways[ip].get('name')}/{remote_id}: {ex}")

    def update_remote_shutter_config_and_state(self, ip, local_name, remote_shutter_conf, remote_id, is_shutter_group, local_state, reverse):
        self.update_remote_shutter_config(ip, remote_shutter_conf=remote_shutter_conf, local_shutter_name=local_name, remote_id=remote_id, is_shutter_group=is_shutter_group)
        self.update_remote_shutter_state(ip, remote_id, local_state, reverse, is_shutter_group)

    def update_remote_shutter_config(self, ip, remote_shutter_conf, local_shutter_name, remote_id, is_shutter_group):
        # Set configuration of remote shutter according to local shutter
        try:
            if is_shutter_group:
                shutters_to_rename = []
                for shutter in remote_shutter_conf:
                    if shutter.get("group_1") == remote_id or shutter.get("group_2") == remote_id:
                        shutters_to_rename.append(shutter)
            else:
                shutters_to_rename = [remote_shutter_conf[remote_id]]

            for shutter in shutters_to_rename:
                old_name = shutter.get('name')
                if ' (also controlled by syncer plugin ' in old_name:
                    old_name = old_name.split(' (also controlled by syncer plugin ')[0]
                remote_shutter_conf[shutter.get("id")][
                    'name'] = f"{old_name} (also controlled by syncer plugin {self._name}/{local_shutter_name})"
                self._call_remote(
                    f"set_shutter_configuration?config={json.dumps(remote_shutter_conf[shutter.get('id')])}",
                    gateway=self._gateways[ip])
        except Exception as ex:
            raise RuntimeError(
                f'Could not set configuration remote shutter{"group" if is_shutter_group else ""} {ip}/{remote_id}: {ex}')

    def update_remote_shutter_state(self, ip, remote_id, state, reverse, is_shutter_group):
        try:
            do_call = True
            if state == "stopped":
                remote_state = "stop"
            elif state == "going_up":
                remote_state = "up" if not reverse else "down"
            elif state == "going_down":
                remote_state = "up" if reverse else "down"
            else:
                remote_state = ""
                do_call = False

            if is_shutter_group:
                group = "group_"
            else:
                group = ""

            if do_call:
                self._call_remote(api_call=f"do_shutter_{group}{remote_state}", params={
                    "id": remote_id
                }, gateway=self._gateways[ip])
            logger.info(f"Updated remote shutter{group[:-1]} {remote_id} on GW {self._gateways[ip].get('name')} to {remote_state}")
        except Exception as ex:
            raise RuntimeError(
                f"Could not set state of remote shutter{'group' if is_shutter_group else ''} {self._gateways[ip].get('name')}/{remote_id}: {ex}")

    @background_task
    def run(self):
        while True:
            if not self._enabled:
                time.sleep(30)
                continue
            try:
                # Sync sensor values:
                for gateway in self._gateways.values():
                    sensor_mapping = gateway.get('sensor_mapping')
                    if sensor_mapping == {}:
                        continue
                    sensor_status = self._call_remote('get_sensor_status', gateway).get('status')
                    for sensor in sensor_status:
                        sensor_tdo = sensor_mapping.get(sensor.get('id'), None)
                        if sensor_tdo is None:
                            continue
                        self.connector.sensor.report_state(sensor=sensor_tdo,
                                                           value=sensor.get('value'))
                        logger.info(
                            f"Updated {sensor_tdo.name} with value {sensor.get('value')} from remote sensor ({gateway.get('ip')}) with id {sensor.get('id')}")
            except Exception as ex:
                logger.exception('Error while syncing sensors: {0}'.format(ex))
            time.sleep(self._polling_interval)

    def handle_shutter_status(self, minimal_event, full_event):
        if not self._enabled:
            return
        for key, value in self._shutter_mapping.items():
            if value.get('state') != minimal_event[key]:
                state = minimal_event[key]
                self._shutter_mapping[key]['state'] = state
                logger.info(f"Shutter change detected: {key} {state}")
                logger.debug(f"Updating remote shutters... {value.get('remote_shutters')}")
                try:
                    for remote_shutter in value.get('remote_shutters'):
                        ip = remote_shutter.get('gw')
                        remote_id = remote_shutter.get('remote')
                        reverse = remote_shutter.get('reversed')
                        is_shutter_group = remote_shutter.get('is_shutter_group')
                        self.update_remote_shutter_state(ip=ip, remote_id=remote_id, state=state, reverse=reverse, is_shutter_group=is_shutter_group)
                except Exception as ex:
                    logger.exception(f"Error processing shutter event {state} of shutter {key}: {ex}")

    def handle_output_status(self, event):
        if not self._enabled or event.get('id') not in self._output_mapping:
            return
        local_id = event.get('id')
        state = {'status': event.get('status').get('on'),
                 'dimmer': event.get('status').get('value', "")}

        self._output_mapping[local_id]["state"] = state
        remote_outputs = self._output_mapping.get(local_id).get('remote_outputs')
        logger.info(f"Output change detected: {local_id} {'on' if state.get('status') else 'off'} {'(' + str(state.get('dimmer')) + '%)' if state.get('dimmer') != '' else ''}")
        logger.debug(f"Updating remote outputs... {remote_outputs}")

        try:
            for remote_output in remote_outputs:
                ip = remote_output.get('gw')
                remote_id = remote_output.get('remote')
                self.update_remote_output_config_and_state(ip=ip, remote_id=remote_id, state=state, state_only=True)
        except Exception as ex:
            logger.exception(f"Error processing output event {event}: {ex}")

    def _call_remote(self, api_call, gateway, params=None, method="GET"):
        # TODO: If there's an invalid_token error, call self._login() and try this call again
        retries = 0
        while retries < 3:
            try:
                if gateway.get("headers", {}).get("Authorization") is None:
                    self._login(gateway)
                response = requests.request(method=method,
                                            url=f"{gateway.get('endpoint')}/{api_call}",
                                            params=params,
                                            verify=False,
                                            headers=gateway.get('headers'))
                response_data = json.loads(response.text)
                if response_data.get('success', False) is False:
                    if response_data.get('msg') == 'invalid_token':
                        logger.debug('Token expired')
                        gateway["headers"]["Authorization"] = None
                        retries += 1
                        continue
                    else:
                        raise RuntimeError('Could not execute API call {0}: {1}'.format(api_call, response_data.get('msg',
                                                                                                             'Unknown error')))
                return response_data
            except Exception as ex:
                logger.exception('Unexpected error during API call {0}: {1}'.format(api_call, ex))
                return None

    def _login(self, gateway):
        try:
            response = requests.get(f"{gateway.get('endpoint')}/login",
                                    params={
                                        'username': gateway.get("username"),
                                        'password': gateway.get("password"),
                                        'accept_terms': '1',
                                        'timeout': 60 * 60 * 24 * 30
                                    },
                                    verify=False,
                                    headers=gateway.get("headers"))
            response_data = json.loads(response.text)
            if response_data.get('success', False) is False:
                logger.error(f"Could not login to {gateway.get('ip')}: {response_data.get('msg', 'Unknown error')}")
            else:
                token = response_data.get('token')
                gateway["headers"]['Authorization'] = 'Bearer {0}'.format(token)
        except Exception as ex:
            logger.exception('Unexpected error during login: {0}'.format(ex))

    @om_expose
    def get_config_description(self):
        return json.dumps(Syncer.config_description)

    @om_expose
    def get_config(self):
        return json.dumps(self._config)

    @om_expose
    def set_config(self, config):
        logger.info("Saving configuration")
        config = json.loads(config)
        for key in config:
            if isinstance(config[key], six.string_types):
                config[key] = str(config[key])
        self._config_checker.check_config(config)
        self._config = config
        thread = Thread(target=self._process_config)
        thread.start()
        self.write_config(config)
        return json.dumps({
            'success': True
        })
