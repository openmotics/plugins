# MQTT Client

An MQTT client plugin for sending/receiving data to/from an MQTT broker.

## Work in progress

This is a work in progress and might or might not be suitable for real-life usage. This plugin is shared for community
feedback and/or contributions. Please only use this plugin if you know what you're doing and if you're willing to debug
issues you might encounter. As always, feel free to report issues and/or make pull requests.

## Configuration

```
config_description = [{'name': 'broker_ip',
                       'type': 'str',
                       'description': 'IP or hostname of the MQTT broker.'},
                      {'name': 'broker_port',
                       'type': 'int',
                       'description': 'Port of the MQTT broker. Default: 1883'}]
```

## Topics

### Events

The system will publish events for Inputs pressed, Outputs that change and Events. It publishes to following topics:

* Input: openmotics/events/input/{id}
* Output: openmotics/events/output/{id}
* Events: openmotics/events/event/{id}

For Inputs, the data is a JSON object:

```
{
    "id": "<input id>",
    "name": "<name of the Input>",
    "timestamp": <unix timestamp>
}
```

For Outputs, the data is a JSON object:

```
{
    "id": "<output id>",
    "name": "<name of the Output>",
    "value": <level of the Output, value 0-100>,
    "timestamp": <unix timestamp>
}
```

For Events, the data is a JSON object:
```
{
    "id": "<event id>",
    "timestamp": <unix timestamp>
}
```

More information on how to send these OpenMotics events can be found on the [OpenMotics wiki: Action Types](http://wiki.openmotics.com/index.php/Action_Types), number 60.

### Control

The system can also be controlled by letting clients publish to a given topic.

* Outputs: openmotics/set/output/{id}

For Outputs, the value should be an integer (0-100) representing the desired output state. In case
the Output is a relay, only 0 and 100 are considered valid values.