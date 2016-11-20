# OpenMotics Gateway Plugins

## Contents

This repository contains the gateway plugins.

## Plugins

### Production ready

A plugin is considered production ready when it's been in use in a real-live production setup for quite some time,
is stable and has most bugs ironed out. These production ready plugins can be downloaded pre-packaged, see the "Download" section below.

* influxdb - A plugin for sending output/input events to InfluxDB
* fibaro - A plugin that can control fibaro hardware through a Fibaro Home Center Lite
* ventilation - A ventilation plugin, using statistical humidity data to control the ventilation
* astro - An astronomical plugin, for providing the system with astronomical data (e.g. whether it's day or not, based on the sun's location)

Third party:

* Pushsafer - A plugin for sending events (triggered by OpenMotics (virtual) Inputs) to various devices (phones, browsers, ...)

### In development

Some plugins are still a work in progress. While they might be suitable for daily usage, they might require some more attention or lack decent
documentation.

* flooding - A plugin that measures the current on a power port and switches an output if the current is higher then a threshold for 10 minutes.
* mqtt-client - An MQTT client to broadcast/send various events/messages to the MQTT broker which can be consumed by other hard- or software.
* pushetta - A plugin for sending an event to Pushetta (http://www.pushetta.com/) when an input is pressed.

## Download

The production ready plugins will be available for direct download via the releases page. Our "[latest releases](https://github.com/openmotics/plugins/releases/tag/releases)"
contain the binary ```.tgz``` plugin packages, toghether with their checksum.

When you would like your plugin to be included in these releases, please open an issue.

## Contribution

If you'd like to add your own plugin, please take note of the following rules/guidelines:
* Create a separate directory for your plugin
* Add a license header to all your files and/or add a LICENSE.txt file to your plugin's folder. We prefer licenses approved by the OSI (http://opensource.org/licenses). If no license is given/stated, GPLv3 is to be assumed.
* You might want to add contact information, so people can contact you directly or mention you in issues they report here on GitHub.
* Try do document your plugin as good as possible. You can do that by adding sufficient comments in the code and/or by adding a README.md file with some help in the root of your plugin's folder. Make sure any external dependencies are documented as well (e.g. you make use of a 3rd party service to send SMS messages which requires registration)

**Don't hesitate to send us pull requests with your own plugins.**

## Tools

This repository contains a few helper scripts for maintaining plugins:

### Packaging

The ```package.sh``` script can be used to create a tgz file that can be uploaded to the OpenMotics gateway. It will print the md5sum and the name of the resulting archive file.

Usage: ```./package.sh <plugin name>```.

Example:

```
[somebody@computer plugins]$ ./package.sh fibaro
79cfa774148ee56bcbfbd6372f53afa2  fibaro_1.2.3.tgz
[somebody@computer plugins]$
```

### Publishing

The ```publish.sh``` script can be used for uploading a plugin that was packaged before. So first, use the package script, then use the publish script.

Usage: ```./publish.sh <package> <ip/hostname of openmotics gateway> <username>```.

Example:

```
[somebody@computer plugins]$ ./publish.sh fibaro_1.2.3.tgz 192.168.0.24 john
Enter password:
Publish succeeded
[somebody@computer plugins]$
```

The gateway interface will reload and after a few seconds, the plugin will be available.

### Log watching

The ```logwatcher.py``` script can be used to watch (or ```tail -f``` if you're used to Linux) the logs of a certain plugin. Please note that plugin names should be the
plugin name as stated in the code, not the foldername as with the publish and package scripts. This logwatcher depends on a few python modules (e.g. requests).

Usage: ```./logwatcher.py <ip/hostname of openmotics gateway> <username> <plugin name>```

Example:

```
[somebody@computer plugins]$ ./logwatcher.py 192.168.0.24 john InfluxDB
Password:
2016-01-03 10:15:19.430031 - Starting InfluxDB plugin...
2016-01-03 10:15:19.431273 - InfluxDB is enabled
2016-01-03 10:15:19.432826 - Started InfluxDB plugin
2016-01-03 10:16:04.790170 - Output 28 changed to ON
2016-01-03 10:16:04.790435 - Output 28 changed to level 97
2016-01-03 10:16:04.791925 - Output 29 changed to ON
2016-01-03 10:16:04.799517 - Output 30 changed to ON
2016-01-03 10:16:04.811670 - Output 31 changed to ON
```

## Warranty

This repository contains plugins that might not be written by OpenMotics which means we can give no official support on them. However, we'll do our best to help you wherever possible. If you have any problems, please create an issue here in GitHub and mention (@<username>) the creator if known.
