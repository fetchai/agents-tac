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

"""
Implement a Flask-based server for controlling the simulation.

In particular, it provides REST methods to start/stop a sandbox and an agent, alongside a GUI to let the
 user to easily change the parameters.
"""

import docker
import logging
import os
import re
from queue import Empty
from threading import Thread

from flask import Flask

from tac.gui.launcher import home, api
from tac.gui.launcher.api.resources.sandboxes import sandbox_queue, SandboxRunner

logger = logging.getLogger(__name__)


class CustomFlask(Flask):
    """Wrapper of the Flask app."""

    def __init__(self, *args, **kwargs):
        """Initialize our wrapper."""
        super().__init__(*args, **kwargs)

        self.running = False
        self.sandbox_runner_thread = Thread(target=self.run_sandbox_queue)

    def run_sandbox_queue(self):
        """Consume elements from the sandbox queue."""
        while self.running:
            logger.debug("Waiting for sandbox to execute...")
            try:
                sandbox_runner = sandbox_queue.get(timeout=5.0)  # type: SandboxRunner
                logger.debug("Launching the sandbox with id: {}".format(sandbox_runner.id))
                sandbox_runner()
                logger.debug("Waiting until it completes.")
                sandbox_runner.wait()
                logger.debug("Sandbox with ID={} has been completed.".format(sandbox_runner.id))
            except Empty:
                pass
        logger.debug("Exiting from the job loop...")

    def setup(self):
        """Set up resources before running the main app."""
        logger.debug("Setup method called.")
        kill_any_running_oef()
        self.running = True
        self.sandbox_runner_thread.start()

    def run(self, *args, **kwargs):
        """Wrap the run method to hide setup and teardown operations to the user."""
        try:
            self.setup()
            super().run(*args, **kwargs)
        finally:
            self.teardown()

    def teardown(self):
        """Teardown the allocated resources."""
        logger.debug("Teardown method called.")
        self.running = False
        self.sandbox_runner_thread.join()


def kill_any_running_oef():
    """Kill any running OEF instance."""
    client = docker.from_env()
    for container in client.containers.list():
        if any(re.match("fetchai/oef-search", tag) for tag in container.image.tags):
            logger.debug("Stopping existing OEF Node...")
            container.stop()


def create_app(test_config=None):
    """Create and configure an instance of the Flask application."""
    app = CustomFlask(__name__, instance_relative_config=True)

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile("config.py", silent=True)
    else:
        # load the test config if passed in
        app.config.update(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # register api endpoints
    api.create_api(app)

    # register home pages
    app.register_blueprint(home.bp)

    return app
