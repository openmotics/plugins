"""
A Hue plugin, for controlling lights connected to your Hue Bridge
"""

import time
import requests
import simplejson as json
from threading import Thread
from plugins.base import om_expose, output_status, OMPluginBase, PluginConfigChecker, background_task


class Hue(OMPluginBase):

    name = 'Hue'
    version = '1.0.0'
    interfaces = [('config', '1.0')]

    config_description = [{'name': 'api_url',
                           'type': 'str',
                           'description': 'The API URL of the Hue Bridge device. E.g. http://192.168.1.2/api'},
                          {'name': 'username',
                           'type': 'str',
                           'description': 'Hue Bridge generated username.'},
                          {'name': 'poll_frequency',
                           'type': 'int',
                           'description': 'The frequency used to pull the status of all lights from the Hue bridge in seconds (0 means never)'},
                          {'name': 'output_mapping',
                           'type': 'section',
                           'description': 'Mapping between OpenMotics Virtual Outputs/Dimmers and Hue Outputs',
                           'repeat': True, 'min': 0,
                           'content': [{'name': 'output_id', 'type': 'int'},
                                       {'name': 'hue_output_id', 'type': 'int'}]}]

    default_config = {'api_url': 'http://hue/api', 'username': '', 'poll_frequency': 60}

    def __init__(self, webinterface, logger):
        super(Hue, self).__init__(webinterface, logger)
        self.logger('Starting Hue plugin...')

        self._config = self.read_config(Hue.default_config)
        self._config_checker = PluginConfigChecker(Hue.config_description)

        self._read_config()

        self._previous_output_state = {}

        self.logger("Hue plugin started")

    def _read_config(self):
        self._api_url = self._config['api_url']
        self._output_mapping = self._config.get('output_mapping', [])
        self._output = self._create_output_object()
        self._hue = self._create_hue_object()
        self._username = self._config['username']
        self._poll_frequency = self._config['poll_frequency']

        self._endpoint = '{0}/{1}/{{0}}'.format(self._api_url, self._username)

        self._enabled = self._api_url != '' and self._username != ''
        self.logger('Hue is {0}'.format('enabled' if self._enabled else 'disabled'))

    def _create_output_object(self):
        # create an object with the OM output IDs as the keys and hue light IDs as the values
        output_object = {}
        for entry in self._output_mapping:
            output_object[entry['output_id']] = entry['hue_output_id']
        return output_object

    def _create_hue_object(self):
        # create an object with the hue light IDs as the keys and OM output IDs as the values
        hue_object = {}
        for entry in self._output_mapping:
            hue_object[entry['hue_output_id']] = entry['output_id']
        return hue_object

    @output_status
    def output_status(self, status):
        if self._enabled is True:
            try:
                current_output_state = {}
                for (output_id, dimmer_level) in status:
                    hue_light_id = self._output.get(output_id)
                    if hue_light_id is not None:
                        key = '{0}_{1}'.format(output_id, hue_light_id)
                        current_output_state[key] = dimmer_level
                        previous_dimmer_level = self._previous_output_state.get(key, 0)
                        if dimmer_level != previous_dimmer_level:
                            self.logger('Dimming light {0} from {1} to {2}%'.format(key, previous_dimmer_level, dimmer_level))
                            thread = Thread(target=self._send, args=(hue_light_id, True, dimmer_level))
                            thread.start()
                        else:
                            self.logger('Light {0} unchanged at {1}%'.format(key, dimmer_level))
                    else:
                        self.logger('Ignoring light {0}, because it is not a Hue light'.format(output_id))
                for previous_key in self._previous_output_state.keys():
                    (output_id, hue_light_id) = previous_key.split('_')
                    if current_output_state.get(previous_key) is None:
                        self.logger('Switching light {0} OFF'.format(previous_key))
                        thread = Thread(target=self._send, args=(hue_light_id, False, self._previous_output_state.get(previous_key, 0)))
                        thread.start()
                    else:
                        self.logger('Light {0} was already on'.format(previous_key))
                self._previous_output_state = current_output_state
            except Exception as ex:
                self.logger('Error processing output_status event: {0}'.format(ex))

    def _send(self, hue_light_id, state, dimmer_level):
        try:
            old_state = self._getLightState(hue_light_id)
            brightness = self._dimmerLevelToBrightness(dimmer_level)
            if old_state != False:
                if old_state['state'].get('on', False):
                    if state:
                        # light was on in Hue and is still on in OM -> send brightness command to Hue
                        self._setLightState(hue_light_id, {'bri': brightness})
                    else:
                        # light was on in Hue and is now off in OM -> send off command to Hue 
                        self._setLightState(hue_light_id, {'on': False})
                else:
                    if state:
                        old_dimmer_level = self._brightnessToDimmerLevel(old_state['state']['bri'])
                        if old_dimmer_level == dimmer_level:
                            # light was off in Hue and is now on in OM with same dimmer level -> switch on command to Hue
                            self._setLightState(hue_light_id, {'on': True})
                        else:
                            # light was off in Hue and is now on in OM with different dimmer level -> switch on command to Hue and set brightness
                            brightness = self._dimmerLevelToBrightness(dimmer_level)
                            self._setLightState(hue_light_id, {'on': True, 'bri': brightness})
            else:
                self.logger('Unable to read current state for Hue light {0}'.format(hue_light_id))
            # sleep to avoid queueing the commands on the Hue bridge
            # time.sleep(1)
        except Exception as ex:
            self.logger('Error sending command to Hue light {0}: {1}'.format(hue_light_id, ex))

    def _getLightState(self, hue_light_id):
        try:
            start = time.time()
            response = requests.get(url=self._endpoint.format('lights/{0}').format(hue_light_id))
            if response.status_code is 200:
                hue_light = response.json()
                self.logger('Getting light state for Hue light {0} took {1}s'.format(hue_light_id, round(time.time() - start, 2)))
                return hue_light
            else:
                self.logger('Failed to pull state for light {0}'.format(hue_light_id))
                return False
        except Exception as ex:
            self.logger('Error while getting light state for Hue light {0}: {1}'.format(hue_light_id, ex))

    def _setLightState(self, hue_light_id, state):
        try:
            start = time.time()
            response = requests.put(url=self._endpoint.format('lights/{0}/state').format(hue_light_id), data=json.dumps(state))
            if response.status_code is 200:
                result = response.json()
                if result[0].get('success')is None:
                    self.logger('Setting light state for Hue light {0} returned unexpected result. Response: {1} ({2})'.format(hue_light_id, response.text, response.status_code))
                    return False
                self.logger('Setting light state for Hue light {0} took {1}s'.format(hue_light_id, round(time.time() - start, 2)))
                return True
            else:
                self.logger('Setting light state for Hue light {0} failed. Response: {1} ({2})'.format(response.text, response.status_code))
                return False
        except Exception as ex:
            self.logger('Error while setting light state for Hue light {0} to {1}: {2}'.format(hue_light_id, json.dumps(state), ex))

    def _getAllLightsState(self):
        self.logger('Pulling state for all lights from the Hue bridge')
        try:
            response = requests.get(url=self._endpoint.format('lights'))
            if response.status_code is 200:
                hue_lights = response.json()

                for output in self._output_mapping:
                    output_id = output['output_id']
                    hue_light_id = str(output['hue_output_id'])
                    hue_light = self._parseLightObject(hue_light_id, hue_lights[hue_light_id])
                    if hue_light.get('on', False):
                        result = json.loads(self.webinterface.set_output(None, str(output_id), 'true', str(hue_light['dimmer_level'])))
                    else:
                        result = json.loads(self.webinterface.set_output(None, str(output_id), 'false'))
                    if result['success'] is False:
                        self.logger('--> Error when updating output {0}: {1}'.format(output_id, result['msg']))
            else:
                self.logger('--> Failed to pull state for all lights')
        except Exception as ex:
            self.logger('--> Error while getting state for all Hue lights: {0}'.format(ex))

    def _parseLightObject(self, hue_light_id, hue_light_object):
        try:
            light = {'id': hue_light_id,
                     'name': hue_light_object['name'],
                     'on': hue_light_object['state'].get('on', False),
                     'brightness': hue_light_object['state'].get('bri', 254)}
            light['dimmer_level'] = self._brightnessToDimmerLevel(light['brightness'])
        except Exception as ex:
                self.logger('--> Error while parsing Hue light {0}: {1}'.format(hue_light_object, ex))
        return light

    def _brightnessToDimmerLevel(self, brightness):
        return int(round(brightness / 2.54))

    def _dimmerLevelToBrightness(self, dimmer_level):
        return int(round(dimmer_level * 2.54))

    @background_task
    def run(self):
        if self._enabled:
            while self._poll_frequency > 0:
                start = time.time()
                self._getAllLightsState()
                # This loop will run approx. every 'poll_frequency' seconds
                sleep = self._poll_frequency - (time.time() - start)
                if sleep < 0:
                    sleep = 1
                time.sleep(sleep)

    @om_expose
    def get_config_description(self):
        return json.dumps(Hue.config_description)

    @om_expose
    def get_config(self):
        return json.dumps(self._config)

    @om_expose
    def set_config(self, config):
        config = json.loads(config)
        for key in config:
            if isinstance(config[key], basestring):
                config[key] = str(config[key])
        self._config_checker.check_config(config)
        self._config = config
        self._read_config()
        self.write_config(config)
        return json.dumps({'success': True})