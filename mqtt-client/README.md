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
                       'description': 'Port of the MQTT broker. Default: 1883'},
                      {'name': 'username',
                       'type': 'str',
                       'description': 'Username'},
                      {'name': 'password',
                       'type': 'str',
                       'description': 'Password'},
                      {'name': 'topic_prefix',
                       'type': 'str',
                       'description': 'Topic prefix'},
                      {'name': 'timezone',
                       'type': 'str',
                       'description': 'Timezone. Default: same as Gateway. Example: UTC'}]
```

## Topics

### State messages

The system will publish the state for Inputs pressed, Outputs that change and Events. It publishes to following topics:

#### Input state

* Topic:  {topic_prefix}/input/{id}/state
* Payload:
```
{
    "id": "<input id>",
    "name": "<name of the Input>",
    "timestamp": <ISO format timestamp in {timezone}>
}
```

#### Output state

* Topic: {topic_prefix}/output/{id}/state
* Payload:
```
{
    "id": "<output id>",
    "name": "<name of the Output>",
    "value": <level of the Output, value 0-100>,
    "timestamp": <ISO format timestamp in {timezone}>
}
```

### Event state

* Topic: {topic_prefix}/event/{id}/state
* Payload:
```
{
    "id": "<event id>",
    "timestamp": <ISO format timestamp in {timezone}>
}
```

More information on how to send these OpenMotics events can be found on the [OpenMotics wiki: Action Types](http://wiki.openmotics.com/index.php/Action_Types), number 60.

### Command messages

The system can also be controlled by letting clients publish to a given topic.

#### Set Output

* Topic: {topic_prefix}/output/{id}/set
* Payload: <value>

For Outputs, the value should be an integer (0-100) representing the desired output state. In case
the Output is a relay, only 0 and 100 are considered valid values.