"""Request wrapper around requests module.

Handles errors and re-throw in a `smrt` way.
"""

from flask import has_request_context, g

import logging as loggr
from json import dumps as jsonify
from uuid import uuid4

import requests
from requests.exceptions import MissingSchema, ConnectionError
from werkzeug.exceptions import GatewayTimeout, InternalServerError, BadGateway

log = loggr.getLogger('smrt')


def make_request(method, url, headers=None, timeout=30, body=None):
    """Wrap requests call to hande ´smrt´ exceptions.

    :returns: response object
    """
    method = method.upper()
    if method not in ['GET', 'POST', 'PUT', 'DELETE']:
        raise RuntimeError('unsupported rest method: %s' % method)

    if headers is None:
        headers = {}

    # not prettiest solution
    headers['X-Request-Id'] = g.request_id if has_request_context() else str(uuid4())
    log.debug('[%s] %s %s', headers['X-Request-Id'], method, url)

    try:
        if isinstance(body, dict):
            body = jsonify(body)  # cast to string if dictionary
        response = requests.request(
            method, url, headers=headers, timeout=timeout, data=body)
    except (MissingSchema, ConnectionError, InternalServerError) as err:
        log.warning('unexpected issue when connecting to %s: %s', url, err)
        if isinstance(err, MissingSchema):
            raise RuntimeError(
                f'invalid uri for rest request: {method} (origin: {err})')
        elif isinstance(err, ConnectionError):
            raise GatewayTimeout(
                f'received no response from "{url}" (origin: {err})')

    if response.status_code == 500:
        raise BadGateway(response.text)

    return response


def get(url, headers=None, timeout=30, body=None):
    """Wrap make_request as `GET`, see `make_request` documentation."""
    return make_request('GET',
                        url, headers=headers, timeout=timeout, body=body)


def put(url, headers=None, timeout=30, body=None):
    """Wrap make_request as `PUT`, see `make_request` documentation."""
    return make_request('PUT',
                        url, headers=headers, timeout=timeout, body=body)


def post(url, headers=None, timeout=30, body=None):
    """Wrap make_request as `POST`, see `make_request` documentation."""
    return make_request('POST',
                        url, headers=headers, timeout=timeout, body=body)


def delete(url, headers=None, timeout=30, body=None):
    """Wrap make_request as `DELETE`, see `make_request` documentation."""
    return make_request('DELETE',
                        url, headers=headers, timeout=timeout, body=body)
