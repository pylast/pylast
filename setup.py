#!/usr/bin/env python
import sys

from setuptools import find_packages, setup

version_dict = {}
with open("pylast/version.py") as f:
    exec(f.read(), version_dict)
    version = version_dict["__version__"]


if sys.version_info < (3, 5):
    error = """pylast 3.0 and above are no longer compatible with Python 2.

This is pylast {} and you are using Python {}.
Make sure you have pip >= 9.0 and setuptools >= 24.2 and retry:

 $ pip install --upgrade pip setuptools

Other choices:

- Upgrade to Python 3.

- Install an older version of pylast:

$ pip install 'pylast<3.0'

For more information:

https://github.com/pylast/pylast/issues/265
""".format(
        version, ".".join([str(v) for v in sys.version_info[:3]])
    )
    print(error, file=sys.stderr)
    sys.exit(1)

with open("README.md") as f:
    long_description = f.read()


setup(
    name="pylast",
    description="A Python interface to Last.fm and Libre.fm",
    long_description=long_description,
    long_description_content_type="text/markdown",
    version=version,
    author="Amr Hassan <amr.hassan@gmail.com> and Contributors",
    author_email="amr.hassan@gmail.com",
    url="https://github.com/pylast/pylast",
    tests_require=[
        "coverage",
        "flaky",
        "mock",
        "pycodestyle",
        "pyflakes",
        "pytest",
        "pyyaml",
    ],
    python_requires=">=3.5",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: Apache Software License",
        "Topic :: Internet",
        "Topic :: Multimedia :: Sound/Audio",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
    ],
    keywords=["Last.fm", "music", "scrobble", "scrobbling"],
    packages=find_packages(exclude=("tests*",)),
    license="Apache2",
)

# End of file
