#!/usr/bin/env python
from setuptools import find_packages, setup


setup(
    name="pylast",
    version="2.0.0",
    author="Amr Hassan <amr.hassan@gmail.com>",
    install_requires=['six'],
    tests_require=['mock', 'pytest', 'coverage', 'pycodestyle', 'pyyaml',
                   'pyflakes', 'flaky'],
    description="A Python interface to Last.fm and Libre.fm",
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
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
    ],
    keywords=["Last.fm", "music", "scrobble", "scrobbling"],
    packages=find_packages(exclude=('tests*',)),
    license="Apache2"
)

# End of file
