#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Start a Visdom server, an OEF node instance, and run the simulation script."""

import inspect
import os
import platform
import re
import subprocess
import sys

import docker

import tac
from tac.platform.simulation import parse_arguments, build_simulation_parameters

CUR_PATH = inspect.getfile(inspect.currentframe())
ROOT_DIR = os.path.join(os.path.dirname(CUR_PATH), "..")


class VisdomServer:
    """Class to manage the visdom server."""

    def __enter__(self):
        """Define what the context manager should do at the beginning of the block."""
        if platform.system() == 'Darwin':
            # This is required due to a bug in mac os Mojave
            print("Setting environment var...")
            os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"
        print("Starting Visdom server...")
        self.proc = subprocess.Popen(["python3", "-m", "visdom.server"], env=os.environ, cwd=ROOT_DIR)

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Define what the context manager should do after the block has been executed."""
        print("Terminating Visdom server...")
        self.proc.terminate()


class OEFNode:
    """Class to manage the OEF node."""

    def _stop_oef_search_images(self):
        """Stop any running OEF nodes."""
        client = docker.from_env()
        for container in client.containers.list():
            if any(re.match("fetchai/oef-search", tag) for tag in container.image.tags):
                print("Stopping existing OEF Node...")
                container.stop()

    def _wait_for_oef(self):
        """Wait for the OEF to come live."""
        print("Waiting for the OEF to be operative...")
        wait_for_oef = subprocess.Popen([
            os.path.join("sandbox", "wait-for-oef.sh"),
            "127.0.0.1",
            "10000",
            ":"
        ], env=os.environ, cwd=ROOT_DIR)

        wait_for_oef.wait(30)

    def __enter__(self):
        """Define what the context manager should do at the beginning of the block."""
        self._stop_oef_search_images()
        script_path = os.path.join("oef_search_pluto_scripts", "launch.py")
        configuration_file_path = os.path.join("oef_search_pluto_scripts", "launch_config_latest.json")
        print("Launching new OEF Node...")
        self.oef_process = subprocess.Popen(["python3", script_path, "-c", configuration_file_path, "--background"],
                                            stdout=subprocess.PIPE, env=os.environ, cwd=ROOT_DIR)
        self._wait_for_oef()
        self.id = self._get_image_id()
        print("ID: ", self.id)

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Define what the context manager should do after the block has been executed."""
        print("Stopping OEF Node...")
        p = subprocess.Popen(["docker", "stop", self.id], env=os.environ)
        p.wait()

    def _get_image_id(self):
        output = self.oef_process.communicate()[0]
        id = output.splitlines()[-1].decode("utf-8")
        return id


if __name__ == '__main__':
    sys.argv += ['--gui']
    args = parse_arguments()
    simulation_params = build_simulation_parameters(args)

    with VisdomServer(), OEFNode():
        tac.platform.simulation.run(simulation_params)
