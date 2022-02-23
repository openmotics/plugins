# coding=utf-8
"""
An Statful plugin, for sending metrics to Statful (adapted from InfluxDB plugin)
"""

import six
import time
import requests
import simplejson as json
from threading import Thread
from collections import deque
from plugins.base import om_expose, OMPluginBase, PluginConfigChecker, om_metric_receive


class Statful(OMPluginBase):
    """
    An Statful plugin, for sending metrics to Statful (adapted from InfluxDB plugin)
    """

    name = 'Statful'
    version = '1.0.1'
    url = 'https://api.statful.com/tel/v2.0/metrics'
    interfaces = [('config', '1.0')]

    config_description = [{'name': 'token',
                           'type': 'str',
                           'description': 'Statful API token for authentication.'},
                          {'name': 'add_custom_tag',
                           'type': 'str',
                           'description': 'Add custom tag to statistics'},
                          {'name': 'batch_size',
                           'type': 'int',
                           'description': 'The maximum batch size of grouped metrics to be send to Statful.'}]

    default_config = {}

    def __init__(self, webinterface, logger):
        super(Statful, self).__init__(webinterface, logger)
        self.logger('Starting Statful plugin...')

        self._config = self.read_config(Statful.default_config)
        self._config_checker = PluginConfigChecker(Statful.config_description)
        self._pending_metrics = {}
        self._send_queue = deque()

        self._send_thread = Thread(target=self._sender)
        self._send_thread.setName('Statful batch sender')
        self._send_thread.daemon = True
        self._send_thread.start()

        self._read_config()
        self.logger("Started Statful plugin")

    def _read_config(self):
        self._batch_size = self._config.get('batch_size', 10)
        self._add_custom_tag = self._config.get('add_custom_tag', '')

        token = self._config.get('token', '')
        self._headers = {'M-Api-Token': token, 'X-Requested-With': 'OpenMotics plugin: Statful'}

        self._enabled = token != ''
        self.logger('Statful is {0}'.format('enabled' if self._enabled else 'disabled'))

    @om_metric_receive(interval=30)
    def _receive_metric_data(self, metric):
        """
        All metrics are collected, as filtering is done more finegraded when mapping to tables
        > example_metric = {"source": "OpenMotics",
        >                   "type": "energy",
        >                   "timestamp": 1497677091,
        >                   "tags": {"device": "OpenMotics energy ID1",
        >                            "id": 0},
        >                   "values": {"power": 1234,
        >                              "power_counter": 1234567}}
        """
        try:
            if self._enabled is False:
                return

            values = metric['values']
            _values = {}
            for key in values.keys()[:]:
                value = values[key]
                if isinstance(value, six.string_types):
                    value = '"{0}"'.format(value)
                if isinstance(value, bool):
                    value = int(value == True)
                if isinstance(value, six.integer_types):
                    value = '{0}'.format(value)
                _values[key] = value

            tags = {'source': metric['source'].lower()}
            if self._add_custom_tag:
                tags['custom_tag'] = self._add_custom_tag
            for tag, tvalue in metric['tags'].items():
                if isinstance(tvalue, six.string_types):
                    # send tag values as ascii. specification details at https://www.statful.com/docs/metrics-ingestion-protocol.html#Metrics-Ingestion-Protocol
                    tags[tag] = tvalue.decode("utf-8").encode('ascii', 'ignore').replace(' ', '_').replace(',', '.')
                else:
                    tags[tag] = tvalue

            entries = self._build_entries(metric['type'], tags, _values, metric['timestamp'])
            for entry in entries:
                self._send_queue.appendleft(entry)

        except Exception as ex:
            self.logger('Error receiving metrics: {0}'.format(ex))

    @staticmethod
    def _build_entries(key, tags, value, timestamp):
        if isinstance(value, dict):
            _entries = []
            for vname, vvalue in value.items():
                _entries.append(Statful._build_entry(key, tags, vname, vvalue, timestamp))
            return _entries

        return [Statful._build_entry(key, tags, None, value, timestamp)]

    @staticmethod
    def _build_entry(metric, tags, key, value, timestamp):
        return 'openmotics.{0},{1} {2}{3}'.format(metric if key is None else '{0}.{1}'.format(metric, key),
                                       ','.join('{0}={1}'.format(tname, tvalue)
                                                for tname, tvalue in tags.items()),
                                       value,
                                       '' if timestamp is None else ' {:.0f}'.format(timestamp))

    def _sender(self):
        _stats_time = 0
        _batch_sizes = []
        _queue_sizes = []
        _run_amount = 0
        _batch_amount = 0
        while True:
            try:
                data = []
                try:
                    while True:
                        data.append(self._send_queue.pop())
                        if len(data) == self._batch_size:
                            raise IndexError()
                except IndexError:
                    pass
                if len(data) > 0:
                    _batch_sizes.append(len(data))
                    _run_amount += len(data)
                    _batch_amount += 1
                    _queue_sizes.append(len(self._send_queue))
                    response = requests.put(url=Statful.url,
                                            data='\n'.join(data),
                                            headers=self._headers,
                                            verify=False)
                    if response.status_code != 201:
                        self.logger('Send failed, received: {0} ({1})'.format(response.text, response.status_code))
                    if _stats_time < time.time() - 1800:
                        _stats_time = time.time()
                        self.logger('Queue size stats: {0:.2f} min, {1:.2f} avg, {2:.2f} max'.format(
                            min(_queue_sizes),
                            sum(_queue_sizes) / float(len(_queue_sizes)),
                            max(_queue_sizes)
                        ))
                        self.logger('Batch size stats: {0:.2f} min, {1:.2f} avg, {2:.2f} max'.format(
                            min(_batch_sizes),
                            sum(_batch_sizes) / float(len(_batch_sizes)),
                            max(_batch_sizes)
                        ))
                        self.logger('Total {0} metric(s) over {1} batche(s)'.format(_run_amount, _batch_amount))
                        _batch_sizes = []
                        _queue_sizes = []
                        _run_amount = 0
                        _batch_amount = 0
            except Exception as ex:
                self.logger('Error sending from queue: {0}'.format(ex))
            time.sleep(0.1)

    @om_expose
    def get_config_description(self):
        return json.dumps(Statful.config_description)

    @om_expose
    def get_config(self):
        return json.dumps(self._config)

    @om_expose
    def set_config(self, config):
        config = json.loads(config)
        for key in config:
            if isinstance(config[key], six.string_types):
                config[key] = str(config[key])
        self._config_checker.check_config(config)
        self._config = config
        self._read_config()
        self.write_config(config)
        return json.dumps({'success': True})
