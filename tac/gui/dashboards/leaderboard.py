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
import numpy as np
import pandas as pd
import os
from collections import defaultdict
from typing import Optional, Dict, List

from tac.agents.controller.base.states import Game
from tac.gui.dashboards.base import start_visdom_server, Dashboard
from tac.platform.game.stats import GameStats

DEFAULT_ENV_NAME = "tac_simulation_env_main"


def compute_aggregate_scores(all_game_stats: List[GameStats]) -> Dict[str, float]:
    """
    Compute the sum of all scores for every agents.

    :param all_game_stats: the GameStats object for every instance of TAC.
    :return: a dictionary "agent_name" -> "final score"
    """
    result = defaultdict(lambda: 0.0)  # type: Dict[str, float]
    for game_stats in all_game_stats:
        pbk_to_name = game_stats.game.configuration.agent_pbk_to_name
        pbk_to_score = game_stats.game.get_scores()
        for pbk, score in pbk_to_score.items():
            name = pbk_to_name[pbk]
            result[name] += score
    return result


def compute_statistics(all_game_stats: List[GameStats]) -> None:
    """Compute statistics and dump them."""
    results = []
    equilibrium = []
    initial = []
    tx_results = {}  # type: Dict[str, Dict[str, int]]
    tx_results_seller = []
    tx_results_buyer = []
    tx_prices = {name: [] for name in all_game_stats[0].game.configuration.agent_pbk_to_name.values()}  # type: Dict[str, List[float]]
    name_to_idx = {}
    first = True
    for game_stats in all_game_stats:
        pbk_to_name = game_stats.game.configuration.agent_pbk_to_name
        pbk_to_score = game_stats.game.get_scores()
        count = 0
        result = [0.0] * len(pbk_to_name)
        for pbk, score in pbk_to_score.items():
            if first:
                idx = count
                name = pbk_to_name[pbk]
                name_to_idx[name] = idx
            else:
                name = pbk_to_name[pbk]
                idx = name_to_idx[name]
            result[idx] = score
            count += 1
        results.append(result)
        result = [0.0] * len(pbk_to_name)
        for name, eq_score in game_stats.get_eq_scores().items():
            idx = name_to_idx[name]
            result[idx] = eq_score
        equilibrium.append(result)
        result = [0.0] * len(pbk_to_name)
        for name, initial_score in game_stats.get_initial_scores().items():
            idx = name_to_idx[name]
            result[idx] = eq_score
        initial.append(result)
        counts = game_stats.tx_counts()
        first = False
        if tx_results == {}:
            tx_results = counts.copy()
        else:
            for key, value in counts['seller'].items():
                tx_results['seller'][key] += value
            for key, value in counts['buyer'].items():
                tx_results['buyer'][key] += value
        result = [0] * len(pbk_to_name)
        for name, count in counts['seller'].items():
            idx = name_to_idx[name]
            result[idx] = count
        tx_results_seller.append(result)
        result = [0] * len(pbk_to_name)
        for name, count in counts['buyer'].items():
            idx = name_to_idx[name]
            result[idx] = count
        tx_results_buyer.append(result)
        prices = game_stats.tx_prices()
        for name, price in prices.items():
            tx_prices[name].extend(price)
    scores = np.asarray(results)
    df1 = pd.DataFrame(scores, columns=[key for key in name_to_idx.keys()])
    df1.to_csv('scores_final.csv')
    df2 = pd.DataFrame(equilibrium, columns=[key for key in name_to_idx.keys()])
    df2.to_csv('scores_equilibrium.csv')
    df3 = pd.DataFrame(initial, columns=[key for key in name_to_idx.keys()])
    df3.to_csv('scores_initial.csv')
    df4 = pd.DataFrame(np.asarray(tx_results_buyer), columns=[key for key in name_to_idx.keys()])
    df4.to_csv('transactions_buyer.csv')
    df5 = pd.DataFrame(np.asarray(tx_results_seller), columns=[key for key in name_to_idx.keys()])
    df5.to_csv('transactions_seller.csv')
    # df6 = pd.DataFrame(dict([(k, pd.Series(v)) for k, v in tx_prices.items()]))
    prices_w = []
    prices_b = []
    for column_name, pricess in tx_prices.items():
        if column_name[-3:] == '_wm':
            prices_w.extend(pricess)
        else:
            prices_b.extend(pricess)
    data_dict = {'w_model': pd.Series(prices_w, dtype=np.float64), 'baseline': pd.Series(prices_b, dtype=np.float64)}
    df7 = pd.DataFrame(data_dict)
    df7.to_csv('prices.csv')


class LeaderboardDashboard(Dashboard):
    """
    Class to display the aggregated statistics of multiple TAC instances.

    It assumes that a Visdom server is running at the address and port provided in input
    (default: http://localhost:8097)
    """

    def __init__(self, competition_directory: str,
                 visdom_addr: str = "localhost",
                 visdom_port: int = 8097,
                 env_name: Optional[str] = "leaderboard",
                 dump_stats: bool = False):
        """Instantiate a LeaderboardDashboard.

        :param competition_directory: the path where to find the history of the games.
        """
        super().__init__(visdom_addr, visdom_port, env_name)
        self.competition_directory = competition_directory
        self.game_stats_list = self._load()
        self.dump_stats = dump_stats

    def _load(self) -> List[GameStats]:
        """Load all game statistics from iterated TAC output."""
        result = []  # type: List[GameStats]

        game_dirs = sorted(os.listdir(self.competition_directory))
        for game_dir in game_dirs:
            game_data_json_filepath = os.path.join(self.competition_directory, game_dir, "game.json")
            if not os.path.exists(game_data_json_filepath):
                continue
            game_data = json.load(open(game_data_json_filepath))
            if game_data == {}:
                print("Found incomplete data for game_dir={}!".format(game_dir))
                continue
            game = Game.from_dict(game_data)
            game_stats = GameStats(game)
            result.append(game_stats)

        return result

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the dashboard."""
        self.stop()

    def __enter__(self):
        """Enter the dashboard."""
        self.start()

    def _display_ranking(self):
        """Display the final ranking."""
        window_name = "ranking"

        aggregated_scores = compute_aggregate_scores(self.game_stats_list)
        properties = []
        for name, score in sorted(aggregated_scores.items(), key=lambda x: x[1], reverse=True):
            properties.append({'type': 'number', 'name': name, 'value': str(score)})

        self.viz.properties(properties, env=self.env_name, win=window_name, opts=dict(title="Configuration"))

    def display(self):
        """Display the leaderboard."""
        self._display_ranking()
        if self.dump_stats:
            compute_statistics(self.game_stats_list)


def parse_args():
    """Parse the arguments."""
    parser = argparse.ArgumentParser("dashboard", description="Data Visualization for the simulation outcome")
    parser.add_argument("--datadir", type=str, required=True, help="The path to the simulation data folder.")
    parser.add_argument("--env_name", type=str, default=None, help="The name of the environment to create.")
    parser.add_argument("--dump_stats", action="store_true", help="Dump some game stats.")

    arguments = parser.parse_args()
    return arguments


if __name__ == '__main__':

    arguments = parse_args()
    process = start_visdom_server()
    d = LeaderboardDashboard(arguments.datadir, env_name=arguments.env_name, dump_stats=arguments.dump_stats)

    d.start()
    d.display()
    while True:
        try:
            input()
        except KeyboardInterrupt:
            break
        finally:
            d.stop()
            process.terminate()
