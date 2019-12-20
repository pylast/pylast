#!/usr/bin/env python
from setuptools import find_packages, setup

version_dict = {}
with open("src/pylast/version.py") as f:
    exec(f.read(), version_dict)
    version = version_dict["__version__"]


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
    extras_require={
        "tests": ["flaky", "pytest", "pytest-cov", "pytest-random-order", "pyyaml"]
    },
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
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
    ],
    keywords=["Last.fm", "music", "scrobble", "scrobbling"],
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    license="Apache2",
)

# End of file
