# -*- coding: utf-8 -*-

"""SMRT module.

This module should contain everything you need from Flask.

Exports:
- `app` that extends Flask functionality, must be imported by application.
- `SMRTApp` interface that needs to be extended by application.
- `smrt` decorator that combines Flask and Flask-Negotiate.
- `request` rest request function.
- `make_response` Flask make response function.
- `jsonify` Flask jsonify function.
"""

from .smrt import app, smrt, request, make_response, jsonify, log, \
                  ResouceNotFound
from .smrtapp import SMRTApp
from .schemas import read_schema, validate_json
from .make_request import make_request
from werkzeug.exceptions import InternalServerError, BadRequest

__all__ = ['app', 'SMRTApp', 'smrt', 'request', 'make_response', 'jsonify',
           'read_schema', 'validate_json', 'make_request',
           'InternalServerError', 'BadRequest', 'ResouceNotFound', 'log']
