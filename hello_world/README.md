# Hello world plugin
The hello world plugin is designed to give an initial feel on how to create a plugin and add it to a gateway.
The purpose will be to "say hello" based on changes in the configuration.

For this demo we will use:
- this folder
- a local development gateway: setup for this can be found [here](https://github.com/openmotics/gateway#running-locally)

The hello world plugin consists of 3 parts:
- Minimal boilerplate for plugin
- configuration
- upload and update plugin to gateway

## Minimal example
The code in `plugin_logs.py` and `main.py` contain minimal code to have a running plugin. Mainly it implements the `_get_config_description`, `get_config` and `set_config` methods.

This concerns mainly about the configuration and logging of the plugin.
The plugin does not have metrics and therefor the configuration and interfaces do not include any metric components. 

## Configuration
This sample configuration is also added in the `main.py`.
```
    name = 'HelloWorldPlugin'
    version = '1.0.0'
    interfaces = [('config', '1.0')]

    # configuration
    config_description = [{'type': 'str',
                           'description': 'Give your first name',
                           'name': 'first_name'}]
    default_config = {'first_name': "my_test_name"} # optional default arguments
```

## Start a plugin
Now we will assume that we have a gateway available. This can be mocked by running a local version of the OpenMotics-services running on a gateway.
More info on how to start a gateway can be found [here](https://github.com/openmotics/gateway#running-locally).

- package the plugin with ``` ./package.sh hello_world```
- this will generate a checksum and a packaged version of the plugin
- login to the portal (eg. localhost:8088)
- Go to settings/Apps and upload the package. 
- After a while, the package and corresponding configuration should be loaded.

From now on, the plugin is running and configurations can be adapted.

To upload a new version of the plugin, repeat the same steps as above.

## Next steps
As next steps, we can run the `say_hello` function on a schedule.
