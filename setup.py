# -*- coding: utf-8 -*-
"""``SMRT`` setup tools file."""

from setuptools import setup

setup(
    name='smrt',
    version='0.0.1',
    description='I am so smrt, I am so smrt... I mean S.M.A.R.T',
    author='Kristoffer Nilsson',
    author_email='smrt@novafaen.se',
    url='http://smrt.novafaen.se/',
    packages=['smrt'],
    install_requires=[
        'flask>=1.0',
        'flask-negotiate>=0.1',
        'werkzeug',
        'requests>=2.21',
        'jsonschema>=3.0'
    ],
    test_suite='tests',
    tests_require=[

    ])
