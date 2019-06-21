# -*- coding: utf-8 -*-
from abc import ABC, abstractmethod
from typing import Optional

from tac.gui.dashboards.controller import ControllerDashboard

from tac.platform.stats import GameStats


class Monitor(ABC):

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
        """Check if the monitor is running"""


class NullMonitor(Monitor):

    def __init__(self):
        self._is_running = False

    def start(self, game_stats: GameStats):
        self._is_running = True

    def update(self):
        pass

    def stop(self):
        self._is_running = False

    def is_running(self) -> bool:
        return self._is_running


class VisdomMonitor(Monitor):

    def __init__(self, visdom_addr: str = "localhost", visdom_port: int = 8097):
        self.visdom_addr = visdom_addr
        self.visdom_port = visdom_port
        self.dashboard = None  # type: Optional[ControllerDashboard]

    @property
    def is_running(self) -> bool:
        return self.dashboard is not None

    def start(self, game_stats: GameStats):
        if self.is_running:
            raise Exception("A dashboard is already running.")
        self.dashboard = ControllerDashboard(game_stats, self.visdom_addr, self.visdom_port)
        self.dashboard.start()

    def update(self):
        self.dashboard.update()

    def set_gamestats(self, game_stats: GameStats):
        self.dashboard.game_stats = game_stats

    def stop(self):
        if not self.is_running:
            raise Exception("The dashboard not running.")
        self.dashboard.stop()
        self.dashboard = None
