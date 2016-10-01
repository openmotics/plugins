# Pushsafer

A Pushsafer (http://www.pushsafer.com) plugin for pushing events through Pushsafer

## Work in progress

This is a work in progress and might or might not be suitable for real-life usage. This plugin is shared for community
feedback and/or contributions. Please only use this plugin if you know what you're doing and if you're willing to debug
issues you might encounter. As always, feel free to report issues and/or make pull requests.

## Todo

* Add more information in the readme

## Usecases

* A doorbell (to make sure you know when somebody is at the door, even if you're in the garden)

## Configuration

```
config_description = [{'name': 'privatekey',
                       'type': 'str',
                       'description': 'Your private or alias key from pushsafer.com.'},
                      {'name': 'input_id',
                       'type': 'int',
                       'description': 'The ID of the input that will trigger the event.'},
                      {'name': 'title',
                       'type': 'str',
                       'description': 'The title of the message.'},
                      {'name': 'message',
                       'type': 'str',
                       'description': 'The message to be send.'}
					   {'name': 'device',
                       'type': 'str',
                       'description': 'The device or device group id where the message to be send.'}
					   {'name': 'icon',
                       'type': 'str',
                       'description': 'The icon which is displayed with the message (a number 1-98).'}
					   {'name': 'sound',
                       'type': 'str',
                       'description': 'The notification sound of message (a number 0-28 or empty).'}
					   {'name': 'vibration',
                       'type': 'str',
                       'description': 'How often the device should vibrate (a number 1-3 or empty).'}]
```
