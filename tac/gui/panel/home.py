# -*- coding: utf-8 -*-
from flask import Blueprint, render_template

from tac.gui.panel.forms import SandboxForm

bp = Blueprint("home", __name__, url_prefix="/")


@bp.route("/", methods=["GET"])
def index():
    form = SandboxForm()
    return render_template("panel.html", form_sandbox=form)

