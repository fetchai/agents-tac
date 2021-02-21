#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ------------------------------------------------------------------------------
#
#   Copyright 2018-2019 Fetch.AI Limited
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------

"""Setup of package."""

import glob
import os

from setuptools import setup, find_packages
from typing import Dict

PACKAGE_NAME = "tac"

here = os.path.abspath(os.path.dirname(__file__))
about = {}  # type: Dict[str, str]
with open(
    os.path.join(here, PACKAGE_NAME, "__version__.py"), "r", encoding="utf-8"
) as f:
    exec(f.read(), about)

with open("README.md", "r", encoding="utf-8") as f:
    readme = f.read()


extras = {"gui": ["flask", "flask_restful", "wtforms"]}

setup(
    name=about["__title__"],
    description=about["__description__"],
    version=about["__version__"],
    author=about["__author__"],
    url=about["__url__"],
    long_description=readme,
    packages=find_packages(include=["tac*"]),
    classifiers=[
        "Environment :: Console",
        "Environment :: Web Environment",
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Operating System :: MacOS",
        "Operating System :: Microsoft",
        "Operating System :: Unix",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Communications",
        "Topic :: Internet",
        "Topic :: Scientific/Engineering",
        "Topic :: Software Development",
        "Topic :: System",
    ],
    install_requires=[
        "aea==0.1.4",
        "oef",
        "colorlog",  # TODO 'oef' dependency, to be fixed.
        "numpy",
        "python-dateutil",
        "visdom",
    ],
    tests_require=["tox"],
    extras_require=extras,
    zip_safe=False,
    include_package_data=True,
    data_files=[
        (
            "sandbox",
            ["sandbox/docker-compose.yml", "sandbox/config.json", "sandbox/.env"]
            + glob.glob("sandbox/*.py")
            + glob.glob("sandbox/*.sh"),
        ),
        ("templates/v1", glob.glob("templates/v1/*.py")),
        ("scripts/oef", glob.glob("scripts/oef/*.json")),
        ("simulation/v1", glob.glob("simulation/v1/*")),
        (
            "oef_search_pluto_scripts",
            glob.glob("oef_search_pluto_scripts/*.py")
            + glob.glob("oef_search_pluto_scripts/*.json"),
        ),
    ],
    license=about["__license__"],
)
