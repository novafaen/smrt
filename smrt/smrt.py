import logging
import time

from flask import Flask, request, make_response, jsonify

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
        self._client = client

    @staticmethod
    def create_error(self, code, description, message):
        body = {
            'code': code,
            'description': description,
            'message': message
        }
        response = make_response(jsonify(body), code)
        response.headers['Content-Type'] = 'application/se.novafaen.smrt.error.v1+json'
        return response

    def version(self):
        body = {
            'smrt_version': '0.0.1',
            'time': int(time.time())  # force integer, no need to have better resolution
        }

        # add app version information
        if self._client is not None:
            app_version = self._client.version()
            body['app_version'] = app_version['app_version']
            body['application'] = app_version['application']

        return body

    def status(self):
        body = {
            'app_loaded': self._client is not None,
            'errors': self._errors,
            'warnings': self._warning,
            'bad_requests': self._bad_requests
        }

        if self._client is not None:
            app_status = self._client.status()
            body['status'] = app_status['status']

        return body


# create app
app = SMRT(__name__)


@app.errorhandler(404)
def not_found(error):
    logging.debug('Received 404 error: ' + str(error))
    body = {
        'code': 404,
        'status': 'NotFound',
        'message': 'Requested path %s does not exist.' % request.path
    }
    response = make_response(jsonify(body), 404)
    response.headers['Content-Type'] = 'application/se.novafaen.smrt.error.v1+json'
    return response


@app.route('/version')
def version():
    body = app.version()
    response = make_response(jsonify(body), 200)
    response.headers['Content-Type'] = 'application/se.novafaen.smrt.version.v1+json'
    return response


@app.route('/status')
def status():
    body = app.status()
    response = make_response(jsonify(body), 200)
    response.headers['Content-Type'] = 'application/se.novafaen.smrt.status.v1+json'
    return response


@app.route('/register/<string:service>/<string:identifier>')
def register(service, identifier):
    logging.debug('received register request %s:%s', service, identifier)

    response = make_response('', 204)
    return response


@app.errorhandler(Exception)
def all_exception_handler(error):
    logging.critical(error, exc_info=True)

    body = {
        'code': 500,
        'status': 'Internal Server Error',
        'message': 'An unexpected error has occurred, issue have been logged.'
    }
    return make_response(jsonify(body), 500)
