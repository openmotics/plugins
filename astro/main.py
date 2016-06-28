"""
An astronomical plugin, for providing the system with astronomical data (e.g. whether it's day or not, based on the sun's location)
"""

import time
import requests
import simplejson as json
from datetime import datetime, timedelta
from subprocess import check_output
from plugins.base import om_expose, receive_events, background_task, OMPluginBase, PluginConfigChecker


class Astro(OMPluginBase):
    """
    An astronomical plugin, for providing the system with astronomical data (e.g. whether it's day or not, based on the sun's location)
    """

    name = 'Astro'
    version = '0.2.20'
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
            import pytz
        except ImportError:
            check_output('mount -o remount,rw /', shell=True)
            check_output('pip install pytz', shell=True)
            check_output('mount -o remount,ro /', shell=True)
            import pytz
        self._read_config()

        self.logger("Started Astro plugin")

    def _read_config(self):
        import pytz
        for bit in ['horizon_bit', 'civil_bit', 'nautical_bit', 'astronomical_bit']:
            setattr(self, '_{0}'.format(bit), int(self._config.get(bit, Astro.default_config[bit])))

        self._enabled = False
        if self._config['location'] != '':
            address = self._config['location']
            location = requests.get('https://maps.googleapis.com/maps/api/geocode/json?address={0}'.format(address)).json()
            if location['status'] == 'OK':
                self._latitude = location['results'][0]['geometry']['location']['lat']
                self._longitude = location['results'][0]['geometry']['location']['lng']
                self.logger('Latitude: {0} - Longitude: {1}'.format(self._latitude, self._longitude))
                now = datetime.now(pytz.utc)
                self.logger('It\'s now {0} UTC'.format(now.strftime('%Y-%m-%d %H:%M:%S')))
                self._enabled = True
            else:
                self.logger('Could not translate {0} to coordinates: {1}'.format(address, location['status']))

        self.logger('Astro is {0}'.format('enabled' if self._enabled else 'disabled'))

    @staticmethod
    def _convert(dt_string):
        import pytz
        date = datetime.strptime(dt_string, '%Y-%m-%dT%H:%M:%S+00:00')
        date = pytz.utc.localize(date)
        if date.year == 1970:
            return None
        return date

    @background_task
    def run(self):
        if self._enabled:
            import pytz
            while True:
                now = datetime.now(pytz.utc)
                tomorrow = pytz.utc.localize(datetime(now.year, now.month, now.day) + timedelta(days=1))
                try:
                    data = requests.get('http://api.sunrise-sunset.org/json?lat={0}&lng={1}&formatted=0'.format(
                        self._latitude, self._longitude
                    )).json()
                    sleep = 24 * 60 * 60
                    bits = [True, True, True, True]  # [day, civil, nautical, astronomical]
                    if data['status'] == 'OK':
                        # Load data
                        sunrise = Astro._convert(data['results']['sunrise'])
                        sunset = Astro._convert(data['results']['sunset'])
                        has_sun = sunrise is not None and sunset is not None
                        civil_start = Astro._convert(data['results']['civil_twilight_begin'])
                        civil_end = Astro._convert(data['results']['civil_twilight_end'])
                        has_civil = civil_start is not None and civil_end is not None
                        nautical_start = Astro._convert(data['results']['nautical_twilight_begin'])
                        nautical_end = Astro._convert(data['results']['nautical_twilight_end'])
                        has_nautical = nautical_start is not None and nautical_end is not None
                        astronomical_start = Astro._convert(data['results']['astronomical_twilight_begin'])
                        astronomical_end = Astro._convert(data['results']['astronomical_twilight_end'])
                        has_astronomical = astronomical_start is not None and astronomical_end is not None
                        # Analyse data
                        if not any([has_sun, has_civil, has_nautical, has_astronomical]):
                            # This is an educated guess; Polar day (sun never sets) and polar night (sun never rises) can
                            # happen in the polar circles. However, since we have far more "gradients" in the night part,
                            # polar night (as defined here - pitch black) only happens very close to the poles. So it's
                            # unlikely this plugin is used there.
                            info = 'polar day'
                            bits = [True, True, True, True]
                            sleep = (tomorrow - now).total_seconds()
                        else:
                            if has_sun is False:
                                bits[0] = False
                            else:
                                bits[0] = sunrise < now < sunset
                                if bits[0] is True:
                                    sleep = min(sleep, (sunset - now).total_seconds())
                                elif now < sunrise:
                                    sleep = min(sleep, (sunrise - now).total_seconds())
                            if has_civil is False:
                                if has_sun is True:
                                    bits[1] = not bits[0]
                                else:
                                    bits[1] = False
                            else:
                                bits[1] = civil_start < now < civil_end
                                if bits[1] is True:
                                    sleep = min(sleep, (civil_end - now).total_seconds())
                                elif now < sunrise:
                                    sleep = min(sleep, (civil_start - now).total_seconds())
                            if has_nautical is False:
                                if has_sun is True or has_civil is True:
                                    bits[2] = not bits[1]
                                else:
                                    bits[2] = False
                            else:
                                bits[2] = nautical_start < now < nautical_end
                                if bits[2] is True:
                                    sleep = min(sleep, (nautical_end - now).total_seconds())
                                elif now < sunrise:
                                    sleep = min(sleep, (nautical_start - now).total_seconds())
                            if has_astronomical is False:
                                if has_sun is True or has_civil is True or has_nautical is True:
                                    bits[3] = not bits[2]
                                else:
                                    bits[3] = False
                            else:
                                bits[3] = astronomical_start < now < astronomical_end
                                if bits[3] is True:
                                    sleep = min(sleep, (astronomical_end - now).total_seconds())
                                elif now < sunrise:
                                    sleep = min(sleep, (astronomical_start - now).total_seconds())
                            sleep = min(sleep, (tomorrow - now).total_seconds())
                            info = 'night'
                            if bits[3] is True:
                                info = 'astronimical twilight'
                            if bits[2] is True:
                                info = 'nautical twilight'
                            if bits[1] is True:
                                info = 'civil twilight'
                            if bits[0] is True:
                                info = 'day'
                        # Set bits in system
                        for index, bit in {0: self._horizon_bit,
                                           1: self._civil_bit,
                                           2: self._nautical_bit,
                                           3: self._astronomical_bit}.iteritems():
                            if bit > -1:
                                result = json.loads(self.webinterface.do_basic_action(None, 237 if bits[index] else 238, bit))
                                if result['success'] is False:
                                    self.logger('Failed to set bit {0} to {1}'.format(bit, 1 if bits[index] else 0))
                        self.logger('It\'s {0}. Going to sleep for {1} seconds'.format(info, round(sleep, 1)))
                        time.sleep(sleep + 5)
                    else:
                        self.logger('Could not load data: {0}'.format(data['status']))
                        sleep = (tomorrow - now).total_seconds()
                        time.sleep(sleep + 5)
                except Exception as ex:
                    self.logger('Error figuring out where the sun is: {0}'.format(ex))
                    sleep = (tomorrow - now).total_seconds()
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
