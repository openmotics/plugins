# Pushsafer

A Pushsafer (http://www.pushsafer.com) plugin for pushing events through Pushsafer

## Work in progress

This is a work in progress and might or might not be suitable for real-life usage. This plugin is shared for community
feedback and/or contributions. Please only use this plugin if you know what you're doing and if you're willing to debug
issues you might encounter. As always, feel free to report issues and/or make pull requests.

## Usecases

* A doorbell (to make sure you know when somebody is at the door, even if you're in the garden)

## Configuration

```
config_description = [{'name': 'privatekey',
                       'type': 'str',
                       'description': 'Your Private or Alias key.'},
                      {'name': 'input_mapping',
                       'type': 'section',
                       'description': 'The mapping between input_id and a given Pushsafer settings',
                       'repeat': True,
                       'min': 1,
                       'content': [{'name': 'input_id',
                                    'type': 'int',
                                    'description': 'The ID of the (virtual) input that will trigger the event.'},
                                   {'name': 'message',
                                    'type': 'str',
                                    'description': 'The message to be send.'},
                                   {'name': 'title',
                                    'type': 'str',
                                    'description': 'The title of message to be send.'},
                                   {'name': 'device',
                                    'type': 'str',
                                    'description': 'The device or device group id where the message to be send.'},
                                   {'name': 'icon',
                                    'type': 'str',
                                    'description': 'The icon which is displayed with the message (a number 1-98).'},
                                   {'name': 'sound',
                                    'type': 'int',
                                    'description': 'The notification sound of message (a number 0-28 or empty).'},
                                   {'name': 'vibration',
                                    'type': 'str',
                                    'description': 'How often the device should vibrate (a number 1-3 or empty).'},
                                   {'name': 'url',
                                    'type': 'str',
                                    'description': 'A URL or URL scheme: https://www.pushsafer.com/en/url_schemes'},
                                   {'name': 'urltitle',
                                    'type': 'str',
                                    'description': 'the URLs title'},
                                   {'name': 'time2live',
                                    'type': 'str',
                                    'description': 'Integer number 0-43200: Time in minutes after which message automatically gets purged.'}]}]
```

The ```privatekey``` can be obtained on your [dashboard](https://www.pushsafer.com/dashboard).

The ```input_mapping``` contains a mapping between the ```input_id``` (the ID of the OpenMotics (virtual) Input), and a series of settings
related to Pushsafer. The information about these values can be found at the [API documentation](https://www.pushsafer.com/en/pushapi)
