import logging
import time

from flask import Flask, request, make_response, jsonify
from flask_negotiate import consumes, produces, NotAcceptable, UnsupportedMediaType
from werkzeug.exceptions import MethodNotAllowed

logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.DEBUG
)


class SMRT(Flask):
    def __init__(self, *args, **kwargs):
        super(SMRT, self).__init__(*args, **kwargs)

        self._client = None
        self._warning = 0
        self._errors = 0
        self._bad_requests = 0

    def register_client(self, client):
        if not isinstance(client, SMRTApp):
            raise NotImplementedError('Client registration failed, client does not implement SMRTApp interface')

        self._client = client

    @staticmethod
    def create_error(code, description, message):
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
            'time': int(time.time()),  # force integer, no need to have better resolution
            'status': {
                'errors': self._errors,
                'warnings': self._warning,
                'bad_requests': self._bad_requests
            }
        }

        if self._client is not None:
            body['application'] = self._client.status()

        return body


class SMRTApp:
    def status(self):
        raise NotImplemented('Application is missing status implementation')

    @staticmethod
    def client_name():
        raise NotImplemented('Application is missing client_name implementation')


# create app
app = SMRT(__name__)


@app.route('/status')
@produces('application/se.novafaen.smrt.status.v1+json')
def status():
    body = app.status()
    response = make_response(jsonify(body), 200)
    return response


@app.route('/test/error')
@produces('application/se.novafaen.smrt.test_accept.v1+json')
@consumes('application/se.novafaen.smrt.test_content_type.v1+json')
def test():
    raise RuntimeError('Should raise internal server error')


@app.errorhandler(Exception)
def all_exception_handler(error):
    logging.critical(error, exc_info=True)

    body = {
        'code': 500,
        'status': 'Internal Server Error',
        'message': 'An unexpected error has occurred.'
    }
    return make_response(jsonify(body), 500)


@app.errorhandler(NotAcceptable)
def handle_invalid_usage(error):
    accept_type = ''
    if 'Accept' in request.headers:
        accept_type = request.headers['Accept']
    logging.debug('Not Acceptable, %s, Accept=%s', request.path, accept_type)

    body = {
        'code': 406,
        'status': 'Not Acceptable',
        'message': 'Accept type \'%s\' is not served.' % accept_type
    }
    return make_response(jsonify(body), 406)


@app.errorhandler(UnsupportedMediaType)
def handle_invalid_usage(error):
    content_type = ''
    if 'Content-Type' in request.headers:
        content_type = request.headers['Content-Type']
    logging.debug('Unsupported Media Type, %s, Content-type=%s', request.path, content_type)

    body = {
        'code': 415,
        'status': 'Unsupported Media Type',
        'message': 'Content type \'%s\' cannot be handled.' % content_type
    }
    return make_response(jsonify(body), 415)


@app.errorhandler(404)
def not_found(error):
    return handle_method_not_allowed(error)  # throw method not allowed for not found errors


@app.errorhandler(MethodNotAllowed)
def handle_method_not_allowed(error):
    body = {
        'code': 405,
        'status': 'MethodNotAllowed',
        'message': 'No method %s exist.' % request.path
    }
    response = make_response(jsonify(body), 404)
    response.headers['Content-Type'] = 'application/se.novafaen.smrt.error.v1+json'
    return response
