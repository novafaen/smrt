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

    def register_client(self, client):
        self._client = client

    def version(self):
        body = {
            'smrt_version': 'test',
            'time': time.time()
        }

        # add app version information
        if self._client is not None:
            app_version = self._client.version()
            body['app_version'] = app_version['app_version']

        return body


# create app
app = SMRT(__name__)


@app.errorhandler(404)
def not_found(error):
    body = {
        'status': 'NotFound',
        'code': 404,
        'message': 'Requested URL (%s) does not exist.' % request.path,
        'derived_message': str(error)
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


@app.route('/register/<string:service>/<string:identifier>')
def register(service, identifier):
    logging.debug('received register request %s:%s', service, identifier)

    response = make_response('', 204)
    return response
