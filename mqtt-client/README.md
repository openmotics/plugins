# MQTT Client

An MQTT client plugin for sending/receiving data to/from an MQTT broker.

## Work in progress

This is a work in progress, but has already been extensively tested in a real home. This plugin is shared for community feedback and/or contributions. Please only use this plugin if you know what you're doing and if you're willing to debug issues you might encounter. As always, feel free to report issues and/or make pull requests.


## Configuration


### Broker

![Broker Configuration Screenshot][config_broker]

* hostname: MQTT broker hostname or IP address.
* port: MQTT broker port. Default: 1883.
* username: MQTT broker username. Default: openmotics.
* password: MQTT broker password.


### State messages

The system will publish the state for Inputs and Outputs that change, Events, Temperature, Humidity and Brightness sensors, Realtime Power and Total Energy.
The format will be explained in the following subsections.
In general all topics contain one or more parameters indicated by a placeholder like `{id}`. All payloads will have a JSON format with multiple attributes as described below.


#### Input state

##### Configuration:

![Input Configuration Screenshot][config_input]

* input_status_enabled: Enable OpenMotics to publish input status messages on the MQTT broker.
* input_status_topic_format: Input status topic format. Structure: `topic_prefix/{id}/topic_suffix`. Default: `openmotics/input/{id}/status`.
* input_status_qos: Input status message quality of service. Default: 0. Possible values: 0, 1 or 2.
* input_status_retain: Input status message retain. Default unchecked.

##### Payload:
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

![Output Configuration Screenshot][config_output]

* output_status_enabled: Enable OpenMotics to publish output status messages on the MQTT broker.
* output_status_topic_format: Output status topic format. Structure: `topic_prefix/{id}/topic_suffix`. Default: `openmotics/output/{id}/status`.
* output_status_qos: Output status message quality of service. Default: 0. Possible values: 0, 1 or 2.
* output_status_retain: Output status message retain. Default unchecked.

##### Payload:
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

![Event Configuration Screenshot][config_event]

* event_status_enabled': Enable OpenMotics to publish event status messages on the MQTT broker.
* event_status_topic_format: Event status topic format. Structure: `topic_prefix/{id}/topic_suffix`. Default: `openmotics/event/{id}/status`.
* event_status_qos: Event status message quality of service. Default: 0. Possible values: 0, 1 or 2.
* event_status_retain: Event status message retain. Default unchecked.

##### Payload:
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

More information on how to send these OpenMotics events can be found on the [OpenMotics wiki: Action Types](http://wiki.openmotics.com/index.php/Action_Types), number 60.


#### Temperature sensor state

##### Configuration:

![Temperature Configuration Screenshot][config_temperature]

* temperature_status_enabled: Enable OpenMotics to publish temperature sensor status messages on the MQTT broker.
* temperature_status_topic_format: Temperature sensor status topic format. Structure: `topic_prefix/{id}/topic_suffix`. Default: `openmotics/temperature/{id}/status`.
* temperature_status_qos: Temperature status message quality of service. Default: 0. Possible values: 0, 1 or 2.
* temperature_status_retain: Temperature status message retain. Default unchecked.

##### Payload:
```
{
    "id": "<sensor id>",
    "name": "<sensor name>",
    "value": <temperature in degrees Celsius>,
    "timestamp": <ISO format timestamp in {timezone}>
}
```

##### Example:
* Topic configuration: temperature_status_topic_format = openmotics/temperature/{id}/state
* Actual topic: openmotics/temperature/3/state
* Actual payload:
```
{
    "id": 3,
    "name": "Garage",
    "value": 14.5,
    "timestamp": "2020-04-08T15:51:25.707819+00:00"
}
```


#### Humidity sensor state

##### Configuration:

![Humidity Configuration Screenshot][config_humidity]

* humidity_status_enabled: Enable OpenMotics to publish humidity sensor status messages on the MQTT broker.
* humidity_status_topic_format: Humidity sensor status topic format. Structure: `topic_prefix/{id}/topic_suffix`. Default: `openmotics/humidity/{id}/status`.
* humidity_status_qos: Humidity status message quality of service. Default: 0. Possible values: 0, 1 or 2.
* humidity_status_retain: Humidity status message retain. Default unchecked.

##### Payload:
```
{
    "id": "<sensor id>",
    "name": "<sensor name>",
    "value": <relative humidity in %>,
    "timestamp": <ISO format timestamp in {timezone}>
}
```

##### Example:
* Topic configuration: humidity_status_topic_format = openmotics/humidity/{id}/state
* Actual topic: openmotics/humidity/3/state
* Actual payload:
```
{
    "id": 3,
    "name": "Garage",
    "value": 56.5,
    "timestamp": "2020-04-08T15:51:25.707819+00:00"
}
```


#### Brightness sensor state

##### Configuration:

![Brightness Configuration Screenshot][config_brightness]

* brightness_status_enabled: Enable OpenMotics to publish brightness sensor status messages on the MQTT broker.
* brightness_status_topic_format: Brightness sensor status topic format. Structure: `topic_prefix/{id}/topic_suffix`. Default: `openmotics/brightness/{id}/status`.
* brightness_status_qos: Brightness status message quality of service. Default: 0. Possible values: 0, 1 or 2.
* brightness_status_retain: Brightness status message retain. Default unchecked.

##### Payload:
```
{
    "id": "<sensor id>",
    "name": "<sensor name>",
    "value": <brightness in lux>,
    "timestamp": <ISO format timestamp in {timezone}>
}
```

##### Example:
* Topic configuration: brightness_status_topic_format = openmotics/brightness/{id}/state
* Actual topic: openmotics/brightness/3/state
* Actual payload:
```
{
    "id": 3,
    "name": "Garage",
    "value": 596.62,
    "timestamp": "2020-04-08T15:51:25.707819+00:00"
}
```


#### Realtime Power state

##### Configuration:

![Power Configuration Screenshot][config_power]

* power_status_enabled: Enable OpenMotics to publish realtime power messages on the MQTT broker.
* power_status_topic_format: Realtime power topic format. Structure: `topic_prefix/{module_id}/topic_middle/{sensor_id}/topic_suffix`. Default: `openmotics/power/{module_id}/{sensor_id}/status`.
* power_status_qos: Realtime power message quality of service. Default: 0. Possible values: 0, 1 or 2.
* power_status_retain: Realtime power message retain. Default unchecked.
* power_status_poll_frequency: Polling frequency for power status in seconds. Default: 60, minimum: 10.

##### Payload:
```
{
    "module_id": "<energy module id>",
    "sensor_id": "<sensor id>",
    "name": "<sensor name>",
    "current": <current in Amps>,
    "frequency": <frequency in Hertz>,
    "power": <power in Watts>,
    "voltage": <voltage in Volt>,
    "timestamp": <ISO format timestamp in {timezone}>
}
```

##### Example:
* Topic configuration: power_status_topic_format = openmotics/power/{module_id}/{sensor_id}/state
* Actual topic: openmotics/power/1/11/state
* Actual payload:
```
{
    "module_id": 1,
    "sensor_id": 11,
    "name": "Kitchen",
    "current": 0.23376594483852386,
    "frequency": 49.99971389770508,
    "power": 43.19911575317383,
    "voltage": 240.39581298828125,
    "timestamp": "2020-04-08T15:51:25.707819+00:00"
}
```

#### Total Energy state

##### Configuration:

![Energy Configuration Screenshot][config_energy]

* energy_status_enabled: Enable OpenMotics to publish total energy messages on the MQTT broker.
* energy_status_topic_format: Total energy topic format. Structure: `topic_prefix/{module_id}/topic_middle/{sensor_id}/topic_suffix`. Default: `openmotics/energy/{module_id}/{sensor_id}/status`.
* energy_status_qos: Total energy message quality of service. Default: 0. Possible values: 0, 1 or 2.
* energy_status_retain: Total energy message retain. Default unchecked.
* energy_status_poll_frequency: Polling frequency for energy status in seconds. Default: 3600 (1 hour), minimum: 10.

##### Payload:
```
{
    "module_id": "<energy module id>",
    "sensor_id": "<sensor id>",
    "name": "<sensor name>",
    "counter_day": "<energy used in peak tariff time in KWh>",
    "counter_night": "<energy used in off peak tariff time in KWh>",
    "timestamp": <ISO format timestamp in {timezone}>
}
```

##### Example:
* Topic configuration: energy_status_topic_format = openmotics/energy/{module_id}/{sensor_id}/state
* Actual topic: openmotics/energy/1/11/state
* Actual payload:
```
{
    "module_id": 1,
    "sensor_id": 11,
    "name": "Kitchen",
    "counter_day": 108161,
    "counter_night": 137309,
    "timestamp": "2020-04-08T15:58:10.320326+00:00"
}
```


### Command messages

The system can also be controlled by letting clients publish to a given topic.

#### Set Output

A topic to which this plugin will subscribe to can be defined. Publishing to this topic will control OpenMotics outputs (relays, lights).

##### Configuration:

![Set Output Configuration Screenshot][config_output_command]

* Topic: topic_prefix/+/topic_suffix
* Payload: value
For Outputs, the value should be an integer (0-100) representing the desired output state. In case the Output is a relay, only 0 and 100 are considered valid values.
Note the difference in syntax when compared to the topics this plugin publishes to: a plus sign is used as the wildcard where the output id would go.

##### Example:
* Topic configuration: output_command_topic = openmotics/output/+/set
* Actual topic: openmotics/output/8/set
* Actual payload: 100

### Logging messages

#### Configuration:

![Logging topic Configuration Screenshot][config_logging]

This topic is mainly used for debugging purposes.

* Topic: can_be/any/topic
* Payload: log message

### Timezone

#### Configuration:

![Logging topic Configuration Screenshot][config_timezone]

Timezone used in payloads

[config_broker]: images/config_broker.png "Configuration broker"
[config_input]: images/config_input.png "Configuration inputs"
[config_output]: images/config_output.png "Configuration outputs"
[config_event]: images/config_event.png "Configuration events"
[config_temperature]: images/config_temperature.png "Configuration temperature sensors"
[config_humidity]: images/config_humidity.png "Configuration humidity sensors"
[config_brightness]: images/config_brightness.png "Configuration brightness sensors"
[config_power]: images/config_power.png "Configuration realtime power"
[config_energy]: images/config_energy.png "Configuration total energy"
[config_output_command]: images/config_output_command.png "Configuration output command"
[config_logging]: images/config_logging_topic.png "Configuration logging topic"
[config_timezone]: images/config_timezone.png "Configuration timezone"
