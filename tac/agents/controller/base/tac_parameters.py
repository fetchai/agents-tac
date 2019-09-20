#!/usr/bin/env python3
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

"""TACParameters: this class contains the parameters for the TAC."""

import datetime
import random

from typing import Set, Optional


class TACParameters(object):
    """This class contains the parameters for the TAC."""

    def __init__(self, min_nb_agents: int = 5,
                 money_endowment: int = 200,
                 nb_goods: int = 5,
                 tx_fee: float = 1.0,
                 base_good_endowment: int = 2,
                 lower_bound_factor: int = 1,
                 upper_bound_factor: int = 1,
                 start_time: datetime.datetime = datetime.datetime.now(),
                 registration_timeout: int = 10,
                 competition_timeout: int = 20,
                 inactivity_timeout: int = 10,
                 whitelist: Optional[Set[str]] = None,
                 data_output_dir: str = "data",
                 version_id: str = str(random.randint(0, 10000))):
        """
        Initialize parameters for TAC.

        :param min_nb_agents: the number of agents to wait for the registration.
        :param money_endowment: The money amount every agent receives.
        :param nb_goods: the number of goods in the competition.
        :param tx_fee: the fee for a transaction.
        :param base_good_endowment:The base amount of per good instances every agent receives.
        :param lower_bound_factor: the lower bound factor of a uniform distribution.
        :param upper_bound_factor: the upper bound factor of a uniform distribution.
        :param start_time: the datetime when the competition will start.
        :param registration_timeout: the duration (in seconds) of the registration phase.
        :param competition_timeout: the duration (in seconds) of the competition phase.
        :param inactivity_timeout: the time when the competition will start.
        :param whitelist: the set of agent names allowed. If None, no checks on the agent names.
        """
        self._min_nb_agents = min_nb_agents
        self._money_endowment = money_endowment
        self._nb_goods = nb_goods
        self._tx_fee = tx_fee
        self._base_good_endowment = base_good_endowment
        self._lower_bound_factor = lower_bound_factor
        self._upper_bound_factor = upper_bound_factor
        self._start_time = start_time
        self._registration_timeout = registration_timeout
        self._competition_timeout = competition_timeout
        self._inactivity_timeout = inactivity_timeout
        self._whitelist = whitelist
        self._data_output_dir = data_output_dir
        self._version_id = version_id
        self._check_values()

    def _check_values(self) -> None:
        """
        Check constructor parameters.

        :raises ValueError: if some parameter has not the right value.
        """
        if self._start_time is None:
            raise ValueError
        if self._inactivity_timeout is None:
            raise ValueError

    @property
    def min_nb_agents(self) -> int:
        """Minimum number of agents required for a TAC instance."""
        return self._min_nb_agents

    @property
    def money_endowment(self):
        """Money endowment per agent for a TAC instance."""
        return self._money_endowment

    @property
    def nb_goods(self):
        """Good number for a TAC instance."""
        return self._nb_goods

    @property
    def tx_fee(self):
        """Transaction fee for a TAC instance."""
        return self._tx_fee

    @property
    def base_good_endowment(self):
        """Minimum endowment of each agent for each good."""
        return self._base_good_endowment

    @property
    def lower_bound_factor(self):
        """Lower bound of a uniform distribution."""
        return self._lower_bound_factor

    @property
    def upper_bound_factor(self):
        """Upper bound of a uniform distribution."""
        return self._upper_bound_factor

    @property
    def start_time(self) -> datetime.datetime:
        """TAC start time."""
        return self._start_time

    @property
    def end_time(self) -> datetime.datetime:
        """TAC end time."""
        return self._start_time + self.registration_timedelta + self.competition_timedelta

    @property
    def registration_timeout(self):
        """Timeout of registration."""
        return self._registration_timeout

    @property
    def competition_timeout(self):
        """Timeout of competition."""
        return self._competition_timeout

    @property
    def inactivity_timeout(self):
        """Timeout of agent inactivity from controller perspective (no received transactions)."""
        return self._inactivity_timeout

    @property
    def registration_timedelta(self) -> datetime.timedelta:
        """Time delta of the registration timeout."""
        return datetime.timedelta(0, self._registration_timeout)

    @property
    def competition_timedelta(self) -> datetime.timedelta:
        """Time delta of the competition timeout."""
        return datetime.timedelta(0, self._competition_timeout)

    @property
    def inactivity_timedelta(self) -> datetime.timedelta:
        """Time delta of the inactivity timeout."""
        return datetime.timedelta(0, self._inactivity_timeout)

    @property
    def whitelist(self) -> Optional[Set[str]]:
        """Whitelist of agent public keys allowed into the TAC instance."""
        return self._whitelist

    @property
    def data_output_dir(self) -> str:
        """Get data output dir."""
        return self._data_output_dir

    @property
    def version_id(self) -> str:
        """Version id."""
        return self._version_id
