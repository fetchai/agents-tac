# -*- coding: utf-8 -*-

import os

from flask import Flask
from flask_restful import Api

from tac.gui.panel import home
from tac.gui.panel.api.resources import Sandbox
from tac.gui.panel.api.resources import HelloWorld


def create_app(test_config=None):
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__, instance_relative_config=True)

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
    api = Api(app, prefix='/api')
    api.add_resource(Sandbox, "/sandbox")
    api.add_resource(HelloWorld, "/hello")

    # register home pages
    app.register_blueprint(home.bp)

    return app
