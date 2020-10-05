# Tasmota HTTP

An Tasmota HTTP plugin for synchronising tasmota devices with OpenMotics virtual outputs.

## Work in progress

This is a work in progress, but has already been extensively tested in a real home. This plugin is shared for community feedback and/or contributions. Please only use this plugin if you know what you're doing and if you're willing to debug issues you might encounter. As always, feel free to report issues and/or make pull requests.

## Configuration

### Add a virtual output

First you will need to add a virtual output. For that, use the command line from the local or cloud web portal.
According to the [wiki](https://wiki.openmotics.com/index.php/Virtual_Outputs), virtual outputs can be created from the command line.

```shell
# check for errors before adding a virtual output
[openmotics]$ error list ;if there are errors, clean them with error clear command.
# create a virtual output; it should return OK
[openmotics]$ add virtual module o
OK
# check again for errors
[openmotics]$ error list
# that's it
# you now have 8 new outputs available to use
```

### Plugin

1. Add the refresh interval (in seconds) to update all tasmota devices on `refresh_interval` field
2. On `tasmota_mapping` click on `Add section`
3. Add a `label` to uniquely identify this device
4. Add the device IP address on `ip_address`
5. If the tasmota device is authenticated fill in `username` and `password`
6. Pick one output id from the 8 newly created from previous step (i.e. 60)
7. If you've more tasmota devices to synchronise, repeat step 2 to 6.
8. Save

On Logs section, Tasmota HTTP plugin will become enable and it will print the initial tasmota state and any future changes.