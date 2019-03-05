import logging
from socket import socket, AF_INET, SOCK_DGRAM, SOL_SOCKET, SO_BROADCAST
from threading import Thread


class Broadcaster:
    _port = None

    def __init__(self, port=28015):
        self._port = port

    def broadcast(self, message):
        if not isinstance(message, str):
            message = str(message)

        logging.debug('broadcasting "%s" on port %i', message, self._port)

        sock = socket(AF_INET, SOCK_DGRAM)
        sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
        sock.sendto(bytes(message, 'utf-8'), ('255.255.255.255', self._port))


class Listener(Thread):
    _port = None
    _execute = None
    _callback = None

    def __init__(self, callback, port=28015):
        super().__init__()

        self._callback = callback
        self._port = port

    def stop(self):
        self._execute = False

    def run(self):
        sock = socket(AF_INET, SOCK_DGRAM)
        sock.bind(('', self._port))  # bind to local address

        logging.info('listening for broadcast on port %i', self._port)

        self._execute = True

        while self._execute:
            message = sock.recvfrom(1024)  # message cannot be bigger than this!
            data, (sender, port) = message
            logging.debug('received broadcast message "%s", from %s:%i', data, sender, port)

            self._callback(data)

        logging.info('stopped listening to broadcast port %i', self._port)
        sock.close()
