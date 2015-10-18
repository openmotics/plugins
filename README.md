# OpenMotics Gateway Plugins

## Contents

Repository containing the gateway plugins. It currently contains the following plugins:

* flooding - A plugin that measures the current on a power port and switches an output if the current is higher then a threshold for 10 minutes.
* mqtt-client - An MQTT client to broadcast/send various events/messages to the MQTT broker which can be consumed by other hard- or software.
* pushetta - A plugin for sending an event to Pushetta (http://www.pushetta.com/) when an input is pressed.
* influxdb - A plugin for sending output/input events to InfluxDB

## Contribution

If you'd like to add your own plugin, please take note of the following rules/guidelines:
* Create a separate directory for your plugin
* Add a license header to all your files and/or add a LICENSE.txt file to your plugin's folder. We prefer licenses approved by the OSI (http://opensource.org/licenses). If no license is given/stated, GPLv3 is to be assumed.
* You might want to add contact information, so people can contact you directly or mention you in issues they report here on GitHub.
* Try do document your plugin as good as possible. You can do that by adding sufficient comments in the code and/or by adding a README.md file with some help in the root of your plugin's folder. Make sure any external dependencies are documented as well (e.g. you make use of a 3rd party service to send SMS messages which requires registration)

**Don't hesitate to send us pull requests with your own plugins.**

## Warranty

This repository contains plugins that might not be written by OpenMotics which means we can give no official support on them. However, we'll do our best to help you wherever possible. If you have any problems, please create an issue here in GitHub and mention (@<username>) the creator if known.
