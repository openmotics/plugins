# Astro

An astronomical plugin for providing the system with astronomical data (e.g. whether it's day or not, based on sunset/sunrise).
A configuration example is described ath the bottom of the page.

This documentation is for the Astro plugin version 1.x. Users currently using Astro 0.x are
strongly advised to update and change all required configurations and/or Automations.

**TODO: Remove the legacy configuration below**

## Configuration

### Coordinates

The key element for configuring the plugin are the coordinates of where the Gateway is located. These
can be obtained by using a service such as Google Maps. When double-clicking on a location, the 
URL will hold the coordinates.

For example: `https://www.google.be/maps/@51.1149958,3.7771295,13.43z`

Extracted coordinates: `51.1149958,3.7771295` (can be copied as-is in the configuration)

### Basic configuration

The easiest way to use the Astro plugin is to execute Automations (Group Actions) on certain sun
locations (with optional offset). These can be used to turn on/off outputs, or perform various other actions.

### Advanced configuration

It's also possible to set or clear a Validation Bit at certain sun locations (with optional offset). These validation bits
can be used in for example advanced Input configuration, or to directly enable/disable input or outputs.

## Sun location

The system uses a set of specific sun locations, all of which can be offset with time in minutes.

* Solar noon. Remark: Highest point of the sun, regardless of whether the sun is above the horizon or not.
* Sunrise/sunset. Remark: This is the technical 0 degrees point. When the sun actually passes the visible horizon depends on the horizon features
  such as mountains and will be different from this point. 
* Civil dusk/dawn: Remark: Civil twilight is when typically no artificial lights are needed for 
  outdoor activities
* Nautical dusk/dawn
* Astronomical dusk/dawn

![Twilight](https://upload.wikimedia.org/wikipedia/commons/thumb/d/d2/Twilight_subcategories.svg/500px-Twilight_subcategories.svg.png)

Image by TWCarlson [CC BY-SA 3.0](http://creativecommons.org/licenses/by-sa/3.0) or [GFDL](http://www.gnu.org/copyleft/fdl.html), via Wikimedia 
Commons. More can be read on [Wikipedia](https://en.wikipedia.org/wiki/Twilight).

# Astro 0.x (legacy, will be removed)

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

## Configuration example
In this example we will automate a shutter group to open 20 minutes after sunrise and close 20 minutes before sunset.

Prerequisites:
* Retrieve the exact coordinates from Google Maps in lat;long format for the location you want to base the Astro plugin on (i.e. your home's location). In Google Maps, right click the map and select 'What's Here?' to see the lat;long coordinates for that location. For this example we'll use ```51.056477;3.701103``` (note the ';' divider and no spaces inbetween!). 
* Create an Automation on portal.openmotics.com > Settings > Automations. There doesn't need to be any actions defined in it yet but we need its unique ID (shown on the Automations overview page between brackets next to each Automation). For this example we will use Automation ID ```6```.
* Verify which validation bits (0-255) are already in use by any previously created Automations. If this is the first time you hear about validation bits there will be none in use and you can select any number(s) between 0-255 for use in the plugin. For this example we only need one validation bit and we'll use validation bit ```0```.
* Install the Astro plugin on portal.openmotics.com > Settings > Plugins > Astro > 'Install'

Configuration:
* On the Astro plugin page fill out the following fields:
  * ```coordinates```: ```51.056477;3.701103``` (change this to your coordinates)
  * ```bright_bit```: ```0``` (validation bit to use, change to an available one in your installation)
  * ```bright_offset```: ```20``` (the offset in minutes after 'horizon' is reached which will in turn set the bright_bit)
  * ```group_action```: ```6``` (change this to the ID of your Automation)
  * Press the 'Save' button. If all went well the Log window on the right of the page will report 'Astro is enabled'
  ![plugin](https://wiki.openmotics.com/images/1/1b/Astroconf.png)
* Now it's time to configure the Automation. Open the Automation created in the Prerequisites section and change the configuration as follows and save it.
![plugin](https://wiki.openmotics.com/images/7/79/Astroshutterga.png)
* In order to test run the configuration and set the bits/outputs/etc. in their correct state, open the Astro plugin again and press the Save button (without changing anything).
* The Astro plugin will now continuously monitor the time of day and when one or more of the configuration bits changes trigger the Automation.
