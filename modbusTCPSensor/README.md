# ModBusTCP Client

An modbusTCP client plugin for receiving sensor data from an Modbus Server.

## Work in progress

This is a work in progress and might or might not be suitable for real-life usage. This plugin is shared for community
feedback and/or contributions. Please only use this plugin if you know what you're doing and if you're willing to debug
issues you might encounter. As always, feel free to report issues and/or make pull requests.

## Configuration

```
    config_description = [{'name': 'modbus_server_ip',
                           'type': 'str',
                           'description': 'IP or hostname of the ModBus server.'},
                          {'name': 'modbus_port',
                           'type': 'int',
                           'description': 'Port of the ModBus server. Default: 502'},
                          {'name': 'debug',
                           'type': 'int',
                           'description': 'Turn on debugging (0 = off, 1 = on)'},
                          {'name': 'sample_rate',
                           'type': 'int',
                           'description': 'How frequent (every x seconds) to fetch the sensor data, Default: 60'},
                          {'name': 'sensors',
                           'type': 'section',
                           'description': 'OM sensor ID (e.g. 4), a sensor type and a Modbus Address',
                           'repeat': True,
                           'min': 0,
                           'content': [{'name': 'sensor_id', 'type': 'int'},
                                       {'name': 'sensor_type', 'type': 'enum', 'choices': ['Temperature', 
                                                                                           'Humidity', 
                                                                                           'Brightness']},
                                       {'name': 'modbus_address', 'type': 'int'},
                                       {'name': 'modbus_register_length', 'type': 'int'}]}]
```

## Virtual Sensors

Using maintenance mode the referenced sensors should be configured as being virtual sensors. For more information on how
to do so please visit our [wiki page](https://wiki.openmotics.com/index.php/Virtual_Sensors#Virtual_Sensors_.28Available_in_firmware_version_3.142.1_and_higher.29)