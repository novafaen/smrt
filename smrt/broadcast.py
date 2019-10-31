"""Local area network broadcast and listener.

Can be used to broadcast and listen for component lifecycles or
communicate configuration.
"""

import logging as loggr

from socket import socket, AF_INET, SOCK_DGRAM, SOL_SOCKET, SO_BROADCAST
from threading import Thread

log = loggr.getLogger('smrt')


class Broadcaster:
    """Simple broadcast class.

    Initiate and broadcast, simple as that.
    """

    _port = None

    def __init__(self, port=28015):
        """Create with broadcast port.

        :param port: port number, default 28015.
        """
        self._port = port

    def broadcast(self, message):
        """Broadcast message.

        :param message: message to be broadcasted.
        """
        if not isinstance(message, str):
            message = str(message)

        log.debug('broadcasting on port %s, message: "%s"',
                  self._port, message)

        sock = socket(AF_INET, SOCK_DGRAM)
        sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
        sock.sendto(bytes(message), ('255.255.255.255', self._port))


class Listener(Thread):
    """Simple broadcast listener class.

    Initiate and listen, simple as that.
    """

    _port = None
    _execute = None
    _callback = None

    def __init__(self, callback, port=28015):
        """Create with port and callback function.

        :param callback: callback function upon broadcast message.
        :param port: port to listen to, default 28015.
        """
        Thread.__init__(self)

        self._callback = callback
        self._port = port

    def stop(self):
        """Stop listening for broadcast messages."""
        self._execute = False

    def run(self):
        """Start thread that listen for messages.

        Should be started via `Thread.start()`.
        """
        sock = socket(AF_INET, SOCK_DGRAM)
        sock.bind(('', self._port))  # bind to local address

        log.info('listening on broadcast port %i', self._port)

        self._execute = True

        while self._execute:
            message = sock.recvfrom(1024)  # todo: bigger?
            data, (sender, port) = message
            log.debug('received broadcast message "%s", from %s:%i',
                      data, sender, port)

            self._callback(data)

        log.info('stopped listening to broadcast port %i', self._port)
        sock.close()
