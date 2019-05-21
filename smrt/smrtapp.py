"""SMRT application interface.

Applications that want to use SMRT interface must extend ``SMRTApp`` class.
"""

from json import loads
import logging as loggr
import os

from jsonschema import validate as validate_json, ValidationError

from .broadcast import Broadcaster, Listener
from .schemas import read_schema

log = loggr.getLogger('smrt')


class SMRTApp:
    """SMRT Application interface class.

    Application that is registered with SMRT needs to extend ``SMRTApp`` interface.
    """

    config = None
    broadcaster = None
    listener = None

    def __init__(self, schemas_path=None, schema=None):
        """Create and initiate SMRTApp.

        Will read `configuration.json` from current working directory.

        :param config_schema: ``string`` schemas path.
        :param schema: ``string`` schema name.
        """
        configuration_path = None
        if 'SMRT_CONFIGURATION' in os.environ:
            configuration_path = os.environ['SMRT_CONFIGURATION']
            log.info('%s, environent variable SMRT_CONFIGURATION set to "%s"', self.application_name(), configuration_path)

            if not os.path.isfile(configuration_path):
                log.warning('%s, configuration file "%s" does not exist!', self.application_name(), configuration_path)
                return  # exit on no configuration

        try:
            fh = open(configuration_path, 'rb')
            config = loads(fh.read())
            fh.close()
        except (IOError, ValidationError) as err:
            log.error('%s, could not read configuration file "%s", reason: %s', self.application_name(), configuration_path, err)
            raise RuntimeError('Could not open configuration file, reason: %s', err)

        # validate json schema if given
        if schema is not None:
            schema = read_schema(schema, path=schemas_path)

            if schema is not None:
                validate_json(config, schema)
        else:
            log.warning('%s, application is missing schema for configuration, please fix!', self.application_name())

        log.info('%s, configuration loaded and verified', self.application_name())
        self._config = config

    def broadcast(self, message):
        """Broadcast message to local broadcast address.

        :param message: ``string`` content to be broadcasted.
        """
        if self.broadcaster is None:
            self.broadcaster = Broadcaster()

        self.broadcaster.broadcast(message)

    def listen(self, callback):
        """Register callback function for received broadcasts.

        :param callback: ``function`` callback on received broadcast.
        """
        if self.listener is None:
            self.listener = Listener(callback)

        self.listener.start()

    def status(self):
        """Return application status object.

        :returns: ``dict`` status object.
        """
        raise NotImplementedError('Application is missing smrtapp status implementation')

    @staticmethod
    def application_name():
        """Return application name.

        :returns: ``string`` application name.
        """
        raise NotImplementedError('Application is missing smrtapp application_name implementation')

    @staticmethod
    def version():
        """Return application version.

        :returns: ``string`` application version.
        """
        raise NotImplementedError('Application is missing smrtapp version implementation')
