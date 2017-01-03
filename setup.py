#!/usr/bin/env python2.7

from setuptools import setup
import os

setup(
    name = "pyirobot",
    version = "1.0.4",
    author = "Carl Seelye",
    author_email = "cseelye@gmail.com",
    description = "Control iRobot cleaning robots",
    license = "MIT",
    keywords = "irobot roomba",
    packages = ["pyirobot"],
    url = "https://github.com/cseelye/pyirobot",
    long_description = open(os.path.join(os.path.dirname(__file__), "README.rst")).read(),
    install_requires = [
        "enum34>=1.1.6",
        "requests>=2.12.3",
    ]
)
