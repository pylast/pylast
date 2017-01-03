#!/usr/bin/env python
from setuptools import setup, find_packages


setup(
    name="pylast",
    version="1.7.0",
    author="Amr Hassan <amr.hassan@gmail.com>",
    install_requires=['six'],
    # FIXME This can be removed after 2017-09 when 3.3 is no longer supported
    # and pypy3 uses 3.4 or later, see
    # https://en.wikipedia.org/wiki/CPython#Version_history
    extras_require={
        ':python_version=="3.3"': ["certifi"],
    },
    tests_require=['mock', 'pytest', 'coverage', 'pep8', 'pyyaml', 'pyflakes'],
    description=("A Python interface to Last.fm and Libre.fm"),
    author_email="amr.hassan@gmail.com",
    url="https://github.com/pylast/pylast",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: Apache Software License",
        "Topic :: Internet",
        "Topic :: Multimedia :: Sound/Audio",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
    ],
    keywords=["Last.fm", "music", "scrobble", "scrobbling"],
    packages=find_packages(exclude=('tests*',)),
    license="Apache2"
)

# End of file
