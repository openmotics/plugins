"""
An InfluxDB plugin, for sending statistics to InfluxDB
"""

import time
import requests
import simplejson as json
from threading import Thread
from collections import deque
from plugins.base import om_expose, OMPluginBase, PluginConfigChecker, om_metric_receive


class InfluxDB(OMPluginBase):
    """
    An InfluxDB plugin, for sending statistics to InfluxDB
    """

    name = 'InfluxDB'
    version = '2.0.61'
    interfaces = [('config', '1.0')]

    config_description = [{'name': 'url',
                           'type': 'str',
                           'description': 'The enpoint for the InfluxDB using HTTP. E.g. http://1.2.3.4:8086'},
                          {'name': 'username',
                           'type': 'str',
                           'description': 'Optional username for InfluxDB authentication.'},
                          {'name': 'password',
                           'type': 'str',
                           'description': 'Optional password for InfluxDB authentication.'},
                          {'name': 'database',
                           'type': 'str',
                           'description': 'The InfluxDB database name to witch statistics need to be send.'},
                          {'name': 'add_custom_tag',
                           'type': 'str',
                           'description': 'Add custom tag to statistics'},
                          {'name': 'batch_size',
                           'type': 'int',
                           'description': 'The maximum batch size of grouped metrics to be send to InfluxDB.'}]

    default_config = {'url': '', 'database': 'openmotics'}

    def __init__(self, webinterface, logger):
        super(InfluxDB, self).__init__(webinterface, logger)
        self.logger('Starting InfluxDB plugin...')

        self._config = self.read_config(InfluxDB.default_config)
        self._config_checker = PluginConfigChecker(InfluxDB.config_description)
        self._pending_metrics = {}
        self._send_queue = deque()

        self._send_thread = Thread(target=self._sender)
        self._send_thread.setName('InfluxDB batch sender')
        self._send_thread.daemon = True
        self._send_thread.start()

        self._read_config()
        self.logger("Started InfluxDB plugin")

    def _read_config(self):
        self._url = self._config['url']
        self._database = self._config['database']
        self._batch_size = self._config.get('batch_size', 10)
        username = self._config.get('username', '')
        password = self._config.get('password', '')
        self._auth = None if username == '' else (username, password)
        self._add_custom_tag = self._config.get('add_custom_tag', '')

        self._endpoint = '{0}/write?db={1}'.format(self._url, self._database)
        self._query_endpoint = '{0}/query?db={1}&epoch=ns'.format(self._url, self._database)
        self._headers = {'X-Requested-With': 'OpenMotics plugin: InfluxDB'}

        self._enabled = self._url != '' and self._database != ''
        self.logger('InfluxDB is {0}'.format('enabled' if self._enabled else 'disabled'))

    @om_metric_receive(interval=10)
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
                if isinstance(value, basestring):
                    value = '"{0}"'.format(value)
                if isinstance(value, bool):
                    value = str(value)
                if isinstance(value, int) or isinstance(value, long):
                    value = '{0}i'.format(value)
                _values[key] = value

            tags = {'source': metric['source'].lower()}
            if self._add_custom_tag:
                tags['custom_tag'] = self._add_custom_tag
            for tag, tvalue in metric['tags'].iteritems():
                if isinstance(tvalue, basestring):
                    tags[tag] = tvalue.replace(' ', '\ ').replace(',', '\,')
                else:
                    tags[tag] = tvalue

            entry = self._build_entry(metric['type'], tags, _values, metric['timestamp'] * 1000000000)
            self._send_queue.appendleft(entry)

        except Exception as ex:
            self.logger('Error receiving metrics: {0}'.format(ex))

    @staticmethod
    def _build_entry(key, tags, value, timestamp):
        if isinstance(value, dict):
                values = ','.join('{0}={1}'.format(vname, vvalue)
                                  for vname, vvalue in value.iteritems())
        else:
            values = 'value={0}'.format(value)
        return '{0},{1} {2}{3}'.format(key,
                                       ','.join('{0}={1}'.format(tname, tvalue)
                                                for tname, tvalue in tags.iteritems()),
                                       values,
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
                    response = requests.post(url=self._endpoint,
                                             data='\n'.join(data),
                                             headers=self._headers,
                                             auth=self._auth,
                                             verify=False)
                    if response.status_code != 204:
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
        return json.dumps(InfluxDB.config_description)

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
