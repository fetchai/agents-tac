#!/usr/bin/env python3
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
import json

import flask
from flask import Flask, render_template, request
from werkzeug.datastructures import FileStorage

from tac.core import Game
from tac.stats import GameStats

import pylab as plt

plt.ioff()

app = Flask(__name__)
# prevent caching
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

LIST_FILES = []
current_file = None


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template("index.html")
    elif request.method == "POST":
        return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    uploaded_files = flask.request.files.getlist("file[]")
    current_file = uploaded_files[0]  # type: FileStorage

    game_data = json.loads(current_file.stream.read())
    game = Game.from_dict(game_data)

    game_stats = GameStats(game)
    output_filepath = "static/tmp/tmp.png"
    game_stats.plot_score_history(output_path=output_filepath)
    return render_template("index.html", **game.to_dict(),
                           nb_transactions=len(game.transactions),
                           saved_plot_figure=output_filepath,
                           game_states=game.game_states)


if __name__ == '__main__':
    app.run("0.0.0.0")
