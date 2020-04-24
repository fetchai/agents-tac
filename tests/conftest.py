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

"""This module contains the tests configuration."""

import inspect
import logging
import os
# import subprocess
import shutil
import tempfile
import time

import docker
import pytest
from docker.models.containers import Container

from tac.platform.oef_health_check import OEFHealthCheck

logger = logging.getLogger(__name__)

CUR_PATH = inspect.getfile(inspect.currentframe())  # type: ignore
ROOT_DIR = os.path.join(os.path.dirname(CUR_PATH), "..")


def pytest_addoption(parser):
    """Add options to the parser."""
    parser.addoption("--ci", action="store_true", default=False)
    parser.addoption("--no-oef", action="store_true", default=False, help="Skip tests that require the OEF.")


@pytest.fixture(scope="session")
def oef_addr() -> str:
    """IP address pointing to the OEF Node to use during the tests."""
    return "127.0.0.1"


@pytest.fixture(scope="session")
def oef_port() -> int:
    """Port of the connection to the OEF Node to use during the tests."""
    return 10000


def _stop_oef_search_images():
    client = docker.from_env()
    for container in client.containers.list():
        if "fetchai/oef-search:0.7" in container.image.tags:
            container.stop()


def _wait_for_oef(max_attempts: int = 15, sleep_rate: float = 1.0):
    success = False
    attempt = 0
    while not success and attempt < max_attempts:
        attempt += 1
        logger.info("Attempt {}...".format(attempt))
        # oef_healthcheck = subprocess.Popen(["python3", ROOT_DIR + "/sandbox/oef_healthcheck.py", "127.0.0.1", "10000"])
        # oef_healthcheck.wait()
        # oef_healthcheck.terminate()
        oef_healthcheck = OEFHealthCheck("127.0.0.1", 10000)
        result = oef_healthcheck.run()
        if result:
            success = True
        else:
            logger.info("OEF not available yet - sleeping for {} second...".format(sleep_rate))
            time.sleep(sleep_rate)

    return success


def _create_oef_docker_image(oef_addr_, oef_port_) -> Container:
    client = docker.from_env()

    logger.info(ROOT_DIR + '/scripts/oef')
    ports = {'20000/tcp': ("0.0.0.0", 20000), '30000/tcp': ("0.0.0.0", 30000),
             '{}/tcp'.format(oef_port_): ("0.0.0.0", oef_port_)}
    volumes = {ROOT_DIR + '/scripts/oef': {'bind': '/config', 'mode': 'rw'}, ROOT_DIR + '/data/oef-logs': {'bind': '/logs', 'mode': 'rw'}}
    c = client.containers.run("fetchai/oef-search:0.7",
                              "/config/node_config.json",
                              detach=True, ports=ports, volumes=volumes)
    return c


@pytest.fixture(scope="session")
def network_node(oef_addr, oef_port, pytestconfig):
    """Network node initialization."""
    if pytestconfig.getoption("no_oef"):
        pytest.skip('skipped: no OEF running')
        return

    if pytestconfig.getoption("ci"):
        logger.warning("Skipping creation of OEF Docker image...")
        success = _wait_for_oef(max_attempts=10, sleep_rate=2.0)
        if not success:
            pytest.fail("OEF doesn't work. Exiting...")
        else:
            yield
            return
    else:
        _stop_oef_search_images()
        c = _create_oef_docker_image(oef_addr, oef_port)

        # wait for the setup...
        logger.info("Setting up the OEF node...")
        success = _wait_for_oef(max_attempts=10, sleep_rate=2.0)

        if not success:
            c.stop()
            c.remove()
            pytest.fail("OEF doesn't work. Exiting...")
        else:
            logger.info("Done!")
            time.sleep(1.0)
            yield
            logger.info("Stopping the OEF node...")
            c.stop()
            c.remove()
            logger.info("Stopped the OEF node.")


@pytest.fixture(scope="session", autouse=True)
def environ():
    """Set the environment."""
    d = tempfile.mkdtemp()
    os.environ["SHARED_DIR"] = d
    yield
    shutil.rmtree(d, ignore_errors=False)
