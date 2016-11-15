# Ventilation

A ventilation plugin using statistical humidity data or dew point to control the ventilation. The user can switch between dew point mode or
statistical mode.

Statistical mode: The plugin uses the mean and standard deviation of a set of samples as basis to see whether the current humidity can be
considered "higher than usual" and thus requires an increased ventilation. It calculates this data foreach individual humidity sensor,
and will adapt the ventilation to the highest required.

Dew point mode: The plugin tries to keep the humidity between a given range and will (try to) set the ventilation to such level that
the humidity will eventually be in the given range. It uses the outdoor and indoor absolute humidity to calculate whether increasing
the ventilation would actually change the humidity in the good direction.

The plugin will adapt the ventilation system once per minut, but will only set the ventilation when it detects a change. So it's still possible
to manually override the ventilation system. The manual setting won't be changed until the plugin detects humidity changes for which it needs
to set the ventilation to a specific level.

*The documentation for version 0.x is at the bottom of the page*

## Configuration

```
config_description = [{'name': 'low',
                       'type': 'section',
                       'description': 'Output configuration for "low" ventilation',
                       'repeat': True,
                       'min': 1,
                       'content': [{'name': 'output_id', 'type': 'int'},
                                   {'name': 'value', 'type': 'int'}]},
                      {'name': 'medium',
                       'type': 'section',
                       'description': 'Output configuration for "medium" ventilation',
                       'repeat': True,
                       'min': 1,
                       'content': [{'name': 'output_id', 'type': 'int'},
                                   {'name': 'value', 'type': 'int'}]},
                      {'name': 'high',
                       'type': 'section',
                       'description': 'Output configuration for "high" ventilation',
                       'repeat': True,
                       'min': 1,
                       'content': [{'name': 'output_id', 'type': 'int'},
                                   {'name': 'value', 'type': 'int'}]},
                      {'name': 'sensors',
                       'type': 'section',
                       'description': 'Sensors to use for ventilation control.',
                       'repeat': True,
                       'min': 1,
                       'content': [{'name': 'sensor_id', 'type': 'int'}]},
                      {'name': 'mode',
                       'type': 'nested_enum',
                       'description': 'The mode of the ventilation control',
                       'choices': [{'value': 'statistical', 'content': [{'name': 'samples',
                                                                         'type': 'int'},
                                                                        {'name': 'trigger',
                                                                         'type': 'int'}]},
                                   {'value': 'dew_point', 'content': [{'name': 'outside_sensor_id',
                                                                       'type': 'int'},
                                                                      {'name': 'target_lower',
                                                                       'type': 'int'},
                                                                      {'name': 'target_upper',
                                                                       'type': 'int'},
                                                                      {'name': 'offset',
                                                                       'type': 'int'},
                                                                      {'name': 'trigger',
                                                                       'type': 'int'}]}]}]
```

The configuration parameters ```low```, ```medium``` and ```high``` consist out of one or more outputs together with their desired value.
When the plugin for example wants to set the ventilation to ```medium```, it will set all configured outputs according to that specific setting.
If for example only two levels are possible, a user must set two levels to the same output configuration.

The sensors are a list of the IDs of all Sensors that need to be monitored.

## Mode: Statistical

The ```samples``` setting indicates how many samples should be used as a basis to calculate all thresholds. Taking one sample per minute
means that for a 24h coverage, ```1440``` samples are a good value. A 24h range will result in a stable ventilation system that can cope
with changing humidities by weather influence, but will act correctly on sudden changes (e.g. taking a shower). The system does not cache
samples, so in case of power loss, all previous samples are lost, so after a restart the ventilation might change faster, but as soon as more
samples are collected, it will become more stable.

The ```trigger``` setting covers sensor misreadings. As with every sensor, error readings will occur, and this threshold will make
sure that at least X amount of measurements must be above a threshold to change the ventilation. A good value is ```3```.

## Mode: Dew point

The ```outside_sensor_id``` is the ID of the outside Sensor that will influence the air that will get pulled inside. If for example a bathroom
has a high absolute humidity after a shower, but the air outside is far more humid, the ventilation will not be increased, since it would
increase the humidity.

The ```target_lower``` and ```target_upper``` values indicate the desired relative humidity range indoors. The system will try to get the
relative humidity inside this range. If the current relative humidity is not within this range, and the outdoor humidity is right, the ventilation
is increased to the ```medium``` setting.

The ```offset``` is used to control the ventilation based on how close the dew point is to the actual temperature. If the dew point is higher than
2 times the offset below the actual temperature, the ventilation is set to ```medium```. If higher than 1 times the offset below the actual
temperature, the ventilation is set to ```high```.

The ```trigger``` setting covers sensor misreadings. As with every sensor, error readings will occur, and this threshold will make
sure that at least X amount of measurements must be above a threshold to change the ventilation. A good value is ```3```.

# Ventilation 0.x (obsolete)

## Configuration

```
config_description = [{'name': 'outputs',
                       'type': 'str',
                       'description': 'A JSON formatted dict containing output parameters for 3 ventilation settings. See README.md for more details.'},
                      {'name': 'samples',
                       'type': 'int',
                       'description': 'The number of samples on which to calculate the statistical threshold. There is one sample per minute.'},
                      {'name': 'trigger',
                       'type': 'int',
                       'description': 'The numer of samples that must be above or below the threshold.'},
                      {'name': 'ignore_sensors',
                       'type': 'str',
                       'description': 'A JSON formatted list containing humidity sensor ids to be ignored.'}]
```

The configuration parameters "outputs" and "ignore_sensors" are described below.

The ```samples``` setting indicates how many samples should be used as a basis to calculate all thresholds. Taking one sample per minute
means that for a 24h coverage, ```1440``` samples are a good value. A 24h range will result in a stable ventilation system that can cope
with changing humidities by weather influence, but will act correctly on sudden changes (e.g. taking a shower). The system does not cache
samples, so in case of power loss, all previous samples are lost, so after a restart the ventilation might change faster, but as soon as more
samples are collected, it will become more stable.

The ```trigger``` setting covers sensor misreadings. As with every sensor, error readings will occur, and this threshold will make
sure that at least X amount of measurements must be above a threshold to change the ventilation. A good value is ```3```.

## Outputs

The plugin currently supports 3 levels of ventilation, where the first level is considered "default" and will be set when no higher humidity values
are detected. If a ventilation system supports less levels, two levels can be configured to behave identical, and if the ventilation system supports
more levels, only 3 of them can be used by this plugin.

This setting consists of a JSON formatted string containing a dictionary-like structure. An example:

```
{
    "1": {
        "38": 0,
        "37": 0,
        "36": 100
    },
    "2": {
        "38": 0,
        "37": 100,
        "36": 100
    },
    "3": {
        "38": 100,
        "37": 0,
        "36": 100
    }
}
```

This means that for ventilation level ```1```, output 38 will be set to ```0```, output 37 will be set to ```0``` and output 36 will be set
to ```100```. For the other levels, the outputs are set differntly. The above dictionary must be collapsed to a single line for configuration:

```
{"1": {"36": 100, "37": 0, "38": 0}, "3": {"36": 100, "37": 0, "38": 100}, "2": {"36": 100, "37": 100, "38": 0}}
```

## Ignore sensors

The ```ignore_sensors``` configuration setting is a JSON encoded list of all humidity sensors that should not be monitored. This for example can
be a sensor outside of the house which should not increase ventilation if the outside humidity increases.

An example setting in which sensors 5 and 9 will be ignored:

```
[5, 9]
```
