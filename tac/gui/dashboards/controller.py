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


"""Module containing the controller dashboard and related classes."""

import argparse
import json
import os
from typing import Optional, Dict

import numpy as np

from tac.gui.dashboards.base import start_visdom_server, Dashboard
from tac.agents.controller.base.states import Game
from tac.platform.game.stats import GameStats

DEFAULT_ENV_NAME = "tac_simulation_env_main"


class ControllerDashboard(Dashboard):
    """
    Class to manage a Visdom dashboard for the controller agent.

    It assumes that a Visdom server is running at the address and port provided in input
    (default: http://localhost:8097)
    """

    def __init__(
        self,
        game_stats: Optional[GameStats] = None,
        visdom_addr: str = "localhost",
        visdom_port: int = 8097,
        env_name: Optional[str] = "tac_controller",
    ):
        """Instantiate a ControllerDashboard."""
        super().__init__(visdom_addr, visdom_port, env_name)
        self.game_stats = game_stats

        self.agent_pbk_to_name = {}  # type: Dict[str, str]

    def update(self):
        """Update the dashboard."""
        if not self._is_running():
            raise Exception("Dashboard not running, update not allowed.")

        self._update_registered_agents()
        if self.game_stats is not None:
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
    def from_datadir(datadir: str, env_name: str) -> "ControllerDashboard":
        """
        Return a ControllerDashboard from a data directory.

        :param datadir: the data directory
        :param env_name: the environment name
        :return: controller dashboard
        """
        game_data_json_filepath = os.path.join(datadir, "game.json")
        print("Loading data from {}".format(game_data_json_filepath))
        game_data = json.load(open(game_data_json_filepath))
        game = Game.from_dict(game_data)
        game_stats = GameStats(game)
        return ControllerDashboard(game_stats, env_name=env_name)

    def _update_info(self):
        window_name = "configuration_details"
        self.viz.properties(
            [
                {
                    "type": "number",
                    "name": "# agents",
                    "value": self.game_stats.game.configuration.nb_agents,
                },
                {
                    "type": "number",
                    "name": "# goods",
                    "value": self.game_stats.game.configuration.nb_goods,
                },
                {
                    "type": "number",
                    "name": "tx fee",
                    "value": self.game_stats.game.configuration.tx_fee,
                },
                {
                    "type": "number",
                    "name": "# transactions",
                    "value": len(self.game_stats.game.transactions),
                },
            ],
            env=self.env_name,
            win=window_name,
            opts=dict(title="Configuration"),
        )

    def _update_registered_agents(self):
        window_name = "registered_agents"
        self.viz.properties(
            [
                {"type": "string", "name": "{}".format(agent_name), "value": ""}
                for agent_name in self.agent_pbk_to_name.values()
            ],
            env=self.env_name,
            win=window_name,
            opts=dict(title="Registered Agents"),
        )

    def _update_utility_params(self):
        utility_params = self.game_stats.game.initialization.utility_params
        utility_params = np.asarray(utility_params)

        window_name = "utility_params"
        self.viz.heatmap(
            utility_params,
            env=self.env_name,
            win=window_name,
            opts=dict(title="Utility Parameters", xlabel="Goods", ylabel="Agents"),
        )

    def _update_initial_holdings(self):
        initial_holdings = self.game_stats.holdings_history()[0]

        window_name = "initial_holdings"
        self.viz.heatmap(
            initial_holdings,
            env=self.env_name,
            win=window_name,
            opts=dict(
                title="Initial Holdings", xlabel="Goods", ylabel="Agents", stacked=True,
            ),
        )

    def _update_current_holdings(self):
        initial_holdings = self.game_stats.holdings_history()[-1]

        window_name = "final_holdings"
        self.viz.heatmap(
            initial_holdings,
            env=self.env_name,
            win=window_name,
            opts=dict(
                title="Current Holdings", xlabel="Goods", ylabel="Agents", stacked=True,
            ),
        )

    def _update_plot_scores(self):
        keys, score_history = self.game_stats.score_history()
        agent_names = [
            self.game_stats.game.configuration.agent_pbk_to_name[agent_pbk]
            for agent_pbk in keys
        ]

        window_name = "score_history"
        self.viz.line(
            X=np.arange(score_history.shape[0]),
            Y=score_history,
            env=self.env_name,
            win=window_name,
            opts=dict(
                legend=agent_names,
                title="Scores",
                xlabel="Transactions",
                ylabel="Score",
            ),
        )

    def _update_plot_balance_history(self):
        keys, balance_history = self.game_stats.balance_history()
        agent_names = [
            self.game_stats.game.configuration.agent_pbk_to_name[agent_pbk]
            for agent_pbk in keys
        ]

        window_name = "balance_history"
        self.viz.line(
            X=np.arange(balance_history.shape[0]),
            Y=balance_history,
            env=self.env_name,
            win=window_name,
            opts=dict(
                legend=agent_names,
                title="Balance history",
                xlabel="Transactions",
                ylabel="Money",
            ),
        )

    def _update_plot_price_history(self):
        price_history = self.game_stats.price_history()

        window_name = "price_history"
        self.viz.line(
            X=np.arange(price_history.shape[0]),
            Y=price_history,
            env=self.env_name,
            win=window_name,
            opts=dict(
                legend=list(
                    self.game_stats.game.configuration.good_pbk_to_name.values()
                ),
                title="Price history",
                xlabel="Transactions",
                ylabel="Price",
            ),
        )

    def _update_plot_eq_vs_mean_price(self):
        good_names, eq_vs_mean_price = self.game_stats.eq_vs_mean_price()

        window_name = "eq_vs_mean_price"
        self.viz.bar(
            X=eq_vs_mean_price,
            env=self.env_name,
            win=window_name,
            opts=dict(
                legend=["eq_price", "mean_price"],
                title="Equilibrium vs Mean Prices",
                xlabel="Goods",
                ylabel="Price",
                rownames=good_names,
            ),
        )

    def _update_plot_eq_vs_current_score(self):
        keys, eq_vs_current_score = self.game_stats.eq_vs_current_score()
        agent_names = [
            self.game_stats.game.configuration.agent_pbk_to_name[agent_pbk]
            for agent_pbk in keys
        ]

        window_name = "eq_vs_current_score"
        self.viz.bar(
            X=eq_vs_current_score,
            env=self.env_name,
            win=window_name,
            opts=dict(
                legend=["eq_score", "current_score"],
                title="Equilibrium vs Current Score",
                xlabel="Agents",
                ylabel="Score",
                rownames=agent_names,
            ),
        )

    def _update_adjusted_score(self):
        keys, adjusted_score = self.game_stats.adjusted_score()

        window_name = "adjusted_score"
        self.viz.bar(
            X=adjusted_score,
            env=self.env_name,
            win=window_name,
            opts=dict(
                title="Adjusted Score",
                xlabel="Agents",
                ylabel="Score",
                rownames=[
                    self.game_stats.game.configuration.agent_pbk_to_name[agent_pbk]
                    for agent_pbk in keys
                ],
            ),
        )

    def __enter__(self):
        """Enter the dashboard."""
        self.start()
        self.update()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the dashboard."""
        self.stop()


def parse_args():
    """Parse the arguments."""
    parser = argparse.ArgumentParser(
        "dashboard", description="Data Visualization for the simulation outcome"
    )
    parser.add_argument(
        "--datadir",
        type=str,
        required=True,
        help="The path to the simulation data folder.",
    )
    parser.add_argument(
        "--env_name",
        type=str,
        default=None,
        help="The name of the environment to create.",
    )

    arguments = parser.parse_args()
    return arguments


if __name__ == "__main__":

    arguments = parse_args()
    process = start_visdom_server()
    d = ControllerDashboard.from_datadir(arguments.datadir, arguments.env_name)

    d.start()
    d.update()
    while True:
        try:
            input()
        except KeyboardInterrupt:
            break
        finally:
            d.stop()
            process.terminate()
