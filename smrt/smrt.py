"""SMRT is a convenience framework build around flask.

SMRT, pronounced SMART, is a convenience framework around Flask and Flask-Negotiate.
Applications, that use SMRT should extent `SMRTApp`. This app must be registered
with SMRT using `app.register_application` function.

SMRT will give the application:
 - Basig logging.
 - Routing using @SMRT decorator.
 - Basic error handling.
 - Basic configuration file reading.
"""

from json.decoder import JSONDecodeError
import logging as loggr
from os import environ
import time
from functools import wraps

from flask import Flask, request, make_response, jsonify
from flask_negotiate import consumes, produces, NotAcceptable, UnsupportedMediaType
from werkzeug.exceptions import MethodNotAllowed, InternalServerError, BadRequest

from .smrtapp import SMRTApp
from .make_request import GatewayTimeout
from .schemas import read_schema, validate_json

log = loggr.getLogger('smrt')
log.setLevel(loggr.DEBUG)

formatter = loggr.Formatter('[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s')

sh = loggr.StreamHandler()
sh.setLevel(loggr.DEBUG)
sh.setFormatter(formatter)
log.addHandler(sh)

logfile = None if 'SMRT_LOG' not in environ else environ['SMRT_LOG']
if logfile is not None:
    log.info('logging to logfile=%s', logfile)
    fh = loggr.FileHandler(logfile)
    fh.setLevel(loggr.DEBUG)
    fh.setFormatter(formatter)
    log.addHandler(fh)

# "disable" logging from third party libraries
loggr.getLogger('werkzeug').setLevel(loggr.CRITICAL)
loggr.getLogger('urllib3').setLevel(loggr.CRITICAL)


class _SMRT(Flask):
    """Private class extending Flask with SMRT functionality."""

    def __init__(self, *args, **kwargs):
        """Create SMRT framework with Flask arguments."""
        Flask.__init__(self, *args, **kwargs)

        self._app = None  # client app running on top of SMRT

        self._requests_successful = 0
        self._requests_warning = 0
        self._requests_error = 0
        self._requests_bad = 0

        self._started = int(time.time())  # force integer

    def register_application(self, app):
        """Register an application with SMRT framework.

        :param app: application to be mounted, must be a `SMRTApp`.
        :raise NotImplementedError: If application does not extend `SMRTApp`.
        """
        if not isinstance(app, SMRTApp):
            raise NotImplementedError('Client registration failed, client does not implement SMRTApp interface')

        log.debug('application registered: %s', app.application_name())
        self._app = app

    def increase_successful(self):
        """Increase successful amount."""
        self._requests_successful += 1

    def create_error(self, code, error_type, description, warning=False, error=False, bad=False):
        """Create error response.

        :param code: HTML Error code.
        :param error_type: Error type, typically HTTP error name.
        :param description: Detailed description what went wrong.
        :param warning: Should error be counted as a warning, default `False`.
        :param error: Should error be counted as a error, default `False`.
        :param bad: Should error be counted as a bad request, default `False`.
        :returns: SMRT return type, derived from Flask return type
        """
        if warning:
            self._requests_warning += 1
        if error:
            self._requests_error += 1
        if bad:
            self._requests_bad += 1

        body = {
            'code': code,
            'error': error_type,
            'description': description
        }
        response = make_response(jsonify(body), code)
        response.headers['Content-Type'] = 'application/se.novafaen.smrt.error.v1+json'
        return response

    def status(self):
        """Return status object.

        Get the status from last time launched.
        :returns: status object
        """
        now = int(time.time())
        body = {
            'smrt': {
                'smrt_version': '0.0.1',
                'app_loaded': self._app is not None,
                'uptime': now - self._started
            },
            'server_time': now,  # force integer, no need to have better resolution
            'status': {
                'amount_successful': self._requests_successful,
                'amount_warning': self._requests_warning,
                'amount_error': self._requests_error,
                'amount_bad': self._requests_bad,
                'amount_total': self._requests_successful + self._requests_warning + self._requests_error + self._requests_bad
            }
        }

        if self._app is not None:
            app_status = self._app.status()
            if isinstance(app_status, dict) and len(app_status) == 3 and \
                    'name' in app_status and 'status' in app_status and 'version' in app_status:
                body['application'] = self._app.status()
            else:
                raise RuntimeError('app status have invalid format')

        return body


# create app (i.e. flask instance)
app = _SMRT(__name__)


def smrt(route, **kwargs):
    """Routing decorator.

    Usage:
    `@smrt(
        '/example'                          <- mandatory
        produces='application/my.type+json' <- optional
        consumes='application/my.type+json' <- optional
    )`

    For more information, see Flask routing documentation.
    """
    def decorated(fn):
        smrt_produces = kwargs.get('produces', None)
        if smrt_produces is not None:
            del kwargs['produces']

        smrt_consumes = kwargs.get('consumes', None)
        if smrt_consumes is not None:
            del kwargs['consumes']

        @app.route(route, **kwargs)
        @_call_types(smrt_consumes, smrt_produces)
        @wraps(fn)
        def wrapper(*wrapper_args, **wrapper_kwargs):
            start = int(round(time.time() * 1000))  # start timer

            result = fn(*wrapper_args, **wrapper_kwargs)

            end = int(round(time.time() * 1000))  # stop timer
            log.debug('%s executed in %s ms', request.path, end - start)

            app.increase_successful()

            return result

        return wrapper
    return decorated


def _check_content_type(schema_name, content_bytes):
    """Throw appropriate error if content is not matching schema."""
    try:
        content = content_bytes.get_json()
    except JSONDecodeError as err:
        log.debug('could not parse content: %s', err)
        raise UnsupportedMediaType('could not verify schema')

    schema = read_schema(schema_name.replace('application/', '').replace('+json', '.json'))
    if schema is None:
        raise RuntimeError('could not find schema')
    if not validate_json(content, schema):
        raise UnsupportedMediaType('could not verify schema')


def _call_types(in_type, out_type):
    """Handle produces and/or consumes."""
    def decorated(fn):
        if in_type is not None and out_type is None:
            @consumes(in_type)
            @wraps(fn)
            def wrapper(*w_args, **w_kwargs):
                _check_content_type(in_type, request)

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
                _check_content_type(in_type, request)

                return fn(*w_args, **w_kwargs)
            return wrapper

        @wraps(fn)
        def wrapper(*w_args, **w_kwargs):
            return fn(*w_args, **w_kwargs)
        return wrapper

    return decorated


@smrt('/status',
      produces='application/se.novafaen.smrt.status.v1+json')
def get_status():
    """Get status for the application since boot time.

    :returns: status respone with code 200
    """
    body = app.status()
    response = make_response(jsonify(body), 200)
    return response


@smrt('/test/error',
      methods=['GET', 'PUT'])
def get_put_error():
    """Produce Internal Server error, for testing purposes.

    :returns: Internal Server error with code 500.
    """
    raise RuntimeError('Should raise internal server error')


@app.errorhandler(Exception)
def handler_uncaught_exception(error):
    """Catches unhandeled errors and return Internal Server Error.

    :returns: Internal Server error with code 500.
    """
    log.critical(error, exc_info=True)
    return app.create_error(500,
                            'Internal Server Error',
                            'An unexpected error has occurred.',
                            error=True)


@app.errorhandler(InternalServerError)
def handler_internal_server_error(error):
    """Catches Internal Server error and rethrows as Bad Gateway.

    :returns: Bad Gateway error with code 502.
    """
    log.warning(error, exc_info=True)
    return app.create_error(502,
                            'Bad Gateway',
                            'Received invalid response from proxy.',
                            error=True)


@app.errorhandler(GatewayTimeout)
def handler_gateway_timeout_error(error):
    """Catches Internal Server error and rethrows as Bad Gateway.

    :returns: Bad Gateway error with code 504.
    """
    log.warning(error, exc_info=True)
    return app.create_error(504,
                            'Gateway Timeout',
                            'Received no response from proxy.',
                            error=True)


@app.errorhandler(NotAcceptable)
def handler_not_acceptable(error):
    """Cathes Not Acceptable errors.

    :returns: Not Acceptable error with code 406.
    """
    log.debug(error, exc_info=True)

    if 'Accept' in request.headers and request.headers['Accept'] != '*/*':
        message = 'Accept type \'{}\' is not served by endpoint.'.format(request.headers['Accept'])
    else:
        message = 'Missing Accept header.'

    return app.create_error(406,
                            'Not Acceptable',
                            message,
                            bad=True)


@app.errorhandler(UnsupportedMediaType)
def handler_unsupported_type(error):
    """Catches Unsupported Media Type errors.

    :returns: Unsupported Media Type error with code 415.
    """
    log.debug(error, exc_info=True)

    if 'Content-Type' in request.headers:
        message = 'Content type \'{}\' cannot be handled by endpoint.'.format(request.headers['Content-Type'])
    else:
        message = 'Missing Content-Type header.'

    return app.create_error(415,
                            'Unsupported Media Type',
                            message,
                            bad=True)


@app.errorhandler(BadRequest)
def handler_bad_request(error):
    """Catches Bad Request errors.

    :retuens: Bad Request error with code 400.
    """
    log.debug(error, exc_info=True)

    return app.create_error(400,
                            'Bad Request',
                            'Data does not conform to API specification.',
                            bad=True)


class ResouceNotFound(Exception):
    """Wrapper class around exception to raise ``NotFound`` errors.

    This class should be used by applications implementing ``smrt``.
    """

    def __init__(self, message, *args, **kwargs):
        """Create and initialize ``ResouceNotFound`` exception."""
        Exception.__init__(self, args, kwargs)
        self.message = message if message is not None else 'Resource does not exist.'

    def __str__(self):
        """See python documentation."""
        return self.message

    def __repr__(self):
        """See python documentation."""
        return '<ResouceNotFound message="%s">'.format(self.message)


@app.errorhandler(ResouceNotFound)
def handler_resource_not_found(error):
    """Catches Not Found errors.

    This is typically when resouce is requested that does not exist.

    :returns: Not Found error with code 404
    """
    log.debug(error.message)  # , exc_info=True)
    return app.create_error(404,
                            'NotFound',
                            str(error),
                            bad=True)


@app.errorhandler(MethodNotAllowed)
@app.errorhandler(404)
def handler_not_found(error):
    """Catches Not Found or Method Not Allowed errors, rethrows as Method Not Allowed.

    :returns: Method Not Allowed error with code 405
    """
    log.debug(error, exc_info=True)
    return app.create_error(405,
                            'Method Not Allowed',
                            'No method \'%s\' exist.' % request.path,
                            bad=True)
