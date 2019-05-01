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
from typing import Any, Dict, Optional

import numpy as np
import matplotlib
matplotlib.use('agg')
import os
import pylab as plt

from tac.game import Game


class GameStats:
    """
    A class to query statistics about a game.
    """

    def __init__(self, game: Optional[Game]):
        self.game = game  # type: Optional[Game]

    @classmethod
    def from_json(cls, d: Dict[str, Any]):
        game = Game.from_dict(d)
        return GameStats(game)

    def holdings_history(self):
        """
        Compute the history of holdings.

        :return: a matrix of shape (nb_transactions, nb_agents, nb_goods). i=0 is the initial endowment matrix.
        """
        nb_transactions = len(self.game.transactions)
        nb_agents = self.game.configuration.nb_agents
        nb_goods = self.game.configuration.nb_goods
        result = np.zeros((nb_transactions + 1, nb_agents, nb_goods), dtype=np.int32)

        temp_game = Game(self.game.configuration)

        # initial holdings
        result[0, :] = np.asarray(temp_game.configuration.endowments, dtype=np.int32)

        # compute the partial scores for every agent after every transaction
        # (remember that indexes of the transaction start from one, because index 0 is reserved for the initial scores)
        for idx, tx in enumerate(self.game.transactions):
            temp_game.settle_transaction(tx)
            result[idx + 1, :] = np.asarray(temp_game.get_holdings_matrix(), dtype=np.int32)

        return result

    def score_history(self) -> np.ndarray:
        """
        Compute the history of the scores for every agent.
        To do so, we need to simulate the game again, by settling transactions one by one
        and get the scores after every transaction.

        :return: a matrix of shape (nb_transactions + 1, nb_agents), where every row i contains the scores
                 after transaction i (i=0 is a row with the initial scores.)
        """

        nb_transactions = len(self.game.transactions)
        nb_agents = self.game.configuration.nb_agents
        result = np.zeros((nb_transactions + 1, nb_agents))

        temp_game = Game(self.game.configuration)

        # initial scores
        result[0, :] = temp_game.get_scores()

        # compute the partial scores for every agent after every transaction
        # (remember that indexes of the transaction start from one, because index 0 is reserved for the initial scores)
        for idx, tx in enumerate(self.game.transactions):
            temp_game.settle_transaction(tx)
            result[idx + 1, :] = temp_game.get_scores()

        return result

    def plot_score_history(self, output_path: Optional[str] = None) -> None:
        """
        Plot the history of the scores, for every agent, by transaction.
        :param output_path: an optional output path where to save the figure generated.
        :return: None
        """

        history = self.score_history()

        plt.clf()
        plt.plot(history)
        # labels = ["agent_{:02d}".format(idx) for idx in range(self.game.nb_agents)]
        labels = self.game.configuration.agent_labels
        plt.legend(labels, loc="best")
        plt.xlabel("Transactions")
        plt.ylabel("Score")

        plt.gca().xaxis.set_major_locator(plt.MaxNLocator(integer=True))

        if output_path is None:
            plt.show()
        else:
            plt.savefig(output_path)

    def dump(self, directory: str, experiment_name: str) -> None:
        """
        Dump the plot.

        :param directory: the directory where experiments details are listed.
        :param experiment_name: the name of the folder where the data about experiment will be saved.
        :return: None.
        """
        experiment_dir = directory + "/" + experiment_name
        self.plot_score_history(os.path.join(experiment_dir, "plot.png"))
