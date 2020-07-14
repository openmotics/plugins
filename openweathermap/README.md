# OpenWeatherMap

An OpenWeatherMap plugin for sending temperature and humidity values, based on a location, to virtual sensors.

## Work in progress

This is a work in progress, but has already been extensively tested in a real home. This plugin is shared for community feedback and/or contributions. Please only use this plugin if you know what you're doing and if you're willing to debug issues you might encounter. As always, feel free to report issues and/or make pull requests.

## Configuration

### Add a virtual sensor

First you will need to add a virtual sensor. For that, use the command line from the local or cloud web portal.
According to the [Memory model](https://wiki.openmotics.com/index.php/Memory_Model#Virtual_Sensors_.26_Thermostats_.28Page_195.29), virtual sensors and thermostats are on page 195 of the eeprom with byte 0 corresponds to virtual sensor 0 and byte 31 to virtual sensor 31. A value of 255 means the virtual sensor is disabled, and < 255 the virtual sensor is enabled.

```shell
# let's assume virtual sensor 0, so get it's value
[openmotics]$ eeprom read 195 0
255
# it's disabled, let's enabled it
[openmotics]$ eeprom write 195 0 1
# make sure value was stored properly
[openmotics]$ eeprom read 195 0
1
# let's save the eeprom changes
[openmotics]$ eeprom activate
```

### Plugin

1. [Register](https://home.openweathermap.org/users/sign_up) on [OpenWeatherMap](https://openweathermap.org/current) and fill in `api_key`
2. Enter your `latitude` and `longitude` values
3. On `main_mapping` add the sensor id that you activated previously and `time_offset` for OpenWeatherMap (`time_offset` is >= 0)
4. Save