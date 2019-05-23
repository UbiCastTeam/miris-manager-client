#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
from setuptools import setup


# get version without importing module
version = None
with open(os.path.join(os.path.dirname(__file__), 'mm_client', '__init__.py'), 'r') as fo:
    for line in fo:
        if line.startswith('__version__'):
            version = line[len('__version__'):].strip(' =\'"\n\t')
            break


setup(
    name='mm_client',
    version=version,
    description='A Python3 client to use Miris Manager remote control.',
    author='UbiCast',
    url='https://github.com/UbiCastTeam/miris-manager-client',
    license='LGPL v3',
    packages=['mm_client'],
    package_data={'mm_client': ['conf.json']},
    scripts=[],
    setup_requires=['setuptools'],
    install_requires=['requests'],
)
