from dataclasses import dataclass
import requests
from . import constants
import logging

logger = logging.getLogger(__name__)


@dataclass
class Sensor:
    serial: str
    name: str
    description: str
    physical_quantity: str
    unit: str
    value: float


class SMADevice:

    def __init__(self, ip, password):
        self._ip = ip
        self._password = password
        self._serial = None
        self._session_id = None

    def get_sensors(self):
        sensors = []
        data = self._read_data()
        for key, info in constants.FIELD_MAPPING.items():
            name = info['name']
            description = info['description']
            physical_quantity = info['physical_quantity']
            unit = info['unit']
            if key in data:
                value = None
                values = self._extract_values(key, data[key], info['factor'])
                if len(values) == 0:
                    logger.debug('* {0}: No values'.format(name))
                elif len(values) == 1:
                    value = values[0]
                    logger.debug('* {0}: {1}{2}'.format(name, value, unit if value is not None else ''))
                else:
                    logger.debug('* {0}:'.format(name))
                    for value in values:
                        logger.debug('** {0}{1}'.format(value, unit if value is not None else ''))
                    values = [value for value in values
                              if value is not None]
                    if len(values) == 1:
                        value = values[0]
                    elif len(values) > 1:
                        value = sum(values) / len(values)
                sensors.append(Sensor(serial=self._serial,
                                      name=name,
                                      description=description,
                                      physical_quantity=physical_quantity,
                                      unit=unit,
                                      value=value))
            else:
                logger.debug('* Missing key: {0}'.format(key))
        # explicitly log missing but expected values
        for key in data:
            if key not in constants.FIELD_MAPPING.keys():
                logger.debug('* Unknown key {0}: {1}'.format(key, data[key]))
        return sensors

    def _read_data(self):
        while True:
            endpoint = '{0}/dyn/getValues.json?sid={1}'.format(self._ip, self._session_id or '')
            response = requests.post(endpoint,
                                     json={'destDev': [], 'keys': list(constants.FIELD_MAPPING.keys())},
                                     timeout=10,
                                     verify=False).json()
            if response.get('err') == 401:
                self._login()
                continue
            break
        if 'result' not in response or len(response['result']) != 1:
            raise RuntimeError('Unexpected response: {0}'.format(response))
        self._serial = list(response['result'].keys())[0]
        data = response['result'][self._serial]
        if data is None:
            raise RuntimeError('Unexpected response: {0}'.format(response))
        logger.debug('Read values {0}:'.format(self))
        return data

    def _extract_values(self, key, values, factor):
        if len(values) != 1 or '1' not in values:
            logger.error('* Unexpected structure for {0}: {1}'.format(key, values))
            return []
        values = values['1']
        if len(values) == 0:
            return []
        if len(values) == 1:
            return [self._clean_value(key, values[0], factor)]
        return_data = []
        for raw_value in values:
            value = self._clean_value(key, raw_value, factor)
            if value is not None:
                return_data.append(value)
        return return_data

    def _clean_value(self, key, value_container, factor):
        if 'val' not in value_container:
            logger.error('* Unexpected structure for {0}: {1}'.format(key, value_container))
            return None
        value = value_container['val']
        if value is None:
            return None
        return float(value) / factor

    def _login(self):
        endpoint = '{0}/dyn/login.json'.format(self._ip)
        response = requests.post(endpoint,
                                 json={'right': 'usr',
                                       'pass': self._password},
                                 verify=False).json()
        if 'result' in response and 'sid' in response['result']:
            self._session_id = response['result']['sid']
        else:
            error_code = response.get('err', 'unknown')
            if error_code == 503:
                raise RuntimeError('Maximum amount of sessions')
            raise RuntimeError('Could not login: {0}'.format(error_code))

    def __str__(self):
        return f"SMA {self._serial} @ {self._ip}"

    def __repr__(self):
        return self.__str__()