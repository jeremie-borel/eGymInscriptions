#!/usr/bin/env python
# -*- coding: utf-8 -*-

from io import open

from setuptools import find_packages, setup

setup(
    name='einscriptions',
    version='0.1',
    description='Parser pour les einscriptions',
    long_description='',
    author=u'blj',
    url='https://github.com/jeremie-borel/eGymInscriptions',
    # download_url='',
    license=None,
    packages=find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,
    #packages=['minibus','appsettings','libs'],
    install_requires=[
        'lxml>=3.7.3',
        ],
    include_package_data=True,
    zip_safe=False,                 # because we're including static files
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
