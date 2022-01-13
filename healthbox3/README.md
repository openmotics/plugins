# Renson Healthbox3

A Healthbox 3 plugin, for aggregating all date and controlling boost levels.
It supports:
* Storing sensor data
* Boost individual smart zones

## Configuration

```
    name = 'Healthbox'
    version = '1.0.0'
    interfaces = [('config', '1.0'),
                  ('metrics', '1.0')]

    config_description = [{'name': 'serial',
                           'type': 'str',
                           'description': 'The serial of the Healthbox 3. E.g. 250424P0031'}]

    metric_definitions = [{'type': 'aqi',
                           'tags': ['type', 'description', 'serial'],
                           'metrics': [{'name': 'aqi',
                                        'description': 'Global air quality index',
                                        'type': 'gauge',
                                        'unit': 'aqi'}]}]

    default_config = {'serial': ''}
```

## Sensor mapping

There are 32 Sensors available in OpenMotics. Each sensor can be marked as Virtual, after which this plugin can update its values.

The ```sensor_id``` is the ID (0-31) of the OpenMotics Sensor. The ```renson_temperature_id``` is the ID of Healthbox 3 temperature sensor. 
The ```renson_temperature_id``` is the ID of the Healthbox 3 temperature sensor.
the ```renson_humidity``` is the ID of the Healthbox 3 humidity sensor.

Set unused values to ```-1```. For example, a Healthbox  that only reports CO2

### How to mark an OpenMotics sensor as Virtual

Use the OpenMotics maintenance mode to mark a Sensor as Virtual.

```
[openmotics]$ connect
Connecting...
Opening VPN connection...
VPN connected !
Opening maintenance socket...
Starting maintenance mode, waiting for other actions to complete ...
[openmotics]$ eeprom write 195 <sensor_id> 0
[openmotics]$ eeprom activate
[openmotics]$
```


