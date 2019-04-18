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
from typing import Any, Dict, List, Optional

import numpy as np
import pylab as plt
from tac.game import Game


class GameStats:

    def __init__(self, game: Game):
        self.game = game

    @classmethod
    def from_json(cls, d: Dict[str, Any]):
        g = Game.from_dict(d)
        return GameStats(g)

    def score_history(self) -> np.ndarray:
        """
        Compute the history of the scores for every agent.
        To do so, we need to simulate the game again, by settling transactions one by one
        and get the scores after every transaction.

        :return: a matrix of shape (nb_transactions + 1, nb_agents), where every row i contains the scores
                 after transaction i (i=0 is a row with the initial scores.)
        """

        nb_transactions = len(self.game.transactions)
        nb_agents = self.game.nb_agents
        result = np.zeros((nb_transactions + 1, nb_agents))

        temp_game = Game(
            nb_agents=self.game.nb_agents,
            nb_goods=self.game.nb_goods,
            initial_money_amounts=self.game.initial_money_amount,
            instances_per_good=self.game.instances_per_good,
            scores=self.game.scores,
            fee=self.game.fee,
            initial_endowments=self.game.initial_endowments,
            preferences=self.game.preferences,
            agents_ids=self.game.agents_ids
        )

        # initial scores
        result[0, :] = temp_game.get_scores()

        # compute the partial scores for every agent after every transaction
        # (remember that indexes of the transaction start from one, because index 0 is reserved for the initial scores)
        for idx, tx in enumerate(self.game.transactions):
            temp_game.settle_transaction(tx)
            result[idx + 1, :] = temp_game.get_scores()

        return result

    def plot_score_history(self, output_path: Optional[str] = None) -> None:
        history = self.score_history()

        plt.plot(history)
        # labels = ["agent_{:02d}".format(idx) for idx in range(self.game.nb_agents)]
        labels = self.game.agents_ids
        plt.legend(labels, loc="best")
        plt.xlabel("Transactions")
        plt.ylabel("Score")

        plt.gca().xaxis.set_major_locator(plt.MaxNLocator(integer=True))

        if output_path is None:
            plt.show()
        else:
            plt.savefig(output_path)

