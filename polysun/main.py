# Copyright (C) 2020 OpenMotics BV
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either versio 3 of the
# License, or (at your option) any later versio.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
A Polysun plugin
"""

import time
import simplejson as json
from collections import deque
from plugins.base import om_expose, OMPluginBase, PluginConfigChecker, shutter_status, background_task


class Polysun(OMPluginBase):
    """
    A Polysun plugin
    """

    class State(object):
        # In sync with Gateway implementation
        GOING_UP = 'going_up'
        GOING_DOWN = 'going_down'
        STOPPED = 'stopped'
        UP = 'up'
        DOWN = 'down'

    name = 'Polysun'
    version = '0.0.11'
    interfaces = [('config', '1.0')]

    config_description = [{'name': 'mapping',
                           'type': 'section',
                           'description': 'Shutter to Output mapping',
                           'repeat': True,
                           'min': 1,
                           'content': [{'name': 'shutter_id', 'type': 'int'},
                                       {'name': 'output_id_up', 'type': 'int'},
                                       {'name': 'output_id_down', 'type': 'int'}]}]

    default_config = {}

    def __init__(self, webinterface, logger):
        super(Polysun, self).__init__(webinterface, logger)
        self.logger('Starting Polysun plugin...')

        self._config = self.read_config(Polysun.default_config)
        self._config_checker = PluginConfigChecker(Polysun.config_description)

        self._states = {}
        self._mapping = {}
        self._action_queue = deque()

        self._read_config()
        self.logger("Started Polysun plugin")

    def _read_config(self):
        for entry in self._config.get('mapping', []):
            shutter_id = entry['shutter_id']
            try:
                shutter_id = int(shutter_id)
                output_id_up = entry['output_id_up']
                output_id_down = entry['output_id_down']
                if not 0 <= shutter_id <= 240 or not 0 <= output_id_up <= 240 or not 0 <= output_id_down <= 240:
                    continue
                self._mapping[shutter_id] = {'up': output_id_up,
                                             'down': output_id_down}
            except ValueError:
                self.logger('Skipped entry with shutter_id {0}'.format(shutter_id))
        self._enabled = len(self._mapping)
        self.logger('Polysun is {0}'.format('enabled' if self._enabled else 'disabled'))

    @shutter_status
    def shutter_status(self, status, detail):
        _ = status  # We need the details
        for shutter_id in detail:
            new_state = detail[shutter_id]['state']
            shutter_id = int(shutter_id)
            if shutter_id not in self._mapping:
                continue
            old_state = self._states.get(shutter_id, Polysun.State.STOPPED)
            if new_state != old_state:
                self._states[shutter_id] = new_state
                self._action_queue.appendleft([shutter_id, new_state, old_state])
                self.logger('Received state transition for shutter {0} from {1} to {2}'.format(shutter_id, old_state, new_state))

    @background_task
    def runner(self):
        while True:
            try:
                shutter_id, new_state, old_state = self._action_queue.pop()
                mapping = self._mapping.get(shutter_id)
                if mapping is None:
                    continue

                output_id_up = mapping['up']
                output_id_down = mapping['down']

                # If there's an immediate direction change (the shutter is going up and is suddenly going down or vice versa,
                # the "button" are first released and the shutter considered to be stopped for further logic
                if old_state in [Polysun.State.GOING_DOWN, Polysun.State.GOING_UP] and new_state in [Polysun.State.GOING_DOWN, Polysun.State.GOING_UP]:
                    self.logger('Shutter {0}: Immediate direction change'.format(shutter_id))
                    self._turn_output(output_id_up, False)
                    self._turn_output(output_id_down, False)
                    old_state = Polysun.State.STOPPED
                    self.logger('Shutter {0}: Connected outputs {1} (up) and {2} (down) are turned off'.format(shutter_id, output_id_up, output_id_down))

                # If the old state was in some stopped state (either stopped, up or down) a movement is started. This means one of the
                # "buttons" needs to be pressed until the shutter timeout is elapsed.
                if old_state in [Polysun.State.DOWN, Polysun.State.UP, Polysun.State.STOPPED]:
                    self.logger('Shutter {0}: Started moving'.format(shutter_id))
                    if new_state == Polysun.State.GOING_DOWN:
                        self._turn_output(output_id_up, False)  # Make sure only one "button" is pressed at a time
                        self._turn_output(output_id_down, True)
                        self.logger('Shutter {0}: Connected output {1} (down) is turned on'.format(shutter_id, output_id_down))
                    if new_state == Polysun.State.GOING_UP:
                        self._turn_output(output_id_down, False)  # Make sure only one "button" is pressed at a time
                        self._turn_output(output_id_up, True)
                        self.logger('Shutter {0}: Connected output {1} (up) is turned on'.format(shutter_id, output_id_up))

                # If the shutter is currently moving and reached the UP/DOWN position, it means the configured timeout is elapsed
                # and the the blinds are assumed to be moving to the correct location. The "buttons" can be released
                if old_state in [Polysun.State.GOING_UP, Polysun.State.GOING_DOWN] and new_state in [Polysun.State.UP, Polysun.State.DOWN]:
                    self.logger('Shutter {0}: Shutter is now up/down'.format(shutter_id))
                    self._turn_output(output_id_up, False)
                    self._turn_output(output_id_down, False)
                    self.logger('Shutter {0}: Connected outputs {1} (up) and {2} (down) are turned off'.format(shutter_id, output_id_up, output_id_down))

                # If the new state is STOPPED, it (should) mean that an explicit stop action was executed. This is emulated by
                # briefly pressing the "button" again.
                if new_state == Polysun.State.STOPPED:
                    output_id = output_id_down
                    direction = 'down'
                    if old_state == Polysun.State.GOING_UP:
                        output_id = output_id_up
                        direction = 'up'
                    self.logger('Shutter {0}: Shutter is stopped'.format(shutter_id))
                    self._turn_output(output_id_down, False)
                    self._turn_output(output_id_up, False)
                    self.logger('Shutter {0}: Connected outputs {1} (up) and {2} (down) are turned off'.format(shutter_id, output_id_up, output_id_down))
                    self._turn_output(output_id, True)
                    self._turn_output(output_id, False)
                    self.logger('Shutter {0}: Connected output {1} ({2}) turned on & off'.format(shutter_id, output_id, direction))

            except IndexError:
                time.sleep(1)
            except Exception as ex:
                self.logger('Unexpected exception processing workload: {0}'.format(ex))
                time.sleep(1)

    def _turn_output(self, output_id, on):
        try:
            result = json.loads(self.webinterface.set_output(id=output_id, is_on=on))
            if not result.get('success', False):
                self.logger('Could not turn {0} output {1}: {2}'.format('on' if on else 'off',
                                                                        output_id,
                                                                        result.get('msg', 'Unknown')))
        except Exception as ex:
            self.logger('Unexpected exception turning {0} output {1}: {2}'.format('on' if on else 'off',
                                                                                  output_id,
                                                                                  ex))

    @om_expose
    def get_config_description(self):
        return json.dumps(Polysun.config_description)

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
