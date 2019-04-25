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
import inspect
import json
import os

import flask
from flask import Flask, render_template, request
from werkzeug.datastructures import FileStorage

from tac.game import Game
from tac.stats import GameStats

import pylab as plt

plt.ioff()

THIS_DIR = os.path.dirname(inspect.getfile(inspect.currentframe()))

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
    output_filepath = os.path.join("static", "tmp", "tmp.png")
    full_output_path = os.path.join(THIS_DIR, output_filepath)
    game_stats.plot_score_history(output_path=full_output_path)

    g= game.agent_states[0]

    return render_template("index.html",
                           nb_agents=game.configuration.nb_agents,
                           nb_goods=game.configuration.nb_goods,
                           initial_money_amounts=game.configuration.initial_money_amounts,
                           fee=game.configuration.fee,
                           idx_agent_states=enumerate(game.agent_states),
                           game=game,
                           nb_transactions=len(game.transactions),
                           saved_plot_figure=output_filepath,
                           agent_states=game.agent_states)


if __name__ == '__main__':
    app.run("0.0.0.0")
