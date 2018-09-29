# Renson Healthbox3

A Healthbox 3 plugin, for aggregating all date and controlling boost levels.
It supports:
* Storing sensor data
* Boost individual smart zones

## Configuration

```
config_description = [{'name': 'ip',
                       'type': 'str',
                       'description': 'The IP of the Fibaro Home Center (lite) device. E.g. 1.2.3.4'},
                     {'name': 'sensor_mapping',
                       'type': 'section',
                       'description': 'Mapping betweet OpenMotics Virtual Sensors and Healthbox3 Sensors',
                       'repeat': True,
                       'min': 0,
                       'content': [{'name': 'sensor_id', 'type': 'int'},
                                   {'name': 'renson_temperature_id', 'type': 'int'},
                                   {'name': 'renson_co2_id', 'type': 'int'},
                                   {'name': 'renson_humidity', 'type': 'int'}]}]
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


