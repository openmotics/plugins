# SMA WebConnect plugin

This plugin reads out a SunnyBoy SMA inverter and pushes various metrics.

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

First, a sample rate needs to be configured. This is how frequent the plugin should
poll the inverter for data. A typical value is somewhere between `30` and `120` (seconds).

Second, debug logging can be enabled/disabled.

Then, one or more inverters can be added. You need the ip address of the inverter (as used above, but without `https://`)
together with the password mentioned above.

After saving the configuration, the plugin wil start reading data.

### License

This plugin is licensed under the AGPL v3 license.
