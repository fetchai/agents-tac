# -*- coding: utf-8 -*-

"""Data Visualization for the simulation outcome, using visdom."""
import argparse
import inspect
import json
import os

import numpy as np
from visdom import Visdom

from tac.game import Game
from tac.stats import GameStats

CUR_PATH = inspect.getfile(inspect.currentframe())
ROOT_PATH = os.path.join("..", "..", CUR_PATH)


def parse_args():
    parser = argparse.ArgumentParser("sim_visualization", description="Data Visualization for the simulation outcome")
    parser.add_argument("--datadir", type=str, help="The path to the simulation data folder.")

    arguments = parser.parse_args()
    return arguments


if __name__ == '__main__':
    arguments = parse_args()
    datadir = arguments.datadir
    env_name = "sim_visualization"
    window_name = "score_history"

    game_data_json_filepath = os.path.join(datadir, "game.json")
    game_data = json.load(open(game_data_json_filepath))
    game = Game.from_dict(game_data)
    game_stats = GameStats(game)

    holdings_history = game_stats.holdings_history()
    score_history = game_stats.score_history()

    viz = Visdom()
    win = viz.win_exists(win=window_name, env=env_name)
    viz.line(X=np.arange(score_history.shape[0]), Y=score_history, env=env_name, win=win, opts=dict(
        legend=game.configuration.agent_labels,
        title="Simulation Visualization",
        xlabel="Transactions",
        ylabel="Score"
    ))

