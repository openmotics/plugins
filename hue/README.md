# Hue

A Philips Hue plugin, for controlling lights. Supports dimming and synchronizes with the Hue Bridge, so the Hue app and Hue switches can be used in combination with OpenMotics inputs (switches).

## Configuration

```
config_description = [{'name': 'api_url',
                       'type': 'str',
                       'description': 'The API URL of the Hue Bridge device. E.g. http://192.168.1.2/api'},
                      {'name': 'username',
                       'type': 'str',
                       'description': 'Hue Bridge generated username.'},
                      {'name': 'poll_frequency',
                       'type': 'int',
                       'description': 'The frequency used to pull the status of all light from the Hue bridge in seconds (0 means never)'},
                      {'name': 'output_mapping',
                       'type': 'section',
                       'description': 'Mapping between OpenMotics Virtual Outputs/Dimmers and Hue Outputs',
                       'repeat': True, 'min': 0,
                       'content': [{'name': 'output_id', 'type': 'int'},
                                   {'name': 'hue_output_id', 'type': 'int'}]}]
```

The ```api_url``` and ```username``` are used to connect to/with the Hue Bridge. The username should be generated using the API (physical access to the bridge required).
More information can be found at https://developers.meethue.com/documentation/getting-started.

The ```poll_frequency``` can be used to set the time it takes (in seconds) to pull the state for all lights from the Hue Bridge.
If set to 0, OpenMotics will not query the Hue Bridge and you will not be able to see if a light was switched on or off without using OpenMotics (using the Hue app, or Hue remote for example).

## Output mapping

Virtual Outputs or Virtual Dimmers in the OpenMotics system can be linked to Hue Outputs. This way, the OpenMotics system can control the virtual output or dimmer as any
other output, and its state will be reflected in the Hue environment.

The ```output_id``` is the OpenMotics Virtual Output or Dimmer ID, and the ```hue_output_id``` is the ID of the light in the Hue system.

### How to add a Virtual Output or Dimmer in OpenMotics

Use the OpenMotics maintenance mode to add a Virtual Output (o) and/or a Virtual Dimmer (d) module (8 Virtual Outputs or Dimmers).

```
[openmotics]$ connect
Connecting...
Opening VPN connection...
VPN connected !
Opening maintenance socket...
Starting maintenance mode, waiting for other actions to complete ...
[openmotics]$ add virtual module o
[openmotics]$ add virtual module d
[openmotics]$ 
```


## Hue API

In the current version, the plugin will call the API at ```<api_url>``` and add the username fro mthe configuration:

```
e.g.: http://192.168.1.2/api/<username>/lights/1/state
```


## Mapping

The configuration section has an array of dicts where value associated with the 'output_id' key is the OpenMotics Virtual Output or Dimmer Output ID and the value associated with the 'hue_output_id' key element is the ID of the Hue light.
An example of a mapping string (with added line breaks for reading purposes):

```
[
      {
          "output_id": 1,
          "hue_output_id": 11
      },
      {
          "output_id": 2,
          "hue_output_id": 12
      },
]
```

When output 2 is set to 'On', the following API command will be executed, which will cause Hue light 12 to be turned on:

```
Address: http://192.168.1.2/api/<username>/lights/12/state
Body: {'on':true}
Method: PUT
```

When output 1 is switched on and dimmed to 50%, the following API command will be executed, which will cause Hue light 11 to be dimmed to 50%:

```
Address: http://192.168.1.2/api/<username>/lights/11/state
Body: {'on':true,'bri':127}
Method: PUT
```