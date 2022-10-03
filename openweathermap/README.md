# OpenWeatherMap

An OpenWeatherMap plugin for sending temperature and humidity values, based on a location, to virtual sensors registered by the plugin.

## Work in progress

This is a work in progress, but has already been extensively tested in a real home. This plugin is shared for community feedback and/or contributions. Please only use this plugin if you know what you're doing and if you're willing to debug issues you might encounter. As always, feel free to report issues and/or make pull requests.

## Configuration

### Plugin

1. [Register](https://home.openweathermap.org/users/sign_up) on [OpenWeatherMap](https://openweathermap.org/current) and fill in `api_key`
2. Enter your `latitude` and `longitude` values
3. Set a `time_offset` in minutes for OpenWeatherMap (`time_offset` is >= 0)
4. Save