# -*- coding: utf-8 -*-
import html
import inspect
import os
from typing import Optional

import numpy as np

from tac.gui.dashboards.base import Dashboard
from tac.helpers.misc import generate_html_table_from_dict, escape_html
from tac.platform.game import AgentState
from tac.platform.protocol import Transaction

CUR_PATH = inspect.getfile(inspect.currentframe())
CUR_DIR = os.path.dirname(CUR_PATH)
ROOT_PATH = os.path.join(CUR_DIR, "..", "..")

DEFAULT_ENV_NAME = "tac_simulation_env_main"


class TransactionTable(object):

    def __init__(self):
        self.tx_table = dict()
        self.tx_table["#"] = []
        # self.tx_table["Transaction ID"] = []
        self.tx_table["Role"] = []
        self.tx_table["Counterparty"] = []
        self.tx_table["Amount"] = []
        self.tx_table["Goods Exchanged"] = []

    def add_transaction(self, tx: Transaction):
        self.tx_table["#"].append(str(len(self.tx_table["#"])))
        print(tx.transaction_id)
        # self.tx_table["Transaction ID"].append("..." + tx.transaction_id[-10:])
        self.tx_table["Role"].append("Buyer" if tx.buyer else "Seller")
        self.tx_table["Counterparty"].append(tx.counterparty[:5] + "..." + tx.counterparty[-5:])
        self.tx_table["Amount"].append("{:02.2f}".format(tx.amount))
        self.tx_table["Goods Exchanged"].append("\n"
                                                .join(map(lambda x: "{}: {}".format(x[0], x[1]),
                                                          filter(lambda x: x[1] > 0,
                                                                 tx.quantities_by_good_pbk.items()))))

    def to_html(self):
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
        super().__init__(visdom_addr, visdom_port, env_name)

        self.agent_name = agent_name

        self._update_nb = -1
        self._transaction_table = TransactionTable()
        self._transaction_window = None

    def init(self):
        self.viz.delete_env(self.env_name)
        self._transaction_window = self.viz.text(self._transaction_table.to_html(), env=self.env_name)

    def add_transaction(self, new_tx: Transaction):
        self._transaction_table.add_transaction(new_tx)
        self.viz.text(self._transaction_table.to_html(), win=self._transaction_window, env=self.env_name)

    def _update_holdings(self, agent_state: AgentState):
        scaled_holdings = agent_state.current_holdings / np.sum(agent_state.current_holdings)
        scaled_utility_params = agent_state.utility_params / np.sum(agent_state.utility_params)

        window_name = "{}_utility_and_holdings".format(self.env_name)
        self.viz.heatmap(np.vstack([scaled_utility_params, scaled_holdings]),
                         env=self.env_name, win=window_name,
                         opts=dict(
                             title="{}'s Utilities vs Holdings".format(repr(self.agent_name)),
                             rownames=["Utilities", "Holdings"],
                             xlabel="Goods"))

    def _update_score(self, agent_state: AgentState, append: bool = True):

        window_name = "{}_score_history".format(self.env_name)
        self.viz.line(X=[self._update_nb], Y=[agent_state.get_score()], update="append" if append else "replace",
                      env=self.env_name, win=window_name,
                      opts=dict(
                          title="{}'s Score".format(repr(self.agent_name)),
                          xlabel="Transactions",
                          ylabel="Score"))

    def _update_balance(self, agent_state: AgentState, append: bool = True):

        window_name = "{}_balance_history".format(self.env_name)
        self.viz.line(X=[self._update_nb], Y=[agent_state.balance], env=self.env_name, win=window_name,
                      update="append" if append else "replace",
                      opts=dict(
                          title="{}'s Balance".format(repr(self.agent_name)),
                          xlabel="Transactions",
                          ylabel="Score"))

    def update_from_agent_state(self, agent_state: AgentState, append: bool = True):
        if not self._is_running():
            raise Exception("Dashboard not running, update not allowed.")

        self._update_nb += 1
        self._update_holdings(agent_state)
        self._update_score(agent_state, append=append)
        self._update_balance(agent_state, append=append)
