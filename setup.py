from setuptools import find_packages, setup

with open("README.md") as f:
    long_description = f.read()


def local_scheme(version):
    """Skip the local version (eg. +xyz of 0.6.1.dev4+gdf99fe2)
    to be able to upload to Test PyPI"""
    return ""


setup(
    name="pylast",
    description="A Python interface to Last.fm and Libre.fm",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Amr Hassan <amr.hassan@gmail.com> and Contributors",
    author_email="amr.hassan@gmail.com",
    url="https://github.com/pylast/pylast",
    license="Apache2",
    keywords=["Last.fm", "music", "scrobble", "scrobbling"],
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    use_scm_version={"local_scheme": local_scheme},
    setup_requires=["setuptools_scm"],
    extras_require={
        "tests": ["flaky", "pytest", "pytest-cov", "pytest-random-order", "pyyaml"]
    },
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: Apache Software License",
        "Topic :: Internet",
        "Topic :: Multimedia :: Sound/Audio",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
    ],
)
