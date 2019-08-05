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

"""Start a sandbox."""

import inspect
import os
import re
import subprocess
import sys
from typing import Optional

import docker

from templates.v1 import basic as my_agent

CUR_PATH = inspect.getfile(inspect.currentframe())
ROOT_DIR = os.path.join(os.path.dirname(CUR_PATH), "..")


class Sandbox:
    """Class to manage the sandbox."""

    def _build_sandbox(self):
        """Build sandbox."""
        sandbox_build_process = None  # type: Optional[subprocess.Popen]
        sandbox_build_process = subprocess.Popen(["docker-compose", "build"],
                                                 env=os.environ,
                                                 cwd=os.path.join(ROOT_DIR, "sandbox"))
        sandbox_build_process.wait()

    def _stop_oef_search_images(self):
        """Stop any running OEF nodes."""
        client = docker.from_env()
        for container in client.containers.list():
            if any(re.match("fetchai/oef-search", tag) for tag in container.image.tags):
                print("Stopping existing OEF Node...")
                container.stop()

    def __enter__(self):
        """Define what the context manager should do at the beginning of the block."""
        self._stop_oef_search_images()
        self._build_sandbox()

        print("Launching sandbox...")
        self.sandbox_process = subprocess.Popen(["docker-compose", "up", "--abort-on-container-exit"],
                                                env=os.environ,
                                                cwd=os.path.join(ROOT_DIR, "sandbox"))

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Define what the context manager should do after the block has been executed."""
        print("Terminating sandbox...")
        self.sandbox_process.terminate()


def wait_for_oef():
    """Wait for the OEF to come live."""
    print("Waiting for the OEF to be operative...")
    wait_for_oef = subprocess.Popen([
        os.path.join("sandbox", "wait-for-oef.sh"),
        "127.0.0.1",
        "10000",
        ":"
    ], env=os.environ, cwd=ROOT_DIR)

    wait_for_oef.wait(30)


if __name__ == '__main__':
    sys.argv += ['--name', 'my_agent', '--gui']

    with Sandbox():
        wait_for_oef()
        my_agent.main()
