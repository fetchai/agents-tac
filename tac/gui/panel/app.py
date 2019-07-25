# -*- coding: utf-8 -*-
from flask import Flask, render_template

from tac.gui.panel.forms import SandboxForm

app = Flask(__name__, instance_relative_config=True)


@app.route("/", methods=["GET", "POST"])
def index():
    form = SandboxForm()
    return render_template("panel.html", form_sandbox=form)


if __name__ == '__main__':
    app.run("127.0.0.1", 5000, debug=True)
