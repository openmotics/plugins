# MQTT Client

An MQTT client plugin for sending/receiving data to/from an MQTT broker.

## Work in progress

This is a work in progress and might or might not be suitable for real-life usage. This plugin is shared for community
feedback and/or contributions. Please only use this plugin if you know what you're doing and if you're willing to debug
issues you might encounter. As always, feel free to report issues and/or make pull requests.

## Todo

* Find/create a way of installing pip packages in a non-hacked way
* Make things more configurable (e.g. filter certain events)

## Configuration

```
config_description = [{'name': 'broker_ip',
                       'type': 'str',
                       'description': 'IP or hostname of the MQTT broker.'},
                      {'name': 'broker_port',
                       'type': 'int',
                       'description': 'Port of the MQTT broker. Default: 1883'},
                      {'name': 'send_events',
                       'type': 'bool',
                       'description': 'Should the client send events (inputs, outputs)'}]
```

## Data

### Events

Events can be send (if configured) for input and output changes. The message data has the form of a JSON string.

```
{ "id": 1234, "name": "my_input", "timestamp": 1234567.89 }
```

Topic
-----

The client will publish messages under the configured base_topic. Below that topic following structure will be used:
* Events
  * Input: openmotics/events/input
  * Output: openmotics/events/output
* Sensor data: openmotics/sensor
* Power data: openmotics/power

Message format
--------------

