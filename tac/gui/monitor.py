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

"""Module containing monitor classes."""

from abc import ABC, abstractmethod
from typing import Optional

from tac.gui.dashboards.controller import ControllerDashboard

from tac.platform.stats import GameStats


class Monitor(ABC):
    """Abstract monitor class."""

    @abstractmethod
    def start(self, game_stats: GameStats):
        """Start the monitor."""

    @abstractmethod
    def update(self):
        """Update the monitor."""

    @abstractmethod
    def stop(self):
        """Stop the monitor."""

    @abstractmethod
    def is_running(self) -> bool:
        """Check if the monitor is running."""


class NullMonitor(Monitor):
    """Class for the null monitor."""

    def __init__(self):
        """Instantiate the monitor."""
        self._is_running = False

    def start(self, game_stats: GameStats):
        """Start the monitor."""
        self._is_running = True

    def update(self):
        """Update the monitor."""
        pass

    def stop(self):
        """Stop the monitor."""
        self._is_running = False

    @property
    def is_running(self) -> bool:
        """Check if the monitor is running."""
        return self._is_running


class VisdomMonitor(Monitor):
    """Class for the visdom monitor."""

    def __init__(self, visdom_addr: str = "localhost", visdom_port: int = 8097):
        """Instantiate the monitor."""
        self.visdom_addr = visdom_addr
        self.visdom_port = visdom_port
        self.dashboard = None  # type: Optional[ControllerDashboard]

    @property
    def is_running(self) -> bool:
        """Check if the monitor is running."""
        return self.dashboard is not None

    def start(self, game_stats: GameStats):
        """Start the monitor."""
        if self.is_running:
            raise Exception("A dashboard is already running.")
        self.dashboard = ControllerDashboard(game_stats, self.visdom_addr, self.visdom_port)
        self.dashboard.start()

    def update(self):
        """Update the monitor."""
        self.dashboard.update()

    def set_gamestats(self, game_stats: GameStats):
        """Set the game stats."""
        self.dashboard.game_stats = game_stats

    def stop(self):
        """Stop the monitor."""
        if not self.is_running:
            raise Exception("The dashboard not running.")
        self.dashboard.stop()
        self.dashboard = None
