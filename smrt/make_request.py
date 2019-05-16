"""Request wrapper around requests module.

Handles errors and re-throw in a `smrt` way.
"""

from json import dumps as jsonify
import logging as loggr

import requests
from requests.exceptions import MissingSchema, ConnectionError
from werkzeug.exceptions import GatewayTimeout, InternalServerError, BadGateway

log = loggr.getLogger('smrt')
log.setLevel(loggr.DEBUG)


def make_request(method, url, headers=None, timeout=30, body=None):
    """Wrap requests call to hande ´smrt´ exceptions.

    :returns: response object
    """
    method = method.upper()
    if method not in ['GET', 'POST', 'PUT', 'DELETE']:
        raise RuntimeError('unsupported rest method: %s' % method)

    try:
        if isinstance(body, dict):
            body = jsonify(body)  # cast to string if dictionary
        response = requests.request(method, url, headers=headers, timeout=timeout, data=body)
    except (MissingSchema, ConnectionError, InternalServerError) as err:
        if isinstance(err, MissingSchema):
            raise RuntimeError('invalid uri for rest request: %s (origin: %s)' % (method, err))
        elif isinstance(err, ConnectionError):
            raise GatewayTimeout('received no response from %s (origin: %s)' % (url, err))

    if response.status_code == 500:
        raise BadGateway(response.text)

    print(response.text)
    return response


def get(url, headers=None, timeout=30, body=None):
    """Wrap make_request with method `GET`, see `make_request` documentation for usage."""
    return make_request('GET', url, headers=headers, timeout=timeout, body=body)


def put(url, headers=None, timeout=30, body=None):
    """Wrap make_request with method `PUT`, see `make_request` documentation for usage."""
    return make_request('PUT', url, headers=headers, timeout=timeout, body=body)


def post(url, headers=None, timeout=30, body=None):
    """Wrap make_request with method `POST`, see `make_request` documentation for usage."""
    return make_request('POST', url, headers=headers, timeout=timeout, body=body)


def delete(url, headers=None, timeout=30, body=None):
    """Wrap make_request with method `DELETE`, see `make_request` documentation for usage."""
    return make_request('DELETE', url, headers=headers, timeout=timeout, body=body)
