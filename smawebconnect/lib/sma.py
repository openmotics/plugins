import copy
from dataclasses import dataclass
import requests
from . import constants
import logging
import typing
from typing import Dict, List


logger = logging.getLogger(__name__)



class SMADevice:
    def __init__(self):
        self._serial = None
        self.field_mapping = constants.FieldMapping()

    @property
    def serial(self):
        return self._serial

    def _cleanup_raw_values(self, mapping, values):
        value = None
        if len(values) == 0:
            logger.debug('* {0}: No values'.format(mapping.sensor_mapping.name))
        elif len(values) == 1:
            value = values[0]
            logger.debug('* {0}: {1} {2}'.format(mapping.sensor_mapping.name, value, mapping.sensor_mapping.unit if value is not None else ''))
        else:
            logger.debug('* {0}:'.format(mapping.sensor_mapping.name))
            for value in values:
                logger.debug('** {0} {1}'.format(value, mapping.sensor_mapping.unit if value is not None else ''))
            values = [value for value in values
                      if value is not None]
            if len(values) == 1:
                value = values[0]
            elif len(values) > 1:
                value = sum(values) / len(values)
        return value

    def get_all_mappings(self):
        mappings = self.field_mapping.get_all_mappings()
        data = self._read_data()
        result = []

        for mapping in mappings:
            new_mapping = copy.deepcopy(mapping)
            has_value = False
            if mapping.sensor_key in data:
                values = self._extract_values(mapping.sensor_key, data[mapping.sensor_key], mapping.sensor_mapping.factor)
                value = self._cleanup_raw_values(mapping, values)
                if value is not None:
                    new_mapping.sensor_mapping.value = value
                    has_value = True
            if mapping.counter_key in data:
                values = self._extract_values(mapping.counter_key, data[mapping.counter_key], mapping.counter_mapping.factor)
                value = self._cleanup_raw_values(mapping, values)
                if value is not None:
                    new_mapping.counter_mapping.value = value
                    has_value = True

            if has_value:
                result.append(new_mapping)
        return result

    def _extract_values(self, key: str, values: dict, factor: float):
        return_data = []
        if len(values) == 1:
            for weird_sma_index in ['1', '9']:
                data_values = values.get(weird_sma_index, [])
                for raw_value in data_values:
                    value = self._clean_value(key, raw_value, factor)
                    if value is not None:
                        return_data.append(value)
        else:
            logger.error('* Unexpected structure for {0}: {1}'.format(key, values))
        return return_data

    @staticmethod
    def _clean_value(key: str, value_container: dict, factor: float):
        if 'val' not in value_container:
            logger.error('* Unexpected structure for {0}: {1}'.format(key, value_container))
            return None
        value = value_container.get('val')
        if isinstance(value, float) or isinstance(value, int):
            return float(value) / factor
        else:
            logger.debug('* key {0} value {1} is not a number'.format(key, value))
            return None

    def _read_data(self):
        pass


class SMADeviceDummy(SMADevice):

    def __init__(self, dummy_api_response: Dict):
        self.api_response = dummy_api_response
        super(SMADeviceDummy, self).__init__()

    def _read_data(self):
        response = self.api_response
        logger.debug(f"Got raw response: {response}")
        self._serial = list(response['result'].keys())[0]
        data = response['result'][self._serial]
        if data is None:
            raise RuntimeError('Unexpected response: {0}'.format(response))
        logger.debug('Read Dummy values {0}:'.format(self))
        return data

    def __str__(self):
        return f"<SMA Dummy device>"

    def __repr__(self):
        return self.__str__()


class SMADeviceOverIP(SMADevice):

    def __init__(self, ip, password):
        self._ip = ip
        self._password = password
        self._session_id = None
        super(SMADeviceOverIP, self).__init__()

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