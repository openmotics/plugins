# Fibaro

A Fibaro plugin, for controlling devices in a Fibaro Home Center (lite)

## Configuration

```
config_description = [{'name': 'ip',
                       'type': 'str',
                       'description': 'The IP of the Fibaro Home Center (lite) device. E.g. 1.2.3.4'},
                      {'name': 'username',
                       'type': 'str',
                       'description': 'Username of a user with the required access.'},
                      {'name': 'password',
                       'type': 'str',
                       'description': 'Password of the user.'},
                      {'name': 'mapping',
                       'type': 'str',
                       'description': 'A JSON formatted single-line string containing the Event Code - Action mapping. See README.md for more information.'}]
```

## Fibaro API

In the current version, the plugin will call the following API where ```<ip>``` is replaced by the configured ip address.

```
http://<ip>/api/callAction
```

## Events

The OpenMotics system must be configured to send Events using [Basic Action 60](http://wiki.openmotics.com/index.php/Action_Types)

## Mapping

The configuration section has a JSON formatted string with a dictionary-like structure containing a mapping with on the key-side the
Event Code as configured in the Basic Action, and in the value side another dictionary with the parameters that must be passed to the
Fibaro API.

An example of a mapping string (with added line breaks for reading purposes)

```
{
    "1": {
        "deviceID": 13,
        "name": "turnOn"
    },
    "2": {
        "deviceID": 13,
        "name": "turnOff"
    }
}
```

The same JSON string, on one line (as it should be configured)

```
{"1": {"deviceID": 13, "name": "turnOn"}, "2": {"deviceID": 13, "name": "turnOff"}}
```

When for example event 2 is triggered, following API will be executed, which will cause device 13 to be turned off.

```
GET http://<ip>/api/callAction?deviceID=13&name=turnOff
```

## Configuration in OpenMotics

[Group Actions](http://wiki.openmotics.com/index.php/Group_Action) can be configured to send the required Events. These Group Actions
can then be linked to buttons, or included in other Group Actions. Below are the steps to configure these Group Actions via the Maintenance Mode CLI

First, connect in Maintenance Mode
```
[openmotics]$ connect
Connecting...
Opening VPN connection...
VPN connected !
Opening maintenance socket...
Starting maintenance mode, waiting for other actions to complete ...
[openmotics]$
```

Then, load the list of already configured Group Actions

```
[openmotics]$ group list
000 Ventilation 1
001 Ventilation 2
002 Ventilation 3
[openmotics]$
```

There are already three Group Actions configured. Now, the new Group Actions need to be configured

```
[openmotics]$ group name write 3 Fibaro SW1 On
[openmotics]$
```

The name is now defined, now the actions need to be configured that need to be executed by the Group Action

```
[openmotics]$ group write 3 0 60 1
[openmotics]$
```

The parameters ```60 1``` (meaning Basic Action 60 (send Event) with argument 1) is written to line 0 of Group Action 3. We can verify this

```
[openmotics]$ group read 3
00 060 001
01 255 255
02 255 255
03 255 255
04 255 255
05 255 255
06 255 255
07 255 255
08 255 255
09 255 255
10 255 255
11 255 255
12 255 255
13 255 255
14 255 255
15 255 255
[openmotics]$
```

The first entry of Group Action 3 will now execute Basic Action 60, with argument 1. The first Group Action is configured

```
[openmotics]$ group list
000 Ventilation 1
001 Ventilation 2
002 Ventilation 3
003 Fibaro SW1 On
[openmotics]$
```

Repeat for the second Group Action, making sure to configure it for sending Event 2
