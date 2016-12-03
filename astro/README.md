# Astro

An astronomical plugin, for providing the system with astronomical data (e.g. whether it's day or not, based on sunset/sunrise).

## Configuration

```
config_description = [{'name': 'location',
                       'type': 'str',
                       'description': 'A location which will be passed to Google to fetch location, timezone and elevation.'},
                      {'name': 'horizon_bit',
                       'type': 'int',
                       'description': 'The bit that indicates whether it is day. -1 when not in use.'},
                      {'name': 'civil_bit',
                       'type': 'int',
                       'description': 'The bit that indicates whether it is day or civil twilight. -1 when not in use.'},
                      {'name': 'nautical_bit',
                       'type': 'int',
                       'description': 'The bit that indicates whether it is day, civil or nautical twilight. -1 when not in use.'},
                      {'name': 'astronomical_bit',
                       'type': 'int',
                       'description': 'The bit that indicates whether it is day, civil, nautical or astronomical twilight. -1 when not in use.'},
                      {'name': 'bright_bit',
                       'type': 'int',
                       'description': 'The bit that indicates the brightest part of the day, -1 when not in use.'},
                      {'name': 'bright_offset',
                       'type': 'int',
                       'description': 'The offset (in minutes) after sunrise and before sunset on which the bright_bit should be set.'}]
```

## Location

This plugin uses the [Google Maps Geocoding](https://developers.google.com/maps/documentation/geocoding/start) API to translate
a human-friendly location name into longitude and latitude. This means that the location configured in this plugin must be understood by
the API. By default, "Brussels,Belgium" will be used.

To validate the location, enter ```http://maps.googleapis.com/maps/api/geocode/json?address=<location>``` in a browser, where ```<location>``` is
changed with the location of your choice.

## Times

This plugin uses [Sunrise Sunset](http://sunrise-sunset.org/)'s API to load the different times (e.g. when the sun rises)

## Bits

This plugin can set 5 different bits. You can configure the desired bit or set them to ```-1``` when not in use. There is a bit indicating
whether it's day, civil twilight, nautical twilight and astronomical twilight. One (or a combination of multiple) bit(s) can be used in for
example Group Actions to decide on certain things.

An extra special bit (```bright_bit```) is available to indicate a smaller part of the day, for example, when something needs to be
executed when it's at least X minutes after sunrise. The offset after sunrise and before sunset can be set in the ```bright_offset``` configuration.

The below image will give you some insights in how to read/interprete the different bits. More can be read on [Wikipedia](https://en.wikipedia.org/wiki/Twilight).

![Twilight](https://upload.wikimedia.org/wikipedia/commons/thumb/d/d2/Twilight_subcategories.svg/500px-Twilight_subcategories.svg.png)

Image by TWCarlson [CC BY-SA 3.0](http://creativecommons.org/licenses/by-sa/3.0) or [GFDL](http://www.gnu.org/copyleft/fdl.html), via Wikimedia Commons

The different bits:

* The ```horizon_bit``` is ```1``` when it's day.
* The ```civil_bit``` is ```1``` when it's day or civil twilight
* The ```nautical_bit``` is ```1``` when it's day, civil twilight or nautical twilight
* The ```astronomical_bit``` is ```1``` when it's day, civil twilight, nautical twilight or astronomical twilight.

The extra bit ```bright_bit``` is ```1``` when it's a given amount of minutes after sunrise and before sunset.

When no bits are set, it's night.

A few examples, where ```bright_offset``` is set to ```60```.

* It's right before noon:
  * ```bright_bit```: ```1```
  * ```horizon_bit```: ```1```
  * ```civil_bit```: ```1```
  * ```nautical_bit```: ```1```
  * ```astronomical_bit```: ```1```
* It's daylight, but sunrise was only 15 minutes ago:
  * ```bright_bit```: ```0```
  * ```horizon_bit```: ```1```
  * ```civil_bit```: ```1```
  * ```nautical_bit```: ```1```
  * ```astronomical_bit```: ```1```
* The sun remains below the horizon (nautical twilight or darker), and is now at it's highest point:
 * ```bright_bit```: ```0```
  * ```horizon_bit```: ```0```
  * ```civil_bit```: ```0```
  * ```nautical_bit```: ```1```
  * ```astronomical_bit```: ```1```
* It's two hours before sunset, but the sun barely sets (it just slips below the horizon for a few hours)
  * ```bright_bit```: ```1```
  * ```horizon_bit```: ```1```
  * ```civil_bit```: ```1```
  * ```nautical_bit```: ```0```
  * ```astronomical_bit```: ```0```

## Usage example

For example, a door sensor need to switch on a light when a door is opened. However, it only has to switch on the light when it's dark outside.
Let's say as soon as it's nautical twilight or darker (night). When it's day or civil twilight the light doesn't need to be switched on.
