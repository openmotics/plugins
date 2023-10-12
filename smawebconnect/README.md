# SMA Sensors plugin

This plugin reads out a SunnyBoy SMA inverter and registers various sensors in the gateway that can then be used throughout the OpenMotics ecosystem (e.g. automations).

### Requirements

The SMA inverter should have a `User` account. To do that, use a browser to navigate to
`https://<ip of the inverter>`. You'll get a security warning because SMA uses a self-signed
certificate but you can accept the warning.

On the login screen, select `User`. Now there are two options:
* A password field is displayed; the `User` accont already exists. If you con't know the password,
refer to your installer as he might have created it.
* The inteface informs you that a `User` does not exist, and it will guide you to the process of creating one. You'll need the
password later.

### Plugin configuration

First of all, a sample rate needs to be configured. This is how frequent the plugin should
poll the inverter(s) for data. A typical value is somewhere around `60`s or `900`s.

Furthermore, one or more inverters can be added. You need the ip address of the inverter (as used above, but without `https://`)
together with the password mentioned above.

In conclusion, the logging level can be set for further troubleshooting if needed.

After saving the configuration, the plugin wil start registering the sensors and populating the sensor values in the gateway.

### Notice

SMA is a brand of solar inverters by SMA Solar Technology AG (https://www.sma.de).
This plugin is a standalone plugin for the OpenMotics platform and is not affiliated with, nor endorsed by SMA Solar Technology AG.

SMA Solar Technology AG cannot be held responsible for any damage that might be caused by the installation/usage of this plugin.

### License

This plugin is licensed under the AGPL v3 license.
