# -*- coding: utf-8 -*-
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
DEFAULT_ENV_NAME = "tac_simulation_env_main"


def start_visdom_server() -> subprocess.Popen:
    visdom_server_args = ["python", "-m", "visdom.server", "-env_path", os.path.join(CUR_DIR, ".visdom_env")]
    print(" ".join(visdom_server_args))
    prog = subprocess.Popen(visdom_server_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.0)
    print("Visdom server running at http://localhost:8097")
    return prog


class Dashboard(object):
    """
    Class to manage Visdom dashboard.
    It assumes that a Visdom server is running at the address and port provided in input
    (default: http://localhost:8097)
    """

    def __init__(self, game_stats: GameStats,
                 visdom_addr: str = "localhost",
                 visdom_port: int = 8097,
                 env_name: Optional[str] = None):
        self._proc = None  # type: Optional[subprocess.Popen]
        self.viz = None  # type: Optional[Visdom]
        self.visdom_addr = visdom_addr
        self.visdom_port = visdom_port
        self.env_name = env_name if env_name is not None else DEFAULT_ENV_NAME
        self.game_stats = game_stats

    def _is_running(self):
        return self.viz is not None

    def start(self):
        self.viz = Visdom(server=self.visdom_addr, port=self.visdom_port, env=self.env_name)

    def stop(self):
        self.viz = None

    def update(self):
        if not self._is_running():
            raise Exception("Dashboard not running, update not allowed.")
        self._update_info()
        self._update_utility_params()
        self._update_current_holdings()
        self._update_initial_holdings()
        self._update_plot_scores()
        self._update_plot_balance_history()
        self._update_plot_price_history()
        self._update_plot_eq_vs_mean_price()
        self._update_plot_eq_vs_current_score()
        self._update_adjusted_score()

    @staticmethod
    def from_datadir(datadir: str, env_name: str):
        game_data_json_filepath = os.path.join(datadir, "game.json")
        print("Loading data from {}".format(game_data_json_filepath))
        game_data = json.load(open(game_data_json_filepath))
        game = Game.from_dict(game_data)
        game_stats = GameStats(game)
        return Dashboard(game_stats, env_name)

    def _update_info(self):
        window_name = "configuration_details"
        self.viz.properties([
            {'type': 'number', 'name': '# agents', 'value': self.game_stats.game.configuration.nb_agents},
            {'type': 'number', 'name': '# goods', 'value': self.game_stats.game.configuration.nb_goods},
            {'type': 'number', 'name': 'tx fee', 'value': self.game_stats.game.configuration.tx_fee},
            {'type': 'number', 'name': '# transactions', 'value': len(self.game_stats.game.transactions)},
        ], env=self.env_name, win=window_name, opts=dict(title="Configuration"))

    def _update_utility_params(self):
        utility_params = self.game_stats.game.initialization.utility_params
        utility_params = np.asarray(utility_params)

        window_name = "utility_params"
        self.viz.heatmap(utility_params, env=self.env_name, win=window_name, opts=dict(
            title="Utility Parameters",
            xlabel="Goods",
            ylabel="Agents"
        ))

    def _update_initial_holdings(self):
        initial_holdings = self.game_stats.holdings_history()[0]

        window_name = "initial_holdings"
        self.viz.heatmap(initial_holdings, env=self.env_name, win=window_name, opts=dict(
            title="Initial Holdings",
            xlabel="Goods",
            ylabel="Agents",
            stacked=True,
        ))

    def _update_current_holdings(self):
        initial_holdings = self.game_stats.holdings_history()[-1]

        window_name = "final_holdings"
        self.viz.heatmap(initial_holdings, env=self.env_name, win=window_name,
                         opts=dict(
                             title="Current Holdings",
                             xlabel="Goods",
                             ylabel="Agents",
                             stacked=True,
                         ))

    def _update_plot_scores(self):
        score_history = self.game_stats.score_history()

        window_name = "score_history"
        self.viz.line(X=np.arange(score_history.shape[0]), Y=score_history, env=self.env_name, win=window_name,
                      opts=dict(
                          legend=self.game_stats.game.configuration.agent_pbks,
                          title="Scores",
                          xlabel="Transactions",
                          ylabel="Score")
                      )

    def _update_plot_balance_history(self):
        balance_history = self.game_stats.balance_history()

        window_name = "balance_history"
        self.viz.line(X=np.arange(balance_history.shape[0]), Y=balance_history, env=self.env_name, win=window_name,
                      opts=dict(
                          legend=self.game_stats.game.configuration.agent_pbks,
                          title="Balance history",
                          xlabel="Transactions",
                          ylabel="Money")
                      )

    def _update_plot_price_history(self):
        price_history = self.game_stats.price_history()

        window_name = "price_history"
        self.viz.line(X=np.arange(price_history.shape[0]), Y=price_history, env=self.env_name, win=window_name,
                      opts=dict(
                          legend=self.game_stats.game.configuration.good_pbks,
                          title="Price history",
                          xlabel="Transactions",
                          ylabel="Price")
                      )

    def _update_plot_eq_vs_mean_price(self):
        eq_vs_mean_price = self.game_stats.eq_vs_mean_price()

        window_name = "eq_vs_mean_price"
        self.viz.line(X=np.arange(eq_vs_mean_price.shape[0]), Y=eq_vs_mean_price, env=self.env_name, win=window_name,
                      opts=dict(
                          legend=['eq_price', 'mean_price'],
                          title="Equilibrium vs Mean Prices",
                          xlabel="Goods",
                          ylabel="Price")
                      )

    def _update_plot_eq_vs_current_score(self):
        eq_vs_current_score = self.game_stats.eq_vs_current_score()

        window_name = "eq_vs_current_score"
        self.viz.line(X=np.arange(eq_vs_current_score.shape[0]), Y=eq_vs_current_score, env=self.env_name, win=window_name,
                      opts=dict(
                          legend=['eq_score', 'current_score'],
                          title="Equilibrium vs Current Score",
                          xlabel="Agents",
                          ylabel="Score")
                      )

    def _update_adjusted_score(self):
        adjusted_score = self.game_stats.adjusted_score()

        window_name = "adjusted_score"
        self.viz.line(X=np.arange(adjusted_score.shape[0]), Y=adjusted_score, env=self.env_name, win=window_name,
                      opts=dict(
                          legend=['adjusted_score'],
                          title="Adjusted Score",
                          xlabel="Agents",
                          ylabel="Score")
                      )

    def __enter__(self):
        d.start()
        d.update()

    def __exit__(self, exc_type, exc_val, exc_tb):
        d.stop()


def parse_args():
    parser = argparse.ArgumentParser("dashboard", description="Data Visualization for the simulation outcome")
    parser.add_argument("--datadir", type=str, required=True, help="The path to the simulation data folder.")
    parser.add_argument("--env_name", type=str, default=None, help="The name of the environment to create.")

    arguments = parser.parse_args()
    return arguments


if __name__ == '__main__':

    arguments = parse_args()
    process = start_visdom_server()
    d = Dashboard.from_datadir(arguments.datadir, arguments.env_name)

    d.start()
    while True:
        try:
            input()
        except KeyboardInterrupt:
            break
        finally:
            d.stop()
            process.terminate()
