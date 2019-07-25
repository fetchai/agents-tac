# -*- coding: utf-8 -*-
from flask import Blueprint

bp = Blueprint("panel", __name__, url_prefix="/panel")


@bp.route("/hello")
def hello():
    return "Hello, World!"
