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
import datetime
import time
from enum import Enum
from threading import Thread
from typing import Dict

import numpy as np


class EndState(Enum):
    SUCCESSFUL = 0
    DECLINED_CFP = 1
    DECLINED_PROPOSE = 2
    DECLINED_ACCEPT = 3


class SearchTime(Enum):
    START = 0
    END = 1


class StatsManager(object):
    """Class to handle agent stats."""

    def __init__(self, dashboard, task_timeout: float = 2.0):
        """
        Initialize a StatsManager.

        :param dashboard: The dashboard.
        :param task_timeout: seconds to sleep for the task
        """
        self.dashboard = dashboard
        self._update_stats_task_is_running = False
        self._update_stats_task = None
        self._update_stats_task_timeout = task_timeout

        self._search_start_time = {}  # type: Dict[int, datetime.datetime]
        self._search_timedelta = {}  # type: Dict[int, datetime.timedelta]
        self._search_result_counts = {}  # type: Dict[int, int]

        self._self_initiated_dialogue_stats = {EndState.SUCCESSFUL: 0,
                                               EndState.DECLINED_CFP: 0,
                                               EndState.DECLINED_PROPOSE: 0,
                                               EndState.DECLINED_ACCEPT: 0}  # type: Dict[EndState, int]
        self._other_initiated_dialogue_stats = {EndState.SUCCESSFUL: 0,
                                                EndState.DECLINED_CFP: 0,
                                                EndState.DECLINED_PROPOSE: 0,
                                                EndState.DECLINED_ACCEPT: 0}  # type: Dict[EndState, int]

    @property
    def self_initiated_dialogue_stats(self) -> Dict[EndState, int]:
        return self._self_initiated_dialogue_stats

    @property
    def other_initiated_dialogue_stats(self) -> Dict[EndState, int]:
        return self._other_initiated_dialogue_stats

    def add_dialogue_endstate(self, end_state: EndState, is_self_initiated: bool) -> None:
        """
        Adds dialogue endstate stats.

        :param end_state: the end state of the dialogue
        :param is_self_initiated: whether the dialogue is initiated by the agent or the opponent
        :return: None
        """
        if is_self_initiated:
            self._self_initiated_dialogue_stats[end_state] += 1
        else:
            self._other_initiated_dialogue_stats[end_state] += 1

    def search_start(self, search_id: int) -> None:
        """
        Adds a search id and start time.

        :param search_id: the search id
        :return: None
        """
        assert search_id not in self._search_start_time
        self._search_start_time[search_id] = datetime.datetime.now()

    def search_end(self, search_id: int, nb_search_results: int) -> None:
        """
        Adds a search id and end time.

        :param search_id: the search id
        :param nb_search_results: the number of agents returned in the search result
        :return: None
        """
        assert search_id in self._search_start_time
        assert search_id not in self._search_timedelta
        self._search_timedelta[search_id] = (datetime.datetime.now() - self._search_start_time[search_id]).total_seconds() * 1000
        self._search_result_counts[search_id] = nb_search_results

    def avg_search_time(self) -> float:
        """
        Avg the search timedeltas

        :return: avg search time in seconds
        """
        timedeltas = list(self._search_timedelta.values())
        if len(timedeltas) == 0:
            result = 0
        else:
            result = sum(timedeltas) / len(timedeltas)
        return result

    def avg_search_result_counts(self) -> float:
        """
        Avg the search result counts

        :return: avg search result counts
        """
        counts = list(self._search_result_counts.values())
        if len(counts) == 0:
            result = 0
        else:
            result = sum(counts) / len(counts)
        return result

    def negotiation_metrics_self(self) -> np.ndarray:
        """
        Get the negotiation metrics on self initiated dialogues.

        :return: an array containing the metrics
        """
        return self._negotiation_metrics(self.self_initiated_dialogue_stats)

    def negotiation_metrics_other(self) -> np.ndarray:
        """
        Get the negotiation metrics on other initiated dialogues.

        :return: an array containing the metrics
        """
        return self._negotiation_metrics(self.other_initiated_dialogue_stats)

    def _negotiation_metrics(self, dialogue_stats: Dict[EndState, int]) -> np.ndarray:
        """
        Get the negotiation metrics.

        :param dialogue_stats: the dialogue statistics
        :return: an array containing the metrics
        """
        result = np.zeros((4), dtype=np.int)
        result[0] = dialogue_stats[EndState.SUCCESSFUL]
        result[1] = dialogue_stats[EndState.DECLINED_CFP]
        result[2] = dialogue_stats[EndState.DECLINED_PROPOSE]
        result[3] = dialogue_stats[EndState.DECLINED_ACCEPT]
        return result

    def start(self) -> None:
        """
        Start the stats manager.

        :return: None
        """
        if not self._update_stats_task_is_running:
            self._update_stats_task_is_running = True
            self._update_stats_task = Thread(target=self.update_stats_job)
            self._update_stats_task.start()

    def stop(self) -> None:
        """
        Stop the stats manager.

        :return: None
        """
        if self._update_stats_task_is_running:
            self._update_stats_task_is_running = False
            self._update_stats_task.join()

    def update_stats_job(self) -> None:
        """
        Periodically update the dashboard

        :return: None
        """
        while self._update_stats_task_is_running:
            time.sleep(self._update_stats_task_timeout)
            self.dashboard.update_from_stats_manager(self, append=True)
