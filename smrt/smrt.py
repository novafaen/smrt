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

import logging as loggr
import time
from functools import wraps

from flask import Flask, request, make_response, jsonify
from flask_negotiate import consumes, produces, NotAcceptable, UnsupportedMediaType
from werkzeug.exceptions import MethodNotAllowed, InternalServerError

from .smrtapp import SMRTApp

loggr.basicConfig(
    format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=loggr.DEBUG
)

loggr.getLogger('werkzeug').setLevel(loggr.CRITICAL)
loggr.getLogger('urllib3').setLevel(loggr.CRITICAL)

log = loggr.getLogger('smrt')


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
            body['application'] = self._app.status()

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
            log.debug('%s executed in %s ms', route, end - start)

            app.increase_successful()

            return result

        return wrapper
    return decorated


def _call_types(in_type, out_type):
    """Handle produces and/or consumes."""
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
def get_status():
    """Get status for the application since boot time.

    :returns: status respone with code 200
    """
    body = app.status()
    response = make_response(jsonify(body), 200)
    return response


@smrt('/test/error',
      produces='application/se.novafaen.smrt.test_accept.v1+json',
      consumes='application/se.novafaen.smrt.test_content_type.v1+json',
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


@app.errorhandler(NotAcceptable)
def handler_not_acceptable(error):
    """Cathes Not Acceptable errors.

    :returns: Not Acceptable error with code 406.
    """
    log.debug(error, exc_info=True)
    accept_type = ''
    if 'Accept' in request.headers and request.headers['Accept'] != '*/*':
        accept_type = request.headers['Accept']

    return app.create_error(406,
                            'Not Acceptable',
                            'Accept type \'%s\' is not served by endpoint.' % accept_type,
                            bad=True)


@app.errorhandler(UnsupportedMediaType)
def handler_unsupported_type(error):
    """Catches Unsupported Media Type errors.

    :retuens: Unsupported Media Type error with code 415.
    """
    log.debug(error, exc_info=True)
    content_type = ''
    if 'Content-Type' in request.headers:
        content_type = request.headers['Content-Type']

    return app.create_error(415,
                            'Unsupported Media Type',
                            'Content type \'%s\' cannot be handled by endpoint.' % content_type,
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
