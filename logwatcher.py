#!/bin/env python2.7

import re
import sys
import time
import requests
import warnings
import getpass
from requests.packages.urllib3 import exceptions
from datetime import datetime


def watch(ip, username, password, plugin):
    lastlog = None
    token = None
    while True:
        if token is None:
            token = connect(ip, username, password)
        try:
            response = requests.get('https://{0}/get_plugin_logs'.format(ip),
                                    params={'token': token},
                                    verify=False)
            if response.status_code == 200:
                logs = response.json()['logs']
                if plugin in logs:
                    for line in [l for l in logs[plugin].splitlines() if l]:
                        if re.match('[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}.[0-9]+', line):
                            timestamp, entry = line.split(' - ', 1)
                            parsed_ts = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S.%f')
                            if lastlog is None or parsed_ts > lastlog:
                                lastlog = parsed_ts
                                print '{0} - {1}'.format(timestamp, entry)
                else:
                    print 'Could not find plugin {0}. Available plugins are: {1}'.format(plugin, ', '.join(logs.keys()))
                    sys.exit(1)
            if response.status_code == 403:
                token = None
        except Exception as ex:
            print 'Error fetching logs: {0}'.format(ex)
            sys.exit(1)
        time.sleep(1)


def connect(ip, username, password):
    try:
        requests.packages.urllib3.disable_warnings()
        response = requests.get('https://{0}/login'.format(ip),
                                params={'username': username,
                                        'password': password},
                                verify=False)
        if response.status_code == 200:
            return response.json()['token']
        print 'Invalid username/password'
    except Exception as ex:
        print 'Error logging in: {0}'.format(ex)
    sys.exit(1)

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print 'Usage: ./logwatcher.py <ip/hostname of gateway> <username> <plugin>'
        sys.exit(1)
    try:
        _ip = sys.argv[1]
        _username = sys.argv[2]
        _plugin = sys.argv[3]
        _password = getpass.getpass('Password: ')
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", exceptions.InsecureRequestWarning)
            watch(_ip, _username, _password, _plugin)
    except KeyboardInterrupt:
        print ''
        pass
