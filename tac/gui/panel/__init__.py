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
import os
import time
from threading import Thread

from flask import Flask

from tac.gui.panel import home, api
from tac.gui.panel.api.resources.agents import Agent
from tac.gui.panel.api.resources.sandboxes import Sandbox, SandboxList, sandbox_queue


class CustomFlask(Flask):
    """Wrapper of the Flask app."""

    def __init__(self, *args, **kwargs):
        """Initialize our wrapper."""
        super().__init__(*args, **kwargs)

        self.running = False
        self.sandbox_runner_thread = Thread(target=self.run_sandbox_queue)

    def run_sandbox_queue(self):
        """Consume elements from the sandbox queue"""
        while self.running:
            sandbox_runner = sandbox_queue.get()
            sandbox_runner()
            sandbox_runner.wait()
            time.sleep(5.0)

    def setup(self):
        """Setup operations to execute before running"""
        self.running = True
        self.sandbox_runner_thread.start()

    def run(self, *args, **kwargs):
        """Wrapper of the run method to hide setup and teardown operations to the user."""
        try:
            self.setup()
            super().run(*args, **kwargs)
        finally:
            self.teardown()

    def teardown(self):
        """Teardown the allocated resources"""
        self.running = False
        self.sandbox_runner_thread.join()


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
