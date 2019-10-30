"""SMRT application interface.

Applications that want to use SMRT interface must extend ``SMRTApp`` class.
"""

import logging as loggr
from json import loads
import os
from pathlib import Path

from jsonschema import validate as validate_json, ValidationError

from .broadcast import Broadcaster, Listener
from .schemas import read_schema

log = loggr.getLogger('smrt')


class SMRTApp:
    """SMRT Application interface class.

    Application that is registered with SMRT needs to extend
    ``SMRTApp`` interface.
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
        config = self._read_configuration()

        if config is None:
            return  # do not validate schema if no configuration exist

        # validate json schema if given
        if schema is not None:
            schema = read_schema(schema, path=schemas_path)

            if schema is not None:
                validate_json(config, schema)
        else:
            log.warning('%s, application is missing schema for configuration',
                        self.application_name())

        log.info('%s, configuration verified and loaded',
                 self.application_name())
        self._config = config

    def _read_configuration(self):
        if 'SMRT_CONFIGURATION' not in os.environ:
            log.info('No configuration given, make sure '
                     'SMRT_CONFIGURATION environment variable is set')
            return None

        configuration_path = Path(os.environ['SMRT_CONFIGURATION'])
        log.info('%s, environent variable SMRT_CONFIGURATION set to "%s"',
                 self.application_name(), configuration_path)

        try:
            fh = configuration_path.open()
            config = loads(fh.read())
            fh.close()
        except (IOError, ValidationError) as err:  # noqa: F841 f8 is wrong
            raise RuntimeError(
                f'Could not open configuration file "{configuration_path}", '
                'reason: {err}')

        return config

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
        raise NotImplementedError(
            'Application is missing smrtapp status implementation')

    @staticmethod
    def application_name():
        """Return application name.

        :returns: ``string`` application name.
        """
        raise NotImplementedError(
            'Application is missing smrtapp application_name implementation')

    @staticmethod
    def version():
        """Return application version.

        :returns: ``string`` application version.
        """
        raise NotImplementedError(
            'Application is missing smrtapp version implementation')
