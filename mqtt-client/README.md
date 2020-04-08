# MQTT Client

An MQTT client plugin for sending/receiving data to/from an MQTT broker.

## Work in progress

This is a work in progress, but has already been extensively tested in a real home. This plugin is shared for community
feedback and/or contributions. Please only use this plugin if you know what you're doing and if you're willing to debug
issues you might encounter. As always, feel free to report issues and/or make pull requests.

## Configuration

```
config_description = [
        {'name': 'hostname',
         'type': 'str',
         'description': 'MQTT broker hostname or IP address.'},
        {'name': 'port',
         'type': 'int',
         'description': 'MQTT broker port. Default: 1883'},
        {'name': 'username',
         'type': 'str',
         'description': 'MQTT broker username. Default: openmotics'},
        {'name': 'password',
         'type': 'password',
         'description': 'MQTT broker password'},
        # input status
        {'name': 'input_status_enabled',
         'type': 'bool',
         'description': 'Enable input status publishing of messages.'},
        {'name': 'input_status_topic_format',
         'type': 'str',
         'description': 'Input status topic format. Default: openmotics/input/{id}/status'},
        {'name': 'input_status_qos',
         'type': 'enum',
         'choices': ['0', '1', '2'],
         'description': 'Input status message quality of service. Default: 0'},
        {'name': 'input_status_retain',
         'type': 'bool',
         'description': 'Input status message retain. Default: False'},
        # output status
        {'name': 'output_status_enabled',
         'type': 'bool',
         'description': 'Enable output status publishing of messages.'},
        {'name': 'output_status_topic_format',
         'type': 'str',
         'description': 'Output status topic format. Default: openmotics/output/{id}/status'},
        {'name': 'output_status_qos',
         'type': 'enum',
         'choices': ['0', '1', '2'],
         'description': 'Output status message quality of service. Default: 0'},
        {'name': 'output_status_retain',
         'type': 'bool',
         'description': 'Output status message retain. Default: False'},
        # event status
        {'name': 'event_status_enabled',
         'type': 'bool',
         'description': 'Enable event status publishing of messages.'},
        {'name': 'event_status_topic_format',
         'type': 'str',
         'description': 'Event status topic format. Default: openmotics/event/{id}/status'},
        {'name': 'event_status_qos',
         'type': 'enum',
         'choices': ['0', '1', '2'],
         'description': 'Event status message quality of service. Default: 0'},
        {'name': 'event_status_retain',
         'type': 'bool',
         'description': 'Event status message retain. Default: False'},
        # sensor status
        {'name': 'sensor_status_enabled',
         'type': 'bool',
         'description': 'Enable sensor status publishing of messages.'},
        {'name': 'sensor_status_topic_format',
         'type': 'str',
         'description': 'Sensor status topic format. Default: openmotics/sensor/{id}/status'},
        {'name': 'sensor_status_qos',
         'type': 'enum',
         'choices': ['0', '1', '2'],
         'description': 'Sensor status message quality of service. Default: 0'},
        {'name': 'sensor_status_retain',
         'type': 'bool',
         'description': 'Sensor status message retain. Default: False'},
        # this doesn't seem to work, removing config parameter for now
        # {'name': 'sensor_metric_poll_frequency',
        #  'type': 'int',
        #  'description': 'Polling frequency for sensor metrics in seconds. Default: 300'},
        # energy status
        {'name': 'energy_status_enabled',
         'type': 'bool',
         'description': 'Enable energy status publishing of messages.'},
        {'name': 'energy_status_topic_format',
         'type': 'str',
         'description': 'Energy status topic format. Default: openmotics/energy/{id}/status'},
        {'name': 'energy_status_qos',
         'type': 'enum',
         'choices': ['0', '1', '2'],
         'description': 'Energy status quality of Service. Default: 0'},
        {'name': 'energy_status_retain',
         'type': 'bool',
         'description': 'Energy status retain. Default: False'},
        # this doesn't seem to work, removing config parameter for now
        # {'name': 'energy_metric_poll_frequency',
        # 'type': 'int',
        # 'description': 'Polling frequency for energy metrics in seconds. Default: 60'},
        # output command
        {'name': 'output_command_topic',
         'type': 'str',
         'description': 'Topic to subscribe to for output command messages. Leave empty to turn off.'},
        # logging
        {'name': 'logging_topic',
         'type': 'str',
         'description': 'Topic for logging messages. Leave empty to turn off.'},
        # timestamp timezone
        {'name': 'timezone',
         'type': 'str',
         'description': 'Timezone. Default: UTC. Example: Europe/Brussels'}
    ]
```

## Topics

### State messages

The system will publish the state for Inputs pressed, Outputs that change and Events. Sensor and Enrgy modules will also be able to periodically publish their status.
The format will be explained in the following subsections.
In general all topics contain an ID parameter indicated by the placeholder `{id}`. All payloads will have a JSON format with multiple attributes as described below.

#### Input state

##### Configuration:
* Topic:  topic_prefix/{id}/topic_suffix
* Payload:
```
{
    "id": "<input id>",
    "name": "<name of the Input>",
    "status": "<ON or OFF>","
    "timestamp": <ISO format timestamp in {timezone}>
}
```

##### Example:
* Topic configuration: input_status_topic_format = openmotics/input/{id}/state
* Actual topic: openmotics/input/1/state
* Actual payload:
```
{
    "id": 1,
    "name": "Bedroom",
    "status": "ON",
    "timestamp": "2020-03-22T06:56:45.009005+00:00"
}
```

#### Output state

##### Configuration:
* Topic: topic_prefix/{id}/topic_suffix
* Payload:
```
{
    "id": "<output id>",
    "name": "<name of the Output>",
    "value": <level of the Output, value 0-100>,
    "timestamp": <ISO format timestamp in {timezone}>
}
```

##### Example:
* Topic configuration: output_status_topic_format = openmotics/output/{id}/state
* Actual topic: openmotics/output/8/state
* Actual payload:
```
{
    "id": 8,
    "name": "Garden",
    "value": 100,
    "timestamp": "2020-03-22T11:57:58.338847+00:00"
}
```

#### Event state

##### Configuration:
* Topic: topic_prefix/{id}/topic_suffix
* Payload:
```
{
    "id": "<event id>",
    "timestamp": <ISO format timestamp in {timezone}>
}
```

##### Example:
* Topic configuration: event_status_topic_format = openmotics/event/{id}/state
* Actual topic: openmotics/event/2/state
* Actual payload:
```
{
    "id": 2,
    "timestamp": "2020-03-18T19:46:23.901069+00:00"
}
```

#### Sensor state

##### Configuration:
* Topic: topic_prefix/{id}/topic_suffix
* Payload:
```
{
    "id": "<output id>",
    "name": "<name of the Output>",
    "humidity": <relative humidity in %>,
    "temperature": <temperature>,
    "brightness": <brightness in lux>,
    "timestamp": <ISO format timestamp in {timezone}>
}
```

##### Example:
* Topic configuration: sensor_status_topic_format = openmotics/sensor/{id}/state
* Actual topic: openmotics/sensor/3/state
* Actual payload:
```
{
    "id": 3,
    "name": "Garage",
    "humidity": 56.5,
    "temperature": 14.5,
    "brightness": 596.62,
    "timestamp": "2020-04-08T15:51:25.707819+00:00"
}
```

#### Energy state

##### Configuration:
* Topic: topic_prefix/{id}/topic_suffix
* Payload:
```
{
    "id": "<output id>",
    "name": "<name of the Output>",
    "humidity": <relative humidity in %>,
    "temperature": <temperature>,
    "brightness": <brightness in lux>,
    "timestamp": <ISO format timestamp in {timezone}>
}
```

##### Example:
* Topic configuration: energy_status_topic_format = openmotics/energy/{id}/state
* Actual topic: openmotics/energy/11/state
* Actual payload:
```
{
    "id": "11",
    "name": "Kitchen",
    "counter": 245470,
    "counter_day": 108161,
    "counter_night": 137309,
    "current": 0.23376594483852386,
    "frequency": 49.99971389770508,
    "power": 43.19911575317383,
    "type": "openmotics",
    "voltage": 240.39581298828125,
    "timestamp": "2020-04-08T15:58:10.320326+00:00"
}
```

More information on how to send these OpenMotics events can be found on the [OpenMotics wiki: Action Types](http://wiki.openmotics.com/index.php/Action_Types), number 60.

### Command messages

The system can also be controlled by letting clients publish to a given topic.

#### Set Output

A topic to which this plugin will subscribe to can be defined. Publishing to this topic will control OpenMotics outputs (relays, lights).

##### Configuration:
* Topic: topic_prefix/+/topic_suffix
* Payload: value
For Outputs, the value should be an integer (0-100) representing the desired output state. In case
the Output is a relay, only 0 and 100 are considered valid values.
Note the difference in syntax when compared to the topics this plugin publishes to: a plus sign is used as the wildcard where the output id would go.

###### Example:
* Topic configuration: output_command_topic = openmotics/output/+/set
* Actual topic: openmotics/output/8/set
* Actual payload: 100

### Logging messages

This topic is mainly used for debugging purposes.

* Topic: can_be/any/topic
* Payload: log message
