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
                       'description': 'The bit that indicates whether it is day, civil, nautical or astronomical twilight. -1 when not in use.'}]
```

## Location

The location configured must be one that can be understood by Google, as Google is used to translate it to location
(longitude and latitude), timezone and elevation. By default, "Brussels,Belgium" will be used.

To validate the location, enter ```http://maps.googleapis.com/maps/api/geocode/json?address=<location>``` in a browser, where ```<location>``` is
changed with the location of your choice.

## Bits

This plugin can set 4 different bits. You can configure the desired bit or set them to ```-1``` when not in use. There is a bit indicating
whether it's day, civil twilight, nautical twilight and astronomical twilight. One (or a combination of multiple) bit(s) can be used in for
example Group Actions to decide on certain things.

The below image will give you some insights in how to read/interprete the different bits. More can be read on [Wikipedia](https://en.wikipedia.org/wiki/Twilight).

![Twilight](https://upload.wikimedia.org/wikipedia/commons/thumb/d/d2/Twilight_subcategories.svg/500px-Twilight_subcategories.svg.png)

Image by TWCarlson [CC BY-SA 3.0](http://creativecommons.org/licenses/by-sa/3.0) or [GFDL](http://www.gnu.org/copyleft/fdl.html), via Wikimedia Commons

The different bits:

* The ```horizon_bit``` is ```1``` when it's day.
* The ```civil_bit``` is ```1``` when it's day or civil twilight
* The ```nautical_bit``` is ```1``` when it's day, civil twilight or nautical twilight
* The ```astronomical_bit``` is ```1``` when it's day, civil twilight, nautical twilight or astronomical twilight.

When no bits are set, it's night.

## Usage example

For example, a door sensor need to switch on a light when a door is opened. However, it only has to switch on the light when it's dark outside.
Let's say as soon as it's nautical twilight or darker (night). When it's day or civil twilight the light doesn't need to be switched on.

The bit that is needed here is the ```civil_bit```. When set (```1```), it's either day or civil twilight. When it's cleared (```0```) it's nautical twilight
or darker (astronomical twilight and night). An IF-structure can be used in a Group Action that only swtiches on the light when the civil bit is cleared.
