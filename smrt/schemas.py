"""Convenience methods for handling schemas."""

import logging as loggr
import json
import os

from jsonschema import validate, Draft6Validator, ValidationError, SchemaError

log = loggr.getLogger('smrt')

_cache = {}


def _read_schema(schema_file):
    try:
        fh = open(schema_file, 'rb')
        content = fh.read()
        fh.close()
    except IOError as err:
        log.error('Could not read file: %s', err)
        raise RuntimeError('Could not read file: %s' % err)

    return content


def _exist_and_read(path, file):
    log.debug('Looking for schema "%s" in %s', file, path)

    schema_file = os.path.join(path, file)

    if not os.path.isfile(schema_file):
        return None

    log.debug('Schema "%s" found in %s', file, path)
    schema = _read_schema(schema_file)
    try:
        return json.loads(schema)  # if valid json, return it
    except json.JSONDecodeError as err:
        log.warning('Invalid schema file format: %s', err)
        raise RuntimeError('Invalid schema file format: %s', err)


def read_schema(schema_name, path=None):
    """Read schema from schema name.

    Looking for schemas as following, will take first match:
    1. path if given
    2. ``SMRT`` module.
    3. current working directory.
    4. on smrt.novafaen.se

    Schemas are cached in memory.

    :param schema_name: ``String`` schema name
    :param path: ``String`` path to schemas
    :returns: ``String`` schema if found, ``None`` if not found
    """
    if schema_name in _cache:
        return _cache[schema_name]

    # 1) in path
    if path is not None:
        schema = _exist_and_read(path, schema_name)
        if schema is not None:
            _cache[schema_name] = schema
            return schema

    # 2) in smrt module
    schema_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'schemas')

    schema = _exist_and_read(schema_path, schema_name)
    if schema is not None:
        _cache[schema_name] = schema
        return schema

    # 3) in current working directory
    schema_path = os.getcwd()

    schema = _exist_and_read(schema_path, schema_name)
    if schema is not None:
        _cache[schema_name] = schema
        return schema

    # 3.5) go down in current working directory
    directories = []
    for root, dirs, files in os.walk(os.getcwd()):
        if len(dirs) == 0:
            directories.append(root)

    log.debug('found %i subdirectories in working dir', len(directories))

    for directory in directories:
        schema = _exist_and_read(directory, schema_name)
        if schema is not None:
            _cache[schema_name] = schema
            return schema

    # 4) online on smrt.novafaen.se
    # todo: implement this when novafaen.se support this

    log.debug('No schema "%s" file found', schema_name)
    return None


def validate_json(instance, schema):
    """Validate json against schema.

    :param instace: ``Dict`` json to be verified
    :param schema: ``Dict`` json schema draft 6
    :returns: ``Boolean`` json valid to schema
    """
    try:
        Draft6Validator.check_schema(schema)
    except SchemaError as err:
        log.debug('Schema does not conform to json schema draft 6: %s', err)
        return False

    try:
        validate(instance=instance, schema=schema)
    except ValidationError as err:
        log.debug('Instance does not conform to schema: %s', err)
        return False

    return True
