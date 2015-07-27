# Pushetta

A Pushetta (http://www.pushetta.com) plugin for pushing events through Pushetta

## Work in progress

This is a work in progress and might or might not be suitable for real-life usage. This plugin is shared for community
feedback and/or contributions. Please only use this plugin if you know what you're doing and if you're willing to debug
issues you might encounter. As always, feel free to report issues and/or make pull requests.

## Todo

* Add more information in the readme
* Add support for multiple inputs/channels/messages

## Usecases

* A doorbell (to make sure you know when somebody is at the door, even if you're in the garden)

## Configuration

```
config_description = [{'name': 'api_key',
                       'type': 'str',
                       'description': 'Your API key.'},
                      {'name': 'input_id',
                       'type': 'int',
                       'description': 'The ID of the input that will trigger the event.'},
                      {'name': 'channel',
                       'type': 'str',
                       'description': 'The channel to push the event to.'},
                      {'name': 'message',
                       'type': 'str',
                       'description': 'The message to be send.'}]
```
