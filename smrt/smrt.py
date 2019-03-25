import json
import logging
import time
import os
from functools import wraps

from flask import Flask, request, make_response, jsonify
from flask_negotiate import consumes, produces, NotAcceptable, UnsupportedMediaType
from werkzeug.exceptions import MethodNotAllowed, InternalServerError

from smrt.broadcast import Broadcaster, Listener

logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.DEBUG
)


class SMRT(Flask):
    def __init__(self, *args, **kwargs):
        super(SMRT, self).__init__(*args, **kwargs)

        self._client = None  # client app running on top of SMRT

        self._requests_total = 0
        self._requests_successful = 0
        self._requests_warning = 0
        self._requests_error = 0
        self._requests_bad = 0

    def register_client(self, client):
        if not isinstance(client, SMRTApp):
            raise NotImplementedError('Client registration failed, client does not implement SMRTApp interface')

        self._client = client

    def increase_successful(self):
        self._requests_successful += 1
        self._requests_total += 1

    def create_error(self, code, description, message, warning=False, error=False, bad=False):
        if warning:
            self._requests_warning += 1
        if error:
            self._requests_error += 1
        if bad:
            self._requests_bad += 1

        self._requests_total += 1

        body = {
            'code': code,
            'description': description,
            'message': message
        }
        response = make_response(jsonify(body), code)
        response.headers['Content-Type'] = 'application/se.novafaen.smrt.error.v1+json'
        return response

    def status(self):
        body = {
            'smrt': {
                'smrt_version': '0.0.1',
                'app_loaded': self._client is not None,
            },
            'server_time': int(time.time()),  # force integer, no need to have better resolution
            'status': {
                'amount_successful': self._requests_successful,
                'amount_warning': self._requests_warning,
                'amount_error': self._requests_error,
                'amount_bad': self._requests_bad,
                'amount_total': self._requests_total
            }
        }

        if self._client is not None:
            body['application'] = self._client.status()

        return body


class SMRTApp:
    config = None
    broadcaster = None
    listener = None

    def __init__(self):
        config_filename = os.path.join(os.path.dirname(os.getcwd()), 'configuration.json')

        if os.path.isfile(config_filename):
            logging.info('[smrt] configuration file found: %s', config_filename)

            config_raw = None
            try:
                fh = open(config_filename, 'rb')
                config_raw = fh.read()
                fh.close()
            except IOError as err:
                logging.error('[smrt] could not read configuration file: %s', err)

            try:
                self.config = json.loads(config_raw)
                logging.debug('[smrt] successfully parsed %i characters from configuration file', len(config_raw))
            except json.JSONDecodeError as err:
                logging.error('[smrt] could parse configuration file: %s', err)
        else:
            logging.info('[smrt] no configuration file found')

    def broadcast(self, message):
        if self.broadcaster is None:
            self.broadcaster = Broadcaster()

        self.broadcaster.broadcast(message)

    def listen(self, callback):
        if self.listener is None:
            self.listener = Listener(callback)

        self.listener.start()

    def status(self):
        raise NotImplemented('Application is missing status implementation')

    @staticmethod
    def client_name():
        raise NotImplemented('Application is missing client_name implementation')


# create app
app = SMRT(__name__)


def smrt(route, **kwargs):
    def decorated(fn):
        smrt_produces = kwargs.get('produces', None)
        if smrt_produces is not None:
            del kwargs['produces']

        smrt_consumes = kwargs.get('consumes', None)
        if smrt_consumes is not None:
            del kwargs['consumes']

        @app.route(route, **kwargs)
        @call_types(smrt_consumes, smrt_produces)
        @wraps(fn)
        def wrapper(*wrapper_args, **wrapper_kwargs):
            start = int(round(time.time() * 1000))  # start timer

            result = fn(*wrapper_args, **wrapper_kwargs)

            end = int(round(time.time() * 1000))  # stop timer
            logging.debug('[%s ms] %s executed', end - start, route)

            app.increase_successful()

            return result

        return wrapper
    return decorated


def call_types(in_type, out_type):
    def decorated(fn):
        if in_type is not None and out_type is None:
            @consumes(in_type)
            @wraps(fn)
            def wrapper(*w_args, **w_kwargs):
                return fn(*w_args, **w_kwargs)
            return wrapper

        if in_type is None and out_type is not None:
            @produces(out_type)
            @wraps(fn)
            def wrapper(*w_args, **w_kwargs):
                return fn(*w_args, **w_kwargs)
            return wrapper

        if in_type is not None and out_type is not None:
            @consumes(in_type)
            @produces(out_type)
            @wraps(fn)
            def wrapper(*w_args, **w_kwargs):
                return fn(*w_args, **w_kwargs)
            return wrapper

        @wraps(fn)
        def wrapper(*w_args, **w_kwargs):
            return fn(*w_args, **w_kwargs)
        return wrapper

    return decorated


@smrt('/status',
      produces='application/se.novafaen.smrt.status.v1+json')
def status():
    body = app.status()
    response = make_response(jsonify(body), 200)
    return response


@smrt('/test/error',
      produces='application/se.novafaen.smrt.test_accept.v1+json',
      consumes='application/se.novafaen.smrt.test_content_type.v1+json',
      methods=['GET', 'PUT'])
def test_error():
    raise RuntimeError('Should raise internal server error')


@app.errorhandler(Exception)
def all_exception_handler(error):
    logging.critical(error, exc_info=True)

    return app.create_error(502,
                            'Bad Gateway',
                            'Received invalid response from proxy.',
                            error=True)


@app.errorhandler(InternalServerError)
def handle_internal_server_error(error):
    logging.warning(error, exc_info=True)

    return app.create_error(500,
                            'Internal Server Error',
                            'An unexpected error has occurred.',
                            error=True)


@app.errorhandler(NotAcceptable)
def handle_invalid_usage(error):
    logging.debug(error, exc_info=True)

    accept_type = ''
    if 'Accept' in request.headers and request.headers['Accept'] != '*/*':
        accept_type = request.headers['Accept']

    return app.create_error(406,
                            'Not Acceptable',
                            'Accept type \'%s\' is not served by endpoint.' % accept_type,
                            bad=True)


@app.errorhandler(UnsupportedMediaType)
def handle_invalid_usage(error):
    logging.debug(error, exc_info=True)

    content_type = ''
    if 'Content-Type' in request.headers:
        content_type = request.headers['Content-Type']

    return app.create_error(415,
                            'Unsupported Media Type',
                            'Content type \'%s\' cannot be handled by endpoint.' % content_type,
                            bad=True)


@app.errorhandler(MethodNotAllowed)
@app.errorhandler(404)
def not_found(error):
    logging.debug(error, exc_info=True)

    return app.create_error(405,
                            'Method Not Allowed',
                            'No method \'%s\' exist.' % request.path,
                            bad=True)
