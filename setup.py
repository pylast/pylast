#!/usr/bin/env python

from distutils.core import setup

import os


setup(
    name="pylast",
    version="1.0.0",
    author="Amr Hassan <amr.hassan@gmail.com>",
    description=("A Python interface to Last.fm "
                 "(and other API compatible social networks)"),
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
        ],
    keywords=["Last.fm", "music", "scrobble", "scrobbling"],
    py_modules=("pylast",),
    license="Apache2"
    )

# End of file
