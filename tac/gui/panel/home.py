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

"""Implement the basic Flask blueprint for the common web pages (e.g. the index page)."""

from flask import Blueprint, render_template, redirect

from tac.gui.panel.forms.sandbox import SandboxForm
from tac.gui.panel.forms.agent import AgentForm

bp = Blueprint("home", __name__, url_prefix="/")


@bp.route("/", methods=["GET"])
def index():
    """Render the index page of the panel app."""
    return redirect("/panel", code=302)


@bp.route("/panel", methods=["GET"])
def panel():
    """Render the panel page."""
    sandbox_form = SandboxForm()
    agent_form = AgentForm()
    return render_template("panel.html", form_sandbox=sandbox_form, form_agent=agent_form)


@bp.route("/grid-search", methods=["GET"])
def grid_search():
    """Render the grid search page."""
    sandbox_form = SandboxForm()
    return render_template("grid_search.html", form_sandbox=sandbox_form)
