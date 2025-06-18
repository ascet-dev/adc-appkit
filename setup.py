#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from setuptools import setup


def get_long_description():
    with open('README.md', encoding='utf8') as f:
        return f.read()


def get_packages(package):
    return [
        dirpath
        for dirpath, dirnames, filenames in os.walk(package)
        if os.path.exists(os.path.join(dirpath, '__init__.py'))
    ]


setup(
    name='appkit',
    version='0.1.0',
    url='https://github.com/ascet-dev/adc-appkit',
    python_requires='>=3.8',
    install_requires=[
    ],
    license='MIT',
    description='FastAPI application toolkit with component-based architecture',
    long_description=get_long_description(),
    long_description_content_type='text/markdown',
    packages=get_packages('appkit'),
    include_package_data=True,
    data_files=[('', [])],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Framework :: FastAPI',
    ],
    zip_safe=False,
)
