# -*- coding: utf-8 -*-
from flask import Blueprint, render_template

from tac.gui.panel.forms import SandboxForm
from tac.gui.panel.forms.agent import AgentForm

bp = Blueprint("home", __name__, url_prefix="/")


@bp.route("/", methods=["GET"])
def index():
    sandbox_form = SandboxForm()
    agent_form = AgentForm()
    return render_template("panel.html", form_sandbox=sandbox_form, form_agent=agent_form)

