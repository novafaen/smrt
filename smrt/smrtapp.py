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

    Application that is registered with SMRT needs to extend `SMRTApp` interface.
    """

    config = None
    broadcaster = None
    listener = None

    def __init__(self, schemas_path, schema):
        """Create and initiate SMRTApp.

        Will read `configuration.json` from current working directory.

        :param config_schema: ``String`` json schema, optional.
        """
        if 'SMRT_CONFIGURATION' in os.environ:
            configuration_path = os.environ['SMRT_CONFIGURATION']
            log.info('will use application configuration: %s', configuration_path)

        if not os.path.isfile(configuration_path):
            log.info('No configuration file found: %s', configuration_path)
            return  # exit on no configuration

        log.debug('Configuration file exist')

        try:
            fh = open(configuration_path, 'rb')
            config = loads(fh.read())
            fh.close()
        except (IOError, ValidationError) as err:
            log.error('Could not read configuration file: %s', err)
            raise RuntimeError('Could not read configuration file: %s', configuration_path)

        # validate json schema if given
        if schema is not None:
            schema = read_schema(schema, path=schemas_path)

            if schema is not None:
                validate_json(config, schema)
        else:
            log.warning('Configuration file found, but no schema supplied')

        log.info('Configuration file read and verified')

    def broadcast(self, message):
        """Broadcast message to local broadcast address.

        :param message: content to be broadcasted.
        """
        if self.broadcaster is None:
            self.broadcaster = Broadcaster()

        self.broadcaster.broadcast(message)

    def listen(self, callback):
        """Register callback function for received broadcasts.

        :param callback: function callback on received broadcast.
        """
        if self.listener is None:
            self.listener = Listener(callback)

        self.listener.start()

    def status(self):
        """Return application status object.

        :returns: status object.
        """
        raise NotImplementedError('Application is missing status implementation')

    @staticmethod
    def application_name():
        """Return application name.

        :returns: application name as string.
        """
        raise NotImplementedError('Application is missing application_name implementation')
