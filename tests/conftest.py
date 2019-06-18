# -*- coding: utf-8 -*-
import inspect
import logging
import os
import subprocess
import time

import docker
import pytest

logger = logging.getLogger(__name__)

CUR_PATH = inspect.getfile(inspect.currentframe())
ROOT_DIR = os.path.dirname(CUR_PATH) + "/.."


def pytest_addoption(parser):
    parser.addoption("--ci", action="store_true", default=False)


@pytest.fixture(scope="session")
def oef_addr() -> str:
    """The IP address pointing to the OEF Node to use during the tests."""
    return "127.0.0.1"


@pytest.fixture(scope="session")
def oef_port() -> int:
    """The port of the connection to the OEF Node to use during the tests."""
    return 10000


def _stop_oef_search_images():
    client = docker.from_env()
    for container in client.containers.list():
        if "fetchai/oef-search:latest" in container.image.tags:
            container.stop()


@pytest.fixture(scope="session")
def network_node(oef_addr, oef_port, pytestconfig):
    if pytestconfig.getoption("ci"):
        logger.warning("Skipping creation of OEF Docker image...")
        yield
        return

    _stop_oef_search_images()
    client = docker.from_env()

    logger.info(ROOT_DIR + '/oef_search_pluto_scripts')
    ports = {'20000/tcp': ("0.0.0.0", 20000), '30000/tcp': ("0.0.0.0", 30000), '{}/tcp'.format(oef_port): ("0.0.0.0", oef_port)}
    volumes = {ROOT_DIR + '/oef_search_pluto_scripts': {'bind': '/config', 'mode': 'rw'}}
    c = client.containers.run("fetchai/oef-search:v4",
                              "node no_sh --config_file /config/node_config.json",
                              detach=True, ports=ports, volumes=volumes)

    # wait for the setup...
    logger.info("Setting up the OEF node...")
    attempt = 0
    success = False
    while not success and attempt < 15:
        attempt += 1
        logger.info("Attempt {}...".format(attempt))
        oef_healthcheck = subprocess.Popen(["python3", ROOT_DIR + "/sandbox/oef_healthcheck.py", "127.0.0.1", "10000"])
        oef_healthcheck.wait()
        oef_healthcheck.terminate()
        if oef_healthcheck.returncode == 0:
            success = True
        else:
            logger.info("OEF not available yet - sleeping for 1 second...")
            time.sleep(1.0)

    if not success:
        c.stop()
        c.remove()
        pytest.fail("OEF doesn't work. Exiting...")

    logger.info("Done!")
    time.sleep(1.0)
    yield
    logger.info("Stopping the OEF node...")
    c.stop()
    c.remove()
