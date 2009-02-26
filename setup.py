#!/usr/bin/env python

from distutils.core import setup

import pylast

setup(name = pylast.__name__,
      version = pylast.__version__,
      author = pylast.__author__,
	  description = pylast.__doc__,
      author_email = pylast.__email__,
      url='http://code.google.com/p/pylast/',
      py_modules= ("pylast",)
)
