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


class LeaderboardDashboard(Dashboard):
    """
    Class to display the aggregated statistics of multiple TAC instances.

    It assumes that a Visdom server is running at the address and port provided in input
    (default: http://localhost:8097)
    """

    def __init__(self, competition_directory: str,
                 visdom_addr: str = "localhost",
                 visdom_port: int = 8097,
                 env_name: Optional[str] = "leaderboard"):
        """Instantiate a LeaderboardDashboard.

        :param competition_directory: the path where to find the history of the games.
        """
        super().__init__(visdom_addr, visdom_port, env_name)
        self.competition_directory = competition_directory
        self.game_stats_list = self._load()

    def _load(self) -> List[GameStats]:
        """Load all game statistics from iterated TAC output."""
        result = []  # type: List[GameStats]

        game_dirs = sorted(os.listdir(self.competition_directory))
        for game_dir in game_dirs:
            game_data_json_filepath = os.path.join(self.competition_directory, game_dir, "game.json")
            if not os.path.exists(game_data_json_filepath):
                continue
            game_data = json.load(open(game_data_json_filepath))
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


def parse_args():
    """Parse the arguments."""
    parser = argparse.ArgumentParser("dashboard", description="Data Visualization for the simulation outcome")
    parser.add_argument("--datadir", type=str, required=True, help="The path to the simulation data folder.")
    parser.add_argument("--env_name", type=str, default=None, help="The name of the environment to create.")

    arguments = parser.parse_args()
    return arguments


if __name__ == '__main__':

    arguments = parse_args()
    process = start_visdom_server()
    d = LeaderboardDashboard(arguments.datadir, env_name=arguments.env_name)

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
