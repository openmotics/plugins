""" A plugin that measures the current on a power port and switches an output
if the current is higher then a threshold for 10 minutes.
"""

from plugins.base import om_expose, background_task, OMPluginBase, \
                         PluginConfigChecker
import simplejson as json
import smtplib
import time
import logging


logger = logging.getLogger(__name__)

class Pumpy(OMPluginBase):
    """ Plugin to prevent flooding. """

    name = 'Pumpy'
    version = '1.0.2'
    interfaces = [('config', '1.0')]

    config_descr = [
        {'name':'output_id', 'type':'int',
         'description':'The output id for the pump.'},
        {'name':'power_id', 'type':'int',
         'description':'The power id for the pump.'},
        {'name':'watts', 'type':'int',
         'description':'The average power used by the pump,'
                       ' when running (in watts).'},
        {'name':'email', 'type':'str',
         'description':'The email address to send the shutdown notification '
                       'to.'}
    ]

    def __init__(self, webinterface, connector):
        """ Default constructor, called by the plugin manager. """
        OMPluginBase.__init__(self, webinterface, connector)
        self.__last_energy = None

        # The list containing whether the pump was on the last 10 minutes
        self.__window = []
        self.__config = self.read_config()
        self.__config_checker = PluginConfigChecker(Pumpy.config_descr)

        logger.info("Started Pumpy plugin")


    @background_task
    def run(self):
        """ Background task that checks the power usage of the pump every
        minute. """
        while True:
            if self.__config is not None:
                self.__do_check()
            time.sleep(60) # Sleep one minute before checking again.

    def __do_check(self):
        """ Code for the actual check. """
        watts = self.__get_total_energy()
        if self.__last_energy == None:
            # The first time we only set the last_energy value.
            self.__last_energy = watts
        else:
            # The next times we calculate the difference: the watts
            diff = (watts - self.__last_energy) * 1000 # Convert from kWh to Wh
            pump_energy_in_one_minute = self.__config['watts'] / 60.0
            pump_on = (diff >= pump_energy_in_one_minute)
            if pump_on:
                logger.debug("Pump was running during the last minute")

            self.__window = self.__window[-9:] # Keep the last 9 'on' values
            self.__window.append(pump_on)           # Add the last 'on' value

            running_for_10_mintues = True
            for pump_on in self.__window:
                running_for_10_mintues = running_for_10_mintues and pump_on

            if running_for_10_mintues:
                logger.debug("Pump was running for 10 minutes")
                self.__pump_alert_triggered()

            self.__last_energy = watts

    def __pump_alert_triggered(self):
        """ Actions to complete when a floodding was detected. """
        # This method is called when the pump is running for 10 minutes.
        self.__stop_pump()

        # The smtp configuration below could be stored in the configuration.
        try:
            smtp = smtplib.SMTP('localhost')
            smtp.sendmail('power@localhost', [self.__config['email']],
                          'Your pump was shut down because of high power '
                          'usage !')
        except smtplib.SMTPException as exc:
            logger.exception("Failed to send email: %s" % exc)

    def __get_total_energy(self):
        """ Get the total energy consumed by the pump. """
        energy = self.webinterface.get_total_energy(None)
        # energy contains a dict of "power_id" to [day, night] array.
        energy_values = energy[str(self.__config['power_id'])]
        # Return the sum of the night and day values.
        return energy_values[0] + energy_values[1]

    def __stop_pump(self):
        """ Stop the pump. """
        self.webinterface.set_output(self.__config['output_id'], False)

    def __start_pump(self):
        """ Start the pump. """
        self.webinterface.set_output(self.__config['output_id'], True)

    @om_expose
    def get_config_description(self):
        """ Get the configuration description. """
        return json.dumps(Pumpy.config_descr)

    @om_expose
    def get_config(self):
        """ Get the current configuration. """
        config = self.__config if self.__config is not None else {}
        return json.dumps(self.__config)

    @om_expose
    def set_config(self, config):
        """ Set a new configuration. """
        config = json.loads(config)
        self.__config_checker.check_config(config)
        self.write_config(config)
        self.__config = config
        return json.dumps({'success':True})

    @om_expose
    def reset(self):
        """ Resets the counters and start the pump. """
        self.__window = []
        if self.__config is not None:
            self.__start_pump()
        return json.dumps({'success':True})
