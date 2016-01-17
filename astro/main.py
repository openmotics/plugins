"""
An astronomical plugin, for providing the system with astronomical data (e.g. whether it's day or not, based on the sun's location)
"""

import time
import simplejson as json
from datetime import datetime, timedelta
from subprocess import check_output
from plugins.base import om_expose, receive_events, background_task, OMPluginBase, PluginConfigChecker


class Astro(OMPluginBase):
    """
    An astronomical plugin, for providing the system with astronomical data (e.g. whether it's day or not, based on the sun's location)
    """

    name = 'Astro'
    version = '0.2.2'
    interfaces = [('config', '1.0')]

    config_description = [{'name': 'location',
                           'type': 'str',
                           'description': 'A location which will be passed to Google to fetch location, timezone and elevation.'},
                          {'name': 'horizon_bit',
                           'type': 'int',
                           'description': 'The bit that indicates whether it is day. -1 when not in use.'},
                          {'name': 'civil_bit',
                           'type': 'int',
                           'description': 'The bit that indicates whether it is day or civil twilight. -1 when not in use.'},
                          {'name': 'nautical_bit',
                           'type': 'int',
                           'description': 'The bit that indicates whether it is day, civil or nautical twilight. -1 when not in use.'},
                          {'name': 'astronomical_bit',
                           'type': 'int',
                           'description': 'The bit that indicates whether it is day, civil, nautical or astronomical twilight. -1 when not in use.'}]

    default_config = {'location': 'Brussels,Belgium', 'horizon_bit': -1, 'civil_bit': -1, 'nautical_bit': -1, 'astronomical_bit': -1}

    def __init__(self, webinterface, logger):
        super(Astro, self).__init__(webinterface, logger)
        self.logger('Starting Astro plugin...')

        self._config = self.read_config(Astro.default_config)
        self._config_checker = PluginConfigChecker(Astro.config_description)

        try:
            import astral
        except ImportError:
            check_output('mount -o remount,rw /', shell=True)
            check_output('pip install astral', shell=True)
            check_output('mount -o remount,ro /', shell=True)
            import astral
        self._read_config()

        self.logger("Started Astro plugin")

    def _read_config(self):
        for bit in ['horizon_bit', 'civil_bit', 'nautical_bit', 'astronomical_bit']:
            setattr(self, '_{0}'.format(bit), int(self._config.get(bit, Astro.default_config[bit])))

        self._enabled = False
        if self._config['location'] != '':
            import astral
            self._astral = astral.Astral(astral.GoogleGeocoder)
            self._location = self._astral[self._config['location']]
            self._enabled = True
            self.logger('Timezone: {0}'.format(self._location.timezone))
            self.logger('Latitude: {0} - Longitude: {1}'.format(self._location.latitude, self._location.longitude))

        self.logger('Astro is {0}'.format('enabled' if self._enabled else 'disabled'))

    @background_task
    def run(self):
        if self._enabled:
            import astral
            import pytz
            while True:
                self._location.solar_depression = 6
                civil_data = self._location.sun(local=False)
                self._location.solar_depression = 12
                nautical_data = self._location.sun(local=False)
                self._location.solar_depression = 18
                astronomical_data = self._location.sun(local=False)
                now = datetime.now(pytz.utc)
                info = ''
                try:
                    # Options: sunrise
                    if now < astronomical_data['dawn']:
                        is_day = [False, False, False, False]
                        sleep = (astronomical_data['dawn'] - now).total_seconds()
                        info = 'night'
                    elif now < nautical_data['dawn']:
                        is_day = [False, False, False, True]
                        sleep = (nautical_data['dawn'] - now).total_seconds()
                        info = 'astronomical twlight (dawn)'
                    elif now < civil_data['dawn']:
                        is_day = [False, False, True, True]
                        sleep = (civil_data['dawn'] - now).total_seconds()
                        info = 'nautical twilight (dawn)'
                    elif now < civil_data['sunrise']:
                        is_day = [False, True, True, True]
                        sleep = (civil_data['sunrise'] - now).total_seconds()
                        info = 'civil twilight (dawn)'
                    elif now < civil_data['sunset']:
                        is_day = [True, True, True, True]
                        sleep = (civil_data['sunset'] - now).total_seconds()
                        info = 'day'
                    elif now < civil_data['dusk']:
                        is_day = [False, True, True, True]
                        sleep = (civil_data['dusk'] - now).total_seconds()
                        info = 'civil twilight (dusk)'
                    elif now < nautical_data['dusk']:
                        is_day = [False, False, True, True]
                        sleep = (nautical_data['dusk'] - now).total_seconds()
                        info = 'nautical twilight (dusk)'
                    elif now < astronomical_data['dusk']:
                        is_day = [False, False, False, True]
                        sleep = (astronomical_data['dusk'] - now).total_seconds()
                        info = 'astronomical twilight (dusk)'
                    else:
                        is_day = [False, False, False, False]
                        now = datetime.now()
                        tomorrow = datetime(now.year, now.month, now.day) + timedelta(days=1)
                        sleep = (tomorrow - now).total_seconds()
                        info = 'night'
                except astral.AstralError:
                    is_day = [False, False, False, False]
                    now = datetime.now()
                    tomorrow = datetime(now.year, now.month, now.day) + timedelta(days=11)
                    sleep = (tomorrow - now).total_seconds()
                for index, bit in {0: self._horizon_bit,
                                   1: self._civil_bit,
                                   2: self._nautical_bit,
                                   3: self._astronomical_bit}.iteritems():
                    if bit > -1:
                        result = json.loads(self.webinterface.do_basic_action(None, 237 if is_day[index] else 238, bit))
                        if result['success'] is False:
                            self.logger('Failed to set bit {0} to {1}'.format(bit, 1 if is_day[index] else 0))
                self.logger('It is now {0}. Going to sleep for {1} seconds'.format(info, sleep))
                time.sleep(sleep + 5)

    @om_expose
    def get_config_description(self):
        return json.dumps(Astro.config_description)

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
