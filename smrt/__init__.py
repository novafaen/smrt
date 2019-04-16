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

from .smrt import app, SMRTApp, smrt
from .smrt import request, make_response, jsonify

__all__ = ['app', 'SMRTApp', 'smrt', 'request', 'make_response', 'jsonify']
