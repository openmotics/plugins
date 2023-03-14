"""
A Hello world plugin
"""
import json
import logging
from time import sleep

from plugin_runtime.decorators import background_task, om_metric_data
from plugin_runtime.base import OMPluginBase, PluginConfigChecker, om_expose
if False:  # MYPY
    pass

logger = logging.getLogger(__name__)


class HelloWorldPlugin(OMPluginBase):
    """
    Hello world plugin to demonstrate minimal requirements of a plugin
    """
    name = 'HelloWorldPlugin'
    version = '1.0.4'
    interfaces = [('config', '1.0')]

    # configuration
    config_description = [{'type': 'str',
                           'description': 'Give your first name',
                           'name': 'first_name'}]
    default_config = {'first_name': "my_test_name"} # optional default arguments

    def __init__(self, webinterface, connector):
        super(HelloWorldPlugin, self).__init__(webinterface=webinterface,
                                                connector=connector)
        logger.info('Starting %s plugin %s ...', self.name, self.version)

        # Use base-class to read the config file, returns default_config if there is no config file
        self._config = self.read_config(HelloWorldPlugin.default_config)
        #  Instantiate a validator
        self._config_checker = PluginConfigChecker(HelloWorldPlugin.config_description)

        logger.info("%s plugin started", self.name)


    @om_expose
    def get_config_description(self):
        """
        Returns the config_description.
        Used to render the structure in the gateway portal.
        """
        return json.dumps(self.config_description)

    @om_expose
    def get_config(self):
        """
        Returns the (filled in) config currently loaded.
        When this is the first time, this will be the default config.
        Otherwise, the adapted version in the portal configuration will be retrieved
        """
        return json.dumps(self._config)

    @om_expose
    def set_config(self, config):
        """
        Reads and validates config values from portal and sets new config.
        """
        # read and validate
        config = json.loads(config)
        self._config_checker.check_config(config)
        # validation succeeded: set config and write out to file
        self._config = config
        self.write_config(config)

        # run the hello world as part of the config, just for demo purposes
        self.say_hello()
        return json.dumps({'success': True})

    def say_hello(self):
        name = self._config['first_name']
        logger.info(f" welcome {name}")

