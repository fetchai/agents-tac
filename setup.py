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
import fileinput
import glob
import os

import re
import shutil
import subprocess

from setuptools import setup, find_packages, Command
from setuptools.command.build_py import build_py as _build_py
from setuptools.command.develop import develop as _develop


PACKAGE_NAME="tac"


class protoc(Command):
    """A custom command to generate Python Protobuf modules from oef-core-protocol"""

    description = "Generate Python Protobuf modules from protobuf files specifications."
    user_options = [
        ("--proto_path", None, "Path to the `oef-core-protocol` folder.")
    ]

    def run(self):
        command = self._build_command()
        self._run_command(command)
        self._fix_import_statements_in_all_protobuf_modules()

    def _run_command(self, command):
        self.announce("Running %s" % str(command))
        subprocess.check_call(command)

    def initialize_options(self):
        """Set default values for options."""
        self.proto_path = os.path.join("tac-cpp", "proto")

    def finalize_options(self):
        """Post-process options."""
        assert os.path.exists(self.proto_path), (
                'Directory %s does not exist.' % self.proto_path)

    def _find_protoc_executable_path(self):
        result = shutil.which("protoc")

        if result is None or result == "":
            raise EnvironmentError("protoc compiler not found.")
        return result

    def _build_command(self):
        protoc_executable_path = self._find_protoc_executable_path()
        command = [protoc_executable_path] + self._get_arguments()
        return command

    def _get_arguments(self):
        arguments = []
        arguments.append("--proto_path=%s" % self.proto_path)
        arguments.append("--python_out=tac")
        arguments += glob.glob(os.path.join(self.proto_path, "*.proto"))
        return arguments

    def _fix_import_statements_in_all_protobuf_modules(self):
        generated_protobuf_python_modules = glob.glob(os.path.join("oef", "*_pb2.py"))
        for filepath in generated_protobuf_python_modules:
            self._fix_import_statements_in_protobuf_module(filepath)

    def _fix_import_statements_in_protobuf_module(self, filename):
        for line in fileinput.input(filename, inplace=True):
            line = re.sub("^(import \w*_pb2)", "from . \g<1>", line)
            # stdout redirected to the file (fileinput.input with inplace=True)
            print(line, end="")


class build_py(_build_py):
    """Custom build_py command."""

    def run(self):
        self.run_command("protoc")
        _build_py.run(self)


class develop(_develop):
    """Custom develop command."""

    def run(self):
        self.run_command("protoc")
        _develop.run(self)


here = os.path.abspath(os.path.dirname(__file__))
about = {}
with open(os.path.join(here, PACKAGE_NAME, '__version__.py'), 'r') as f:
    exec(f.read(), about)

with open('README.md', 'r') as f:
    readme = f.read()


setup(
    name=about['__title__'],
    description=about['__description__'],
    version=about['__version__'],
    author=about['__author__'],
    url=about['__url__'],
    long_description=readme,
    packages=find_packages(),
    cmdclass={
        'protoc': protoc,
        'build_py': build_py,
        'develop': develop,
    },
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT Software License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    install_requires=[
        "oef",
        "numpy",
        "matplotlib",
        "flask"
    ],
    dependency_links=[
        "git+ssh://git@github.com/uvue-git/oef-sdk-python.git#egg=oef",
    ],
    tests_require=["tox"],
    entry_points={
        'console_scripts': ["tac=tac.__main__:main"],
    },
    zip_safe=False,
    include_package_data=True,
    license=about['__license__'],
)

