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
    version = '0.2.18'
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
                    times = []
                    if data['status'] == 'OK':
                        sunrise = Astro._convert(data['results']['sunrise'])
                        sunset = Astro._convert(data['results']['sunset'])
                        times += [sunrise, sunset]
                        if sunrise is None or sunset is None:
                            bits[0] = False
                        else:
                            bits[0] = sunrise < now < sunset
                            if bits[0] is True:
                                sleep = min(sleep, (sunset - now).total_seconds())
                        civil_start = Astro._convert(data['results']['civil_twilight_begin'])
                        civil_end = Astro._convert(data['results']['civil_twilight_end'])
                        times += [civil_start, civil_end]
                        if civil_start is None or civil_end is None:
                            bits[1] = False
                        else:
                            bits[1] = civil_start < now < civil_end
                            if bits[1] is True:
                                sleep = min(sleep, (civil_end - now).total_seconds())
                        nautical_start = Astro._convert(data['results']['nautical_twilight_begin'])
                        nautical_end = Astro._convert(data['results']['nautical_twilight_end'])
                        times += [nautical_start, nautical_end]
                        if nautical_start is None or nautical_end is None:
                            bits[2] = False
                        else:
                            bits[2] = nautical_start < now < nautical_end
                            if bits[2] is True:
                                sleep = min(sleep, (nautical_end - now).total_seconds())
                        astr_start = Astro._convert(data['results']['astronomical_twilight_begin'])
                        astr_end = Astro._convert(data['results']['astronomical_twilight_end'])
                        times += [astr_start, astr_end]
                        if astr_start is None or astr_end is None:
                            bits[3] = False
                        else:
                            bits[3] = astr_start < now < astr_end
                            if bits[3] is True:
                                sleep = min(sleep, (astr_end - now).total_seconds())
                        sleep = min(sleep, (tomorrow - now).total_seconds())
                        info = 'night'
                        if len([item for item in times if item is not None]) == 0:
                            # This is the case when it's permanent day or permanent night, and this plugin can't
                            # distinguish the two, it needs to make a guess here. However, since permanent night
                            # only happens around the poles, and it's unlikely a user of this plugin is at the poles,
                            # permanent day is here a good guess.
                            info = 'permanent day'
                            bits = [True, True, True, True]
                            sleep = (tomorrow - now).total_seconds()
                        else:
                            if bits[3] is True:
                                info = 'astronimical twilight'
                            if bits[2] is True:
                                info = 'nautical twilight'
                            if bits[1] is True:
                                info = 'civil twilight'
                            if bits[0] is True:
                                info = 'day'
                        for index, bit in {0: self._horizon_bit,
                                           1: self._civil_bit,
                                           2: self._nautical_bit,
                                           3: self._astronomical_bit}.iteritems():
                            if bit > -1:
                                result = json.loads(self.webinterface.do_basic_action(None, 237 if bits[index] else 238, bit))
                                if result['success'] is False:
                                    self.logger('Failed to set bit {0} to {1}'.format(bit, 1 if bits[index] else 0))
                        self.logger('It\'s {0}. Going to sleep for {1} seconds'.format(info, sleep))
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
