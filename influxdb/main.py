"""
An InfluxDB plugin, for sending statistics to InfluxDB
"""

import time
import requests
import simplejson as json
from threading import Thread
from Queue import Queue, Empty
from plugins.base import om_expose, OMPluginBase, PluginConfigChecker, om_metric_receive


class InfluxDB(OMPluginBase):
    """
    An InfluxDB plugin, for sending statistics to InfluxDB
    """

    name = 'InfluxDB'
    version = '2.0.25'
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
                          {'name': 'intervals',
                           'type': 'section',
                           'description': 'Optional interval overrides.',
                           'repeat': True,
                           'min': 0,
                           'content': [{'name': 'component', 'type': 'str'},
                                       {'name': 'interval', 'type': 'int'}]}]

    default_config = {'url': '', 'database': 'openmotics'}

    def __init__(self, webinterface, logger):
        super(InfluxDB, self).__init__(webinterface, logger)
        self.logger('Starting InfluxDB plugin...')

        self._config = self.read_config(InfluxDB.default_config)
        self._config_checker = PluginConfigChecker(InfluxDB.config_description)
        self._pending_metrics = {}
        self._send_queue = Queue()

        self._send_thread = Thread(target=self._sender)
        self._send_thread.setName('InfluxDB batch sender')
        self._send_thread.daemon = True
        self._send_thread.start()

        self._read_config()
        self.logger("Started InfluxDB plugin")

    def _read_config(self):
        self._url = self._config['url']
        self._database = self._config['database']
        intervals = self._config.get('intervals', [])
        self._intervals = {}
        for item in intervals:
            self._intervals[item['component']] = item['interval']
        username = self._config.get('username', '')
        password = self._config.get('password', '')
        self._auth = None if username == '' else (username, password)

        self._endpoint = '{0}/write?db={1}'.format(self._url, self._database)
        self._query_endpoint = '{0}/query?db={1}&epoch=ns'.format(self._url, self._database)
        self._headers = {'X-Requested-With': 'OpenMotics plugin: InfluxDB'}

        self._enabled = self._url != '' and self._database != ''
        self.logger('InfluxDB is {0}'.format('enabled' if self._enabled else 'disabled'))

    @om_metric_receive(plugin='.*', metric='.*', include_definition=True)
    def _receive_metric_data(self, metric, definition):
        """
        All metrics are collected, as filtering is done more finegraded when mapping to tables
        > example_definition = {"type": "energy",
        >                       "name": "power",
        >                       "description": "Total energy consumed (in kWh)",
        >                       "mtype": "counter",
        >                       "unit": "Wh",
        >                       "tags": ["device", "id"]}
        > example_metric = {"plugin": "OpenMotics",
        >                   "type": "energy",
        >                   "metric": "power",
        >                   "timestamp": 1497677091,
        >                   "device": "OpenMotics energy ID1",
        >                   "id": 0,
        >                   "value": 1234}
        All metrics are grouped by their plugin, type and tags. As soon as a new timestamp is received, the pending
        group is send to InfluxDB and a new group is started. The tags from a group are based on the metric's definition's
        tags. The fields (values) are the metric > value pairs.
        > example_group = ["energy",
        >                  {"device": "OpenMotics energy ID1",
        >                   "id": 0},
        >                  {"power": 1234,
        >                   "power_counter": 1234567,
        >                   "voltage": 234}]
        """
        try:
            metric_type = metric['type']
            plugin = metric['plugin'].lower()
            timestamp = metric['timestamp'] * 1000000000
            value = metric['value']

            if isinstance(value, basestring):
                value = '"{0}"'.format(value)
            if isinstance(value, bool):
                value = str(value)
            if isinstance(value, int):
                value = '{0}i'.format(value)
            tags = {'type': plugin}
            for tag in definition['tags']:
                if isinstance(metric[tag], basestring):
                    tags[tag] = metric[tag].replace(' ', '\ ')
                else:
                    tags[tag] = metric[tag]

            entries = self._pending_metrics.setdefault(plugin, {}).setdefault(metric_type, [])
            found = False
            for pending in entries[:]:
                this_one = True
                for tag in definition['tags']:
                    if tags[tag] != pending[1].get(tag):
                        this_one = False
                        break
                if this_one is True:
                    if pending[0] == timestamp:
                        found = True
                        pending[2][metric['metric']] = value
                    else:
                        self._enqueue(self._build_command(metric_type, pending[1], pending[2], pending[0]))
                        entries.remove(pending)
                    break
            if found is False:
                entries.append([timestamp, tags, {metric['metric']: value}])
        except Exception as ex:
            self.logger('Error receiving metrics: {0}'.format(ex))

    @staticmethod
    def _build_command(key, tags, value, timestamp):
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

    def _enqueue(self, data):
        if not isinstance(data, list) and not isinstance(data, basestring):
            raise RuntimeError('Invalid data enqueued ({0})'.format(type(data)))
        if isinstance(data, basestring):
            data = [data]
        if len(data) > 0:
            for entry in data:
                self._send_queue.put(entry)

    def _sender(self):
        while True:
            try:
                data = []
                try:
                    while True:
                        data.append(self._send_queue.get(False))
                        if len(data) == 10:
                            raise Empty()
                except Empty:
                    pass
                if len(data) > 0:
                    response = requests.post(url=self._endpoint,
                                             data='\n'.join(data),
                                             headers=self._headers,
                                             auth=self._auth,
                                             verify=False)
                    if response.status_code != 204:
                        self.logger('Send failed, received: {0} ({1})'.format(response.text, response.status_code))
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
