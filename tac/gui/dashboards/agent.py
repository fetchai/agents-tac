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

"""Module containing the agent dashboard and related classes."""

import inspect
import os
from typing import Optional

import numpy as np

from tac.agents.participant.base.states import AgentState
from tac.agents.participant.base.stats_manager import StatsManager
from tac.gui.dashboards.base import Dashboard
from tac.gui.dashboards.helpers import generate_html_table_from_dict, escape_html
from tac.platform.protocol import Transaction

CUR_PATH = inspect.getfile(inspect.currentframe())
CUR_DIR = os.path.dirname(CUR_PATH)
ROOT_PATH = os.path.join(CUR_DIR, "..", "..")

DEFAULT_ENV_NAME = "tac_simulation_env_main"


class TransactionTable(object):
    """Class maintaining a html table of transactions."""

    def __init__(self):
        """Instantiate a TransactionTable."""
        self.tx_table = dict()
        self.tx_table["#"] = []
        self.tx_table["Agent Role"] = []
        self.tx_table["Counterparty"] = []
        self.tx_table["Amount"] = []
        self.tx_table["Goods Exchanged"] = []

    def add_transaction(self, tx: Transaction, agent_name: Optional[str] = None) -> None:
        """
        Add a transaction to the table.

        :param tx: the Transaction object
        :param agent_name: the name of the agent
        :return: None
        """
        self.tx_table["#"].append(str(len(self.tx_table["#"])))
        self.tx_table["Agent Role"].append("Buyer" if tx.is_sender_buyer else "Seller")
        self.tx_table["Counterparty"].append(agent_name if agent_name is not None else tx.counterparty[:5] + "..." + tx.counterparty[-5:])
        self.tx_table["Amount"].append("{:02.2f}".format(tx.amount))
        self.tx_table["Goods Exchanged"].append("\n"
                                                .join(map(lambda x: "{}: {}".format(x[0], x[1]),
                                                          filter(lambda x: x[1] > 0,
                                                                 tx.quantities_by_good_pbk.items()))))

    def to_html(self) -> str:
        """Convert the table to html."""
        srcdoc = generate_html_table_from_dict(self.tx_table, title="Transactions")
        html_code = '<iframe srcdoc="{encoded_html}" style="{style}" />'.format(
            encoded_html=escape_html(srcdoc),
            style="width: 1024px;height: 1024px;")
        return html_code


class AgentDashboard(Dashboard):
    """
    Class to manage a Visdom dashboard for the participant agent.

    It assumes that a Visdom server is running at the address and port provided in input
    (default: http://localhost:8097)
    """

    def __init__(self, agent_name: str,
                 visdom_addr: str = "localhost",
                 visdom_port: int = 8097,
                 env_name: Optional[str] = None):
        """Instantiate an AgentDashboard."""
        super().__init__(visdom_addr, visdom_port, env_name)

        self.agent_name = agent_name

        self._update_nb_agent_state = -1
        self._update_nb_stats_manager = -1
        self._transaction_table = TransactionTable()
        self._transaction_window = None

    def init(self):
        """Re-initiate the AgentDashboard."""
        self._transaction_window = self.viz.text(self._transaction_table.to_html(), env=self.env_name)

    def add_transaction(self, new_tx: Transaction, agent_name: Optional[str] = None) -> None:
        """
        Add a transaction to the transaction table.

        :param new_tx: a new transaction
        :param agent_name: the agent name
        :return: None
        """
        self._transaction_table.add_transaction(new_tx, agent_name=agent_name)
        self.viz.text(self._transaction_table.to_html(), win=self._transaction_window, env=self.env_name)

    def _update_holdings(self, agent_state: AgentState) -> None:

        scaled_holdings = agent_state.current_holdings / np.sum(agent_state.current_holdings)
        scaled_utility_params = agent_state.utility_params / np.sum(agent_state.utility_params)

        window_name = "{}_utility_and_holdings".format(self.env_name)
        self.viz.heatmap(np.vstack([scaled_utility_params, scaled_holdings]),
                         env=self.env_name, win=window_name,
                         opts=dict(
                             title="{}'s Utilities vs Holdings".format(repr(self.agent_name)),
                             rownames=["Utilities", "Holdings"],
                             xlabel="Goods"))

    def _update_score(self, agent_state: AgentState, append: bool = True) -> None:

        window_name = "{}_score_history".format(self.env_name)
        self.viz.line(X=[self._update_nb_agent_state], Y=[agent_state.get_score()], update="append" if append else "replace",
                      env=self.env_name, win=window_name,
                      opts=dict(
                          title="{}'s Score".format(repr(self.agent_name)),
                          xlabel="Transactions",
                          ylabel="Score"))

    def _update_balance(self, agent_state: AgentState, append: bool = True) -> None:

        window_name = "{}_balance_history".format(self.env_name)
        self.viz.line(X=[self._update_nb_agent_state], Y=[agent_state.balance], env=self.env_name, win=window_name,
                      update="append" if append else "replace",
                      opts=dict(
                          title="{}'s Balance".format(repr(self.agent_name)),
                          xlabel="Transactions",
                          ylabel="Score"))

    def _update_search_count(self, stats_manager: StatsManager, append: bool = True) -> None:

        window_name = "{}_search_count".format(self.env_name)
        self.viz.line(X=[self._update_nb_stats_manager], Y=[stats_manager.mail_stats.search_count], update="append" if append else "replace",
                      env=self.env_name, win=window_name,
                      opts=dict(
                          title="{}'s Search Count".format(repr(self.agent_name)),
                          xlabel="Ticks",
                          ylabel="Search Count"))

    def _update_avg_search_time(self, stats_manager: StatsManager, append: bool = True) -> None:

        window_name = "{}_avg_search_time".format(self.env_name)
        self.viz.line(X=[self._update_nb_stats_manager], Y=[stats_manager.avg_search_time()], update="append" if append else "replace",
                      env=self.env_name, win=window_name,
                      opts=dict(
                          title="{}'s Avg Search Time".format(repr(self.agent_name)),
                          xlabel="Ticks",
                          ylabel="Avg Search Time"))

    def _update_avg_search_result_counts(self, stats_manager: StatsManager, append: bool = True) -> None:

        window_name = "{}_avg_search_result_counts".format(self.env_name)
        self.viz.line(X=[self._update_nb_stats_manager], Y=[stats_manager.avg_search_result_counts()], update="append" if append else "replace",
                      env=self.env_name, win=window_name,
                      opts=dict(
                          title="{}'s Avg Search Result Counts".format(repr(self.agent_name)),
                          xlabel="Ticks",
                          ylabel="Avg Search Result Counts"))

    def _update_negotiation_metrics_self(self, stats_manager: StatsManager, append: bool = True) -> None:

        window_name = "{}_negotiation_metrics_self".format(self.env_name)
        self.viz.line(X=[self._update_nb_stats_manager], Y=[stats_manager.negotiation_metrics_self()], update="append" if append else "replace",
                      env=self.env_name, win=window_name,
                      opts=dict(
                          legend=['successful', 'declined cfp', 'declined propose', 'declined accept'],
                          title="{}'s Negotiation Counts (Self Initiated)".format(repr(self.agent_name)),
                          xlabel="Ticks",
                          ylabel="Count"))

    def _update_negotiation_metrics_other(self, stats_manager: StatsManager, append: bool = True) -> None:

        window_name = "{}_negotiation_metrics_other".format(self.env_name)
        self.viz.line(X=[self._update_nb_stats_manager], Y=[stats_manager.negotiation_metrics_other()], update="append" if append else "replace",
                      env=self.env_name, win=window_name,
                      opts=dict(
                          legend=['successful', 'declined cfp', 'declined propose', 'declined accept'],
                          title="{}'s Negotiation Counts (Other Initiated)".format(repr(self.agent_name)),
                          xlabel="Ticks",
                          ylabel="Count"))

    def update_from_agent_state(self, agent_state: AgentState, append: bool = True) -> None:
        """Update the dashboard from the agent state."""
        if not self._is_running():
            raise Exception("Dashboard not running, update not allowed.")

        self._update_nb_agent_state += 1
        self._update_holdings(agent_state)
        self._update_score(agent_state, append=append)
        self._update_balance(agent_state, append=append)

    def update_from_stats_manager(self, stats_manager: StatsManager, append: bool = True) -> None:
        """Update the dashboard from the stats manager."""
        if not self._is_running():
            raise Exception("Dashboard not running, update not allowed.")

        self._update_nb_stats_manager += 1
        self._update_search_count(stats_manager, append=append)
        self._update_avg_search_time(stats_manager, append=append)
        self._update_avg_search_result_counts(stats_manager, append=append)
        self._update_negotiation_metrics_self(stats_manager, append=append)
        self._update_negotiation_metrics_other(stats_manager, append=append)
