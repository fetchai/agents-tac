# -*- coding: utf-8 -*-
import time

import docker
import pytest


@pytest.fixture(scope="module")
def oef_addr() -> str:
    """The IP address pointing to the OEF Node to use during the tests."""
    return "127.0.0.1"


@pytest.fixture(scope="module")
def oef_port() -> int:
    """The port of the connection to the OEF Node to use during the tests."""
    return 3333


@pytest.fixture(scope="module")
def network_node(oef_addr, oef_port):
    client = docker.from_env()
    ports = {'20000/tcp': 20000, '30000/tcp': 30000, '{}/tcp'.format(oef_port): oef_port}
    c = client.containers.run("qati/oef-search:latest",
                              "node no_sh "
                              "--node_key Search1 "
                              "--core_key Core1 "
                              "--search_port 20000 "
                              "--core_port {} ".format(oef_port) +
                              "--dap_port 30000 "
                              "--director_api_port 40000",
                              detach=True, ports=ports)
    # wait for the setup...
    time.sleep(10.0)
    yield
    c.stop()
