# Astro

An astronomical plugin for providing the system with astronomical data (e.g. whether it's day or not, based on sunset/sunrise).
A configuration example is described at the bottom of the page.

This documentation is for the Astro plugin version 1.x. Users currently using Astro 0.x are
strongly advised to update and change all required configurations and/or Automations. 

This plugin is powered by: https://sunrise-sunset.org/

## Configuration

### Coordinates

The key element for configuring the plugin are the coordinates of where the Gateway/Brain/Brain+ module is located. These
can be obtained by using a service such as Google Maps (see example below) or other services.

### Basic configuration

The easiest way to use the Astro plugin is to execute Automations (Group Actions) on certain sun
locations (with optional offset). These can be used to turn on/off outputs, or perform various other actions.

### Advanced configuration

It's also possible to set or clear a Validation Bit at certain sun locations (with optional offset). These validation bits
can be used in for example advanced Input configuration, or to directly enable/disable inputs or outputs.

## Sun location

The system uses a set of specific sun locations, all of which can be offset with time in minutes.

* **Solar noon**
    * Highest point of the sun, regardless of whether the sun is above the horizon or not
* **Sunrise/sunset**
    * This is the technical 0 degrees point. When the sun actually passes the visible horizon depends on the horizon features such as mountains and will be different from this point.
* **Civil dusk/dawn**
    * Civil twilight is when typically no artificial lights are needed for outdoor activities
* **Nautical dusk/dawn**
* **Astronomical dusk/dawn**
    * Astronomical twilight is the darkest of the 3 twilight phases. It is the earliest stage of dawn in the morning and the last stage of dusk in the evening

![Twilight](https://upload.wikimedia.org/wikipedia/commons/thumb/d/d2/Twilight_subcategories.svg/500px-Twilight_subcategories.svg.png)

Image by TWCarlson [CC BY-SA 3.0](http://creativecommons.org/licenses/by-sa/3.0) or [GFDL](http://www.gnu.org/copyleft/fdl.html), via Wikimedia 
Commons. More can be read on [Wikipedia](https://en.wikipedia.org/wiki/Twilight).

## Basic Configuration example
In this example we will automate a shutter group to open at sunrise and close 30 minutes after sunset

Steps:
* Install the Astro plugin on cloud.openmotics.com > Settings > Gateway Settings > Apps > Astro > 'Install'. The page may need to be refreshed to show the configuration options.
* Retrieve the exact coordinates from Google Maps in ```lat, long``` format for the location you want to base the Astro plugin on (i.e. your installation's location). In Google Maps, right click the map and select the first option (coordinates). This will copy those coördinates to your clipboard. For this example we'll use ```51.05654785025445, 3.7011630634177504```.
* Create the Automations on cloud.openmotics.com > Settings > Gateway Settings > Automations:
    * Sunrise: This Automation contains the block 'Let shutter group X up' (with X the shutter group ID as configured on the Setup > Outputs page). Click the 'Finish' button & note down that Automation's ID (between brackets in the list). In this example we'll assume ID ```6```.
    * Sunset: This Automation contains the block 'Let shutter group X down'. Also note down its ID, in this example we'll assume ID ```8```
* Navigate to the Settings > Gateway Settings > Apps > Astro page and fill out the following fields:
    * coordinates: in our example ```51.05654785025445, 3.7011630634177504```
    * Under 'basic_configuration' click the 'add section' button:
        * group_action: ```6``` (the ID for the sunrise Automation)
        * sun_location: select ```sunrise```
        * offset: ```0```
    * Click the 'add section' button again:
        * group_action: ```8``` (the ID for the sunset Automation)
        * sun_location: select ```sunset```
        * offset: ```30```
    * Click the Save button
    * After refreshing the page, the 'Logs' panel of the Astro plugin will show the current configuration
