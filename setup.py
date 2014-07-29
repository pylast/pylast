#!/usr/bin/env python

from distutils.core import setup

import os


def get_build():
    path = "./.build"

    if os.path.exists(path):
        fp = open(path, "r")
        build = eval(fp.read())
        if os.path.exists("./.increase_build"):
            build += 1
        fp.close()
    else:
        build = 1

    fp = open(path, "w")
    fp.write(str(build))
    fp.close()

    return str(build)

setup(
    name="pylast",
    version="1.0." + get_build(),
    author="Amr Hassan <amr.hassan@gmail.com>",
    description="A Python interface to Last.fm (and other API compatible social networks)",
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
