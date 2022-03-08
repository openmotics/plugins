import sys
from logging import Handler


class PluginLogHandler(Handler):

    def __init__(self, log_function=None):
        """
        If log_function is not specified, sys.stderr.write is used.
        """
        Handler.__init__(self)
        if log_function is None:
            log_function = sys.stderr.write
        self.log_function = log_function

    def emit(self, record):
        try:
            msg = self.format(record)
            log_function = self.log_function
            fs = "%s"  # fs = "%s\n"
            log_function(fs % msg.encode("UTF-8"))
            self.flush()  # not implemented afaik
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)
