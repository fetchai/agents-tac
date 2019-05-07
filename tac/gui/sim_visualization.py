# -*- coding: utf-8 -*-

"""Data Visualization for the simulation outcome, using visdom."""
import argparse
import inspect
import json
import os
import subprocess
import time
from typing import Optional

import numpy as np
from visdom import Visdom

from tac.game import Game
from tac.stats import GameStats

CUR_PATH = inspect.getfile(inspect.currentframe())
CUR_DIR = os.path.dirname(CUR_PATH)
ROOT_PATH = os.path.join(CUR_DIR, "..", "..")

viz = None  # type: Optional[Visdom]
env_main_name = "sim_main"
env_txs_name = "sim_txs"


def parse_args():
    parser = argparse.ArgumentParser("sim_visualization", description="Data Visualization for the simulation outcome")
    parser.add_argument("--datadir", type=str, help="The path to the simulation data folder.")

    arguments = parser.parse_args()
    return arguments


def add_configuration_details(game_stats: GameStats):
    window_name = "configuration_details"
    viz.properties([
        {'type': 'number', 'name': '# agents', 'value': game_stats.game.configuration.nb_agents},
        {'type': 'number', 'name': '# goods', 'value': game_stats.game.configuration.nb_goods},
        {'type': 'number', 'name': 'fee', 'value': game_stats.game.configuration.fee},
        {'type': 'number', 'name': 'initial balance', 'value': game_stats.game.configuration.initial_money_amounts[0]},
    ], env=env_main_name, win=window_name, opts=dict(title="Configuration"))


def add_utilities(game_stats: GameStats):
    utilities = game_stats.game.configuration.utilities
    utilities = np.asarray(utilities)

    window_name = "utilities"
    viz.heatmap(utilities, env=env_main_name, win=window_name, opts=dict(
        title="Utilities",
        xlabel="Goods",
        ylabel="Agents"
    ))


def add_current_balance(game_states: GameStats):
    balances = np.asarray([state.balance for state in game_states.game.agent_states])
    viz.bar(X=balances, env=env_main_name, win="balances", opts=dict(title="Balances"))


def add_initial_holdings(game_stats: GameStats):
    initial_holdings = game_stats.holdings_history()[0]
    viz.heatmap(initial_holdings, env=env_main_name, win="initial_holdings", opts=dict(
        title="Initial Holdings",
        xlabel="Agents",
        ylabel="Quantity",
        stacked=True,
    ))


def add_current_holdings(game_stats: GameStats):
    initial_holdings = game_stats.holdings_history()[-1]
    viz.heatmap(initial_holdings, env=env_main_name, win="final_holdings", opts=dict(
        title="Current Holdings",
        xlabel="Goods",
        ylabel="Agents",
        stacked=True,
    ))


def plot_scores(game_stats: GameStats):
    score_history = game_stats.score_history()

    window_name = "score_history"
    viz.line(X=np.arange(score_history.shape[0]), Y=score_history, env=env_main_name, win=window_name, opts=dict(
        legend=game_stats.game.configuration.agent_labels,
        title="Simulation Visualization",
        xlabel="Transactions",
        ylabel="Score"
    ))


def plot_balance_history(game_stats: GameStats):
    balance_history = game_stats.balance_history()

    window_name = "Balances history"
    viz.line(X=np.arange(balance_history.shape[0]), Y=balance_history, env=env_main_name, win=window_name, opts=dict(
        legend=game_stats.game.configuration.agent_labels,
        title="Balance history",
        xlabel="Transactions",
        ylabel="Money"
    ))


def main():
    global viz
    try:
        visdom_server_args = ["python", "-m", "visdom.server", "-env_path", os.path.join(CUR_DIR, ".visdom_env")]
        print(" ".join(visdom_server_args))
        prog = subprocess.Popen(visdom_server_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.0)
        arguments = parse_args()
        datadir = arguments.datadir

        viz = Visdom()

        game_data_json_filepath = os.path.join(datadir, "game.json")
        game_data = json.load(open(game_data_json_filepath))
        game = Game.from_dict(game_data)
        game_stats = GameStats(game)

        # plot_transactions(game_stats)
        add_configuration_details(game_stats)
        add_utilities(game_stats)
        add_current_holdings(game_stats)
        add_initial_holdings(game_stats)
        plot_scores(game_stats)
        plot_balance_history(game_stats)
        add_current_balance(game_stats)

        print("Start server at http://localhost:8097")
        while True:
            input()

    except KeyboardInterrupt:
        print("Key interrupt...")
    finally:
        prog.terminate()


if __name__ == '__main__':
    main()
