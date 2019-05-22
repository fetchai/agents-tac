# -*- coding: utf-8 -*-
from abc import ABC, abstractmethod
from typing import Optional

from tac.gui.dashboard import Dashboard

from tac.stats import GameStats


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


class NullMonitor(Monitor):

    def start(self, game_stats: GameStats):
        pass

    def update(self):
        pass

    def stop(self):
        pass


class VisdomMonitor(Monitor):

    def __init__(self, visdom_addr: str = "localhost", visdom_port: int = 8097):
        self.visdom_addr = visdom_addr
        self.visdom_port = visdom_port
        self.dashboard = None  # type: Optional[Dashboard]

    def start(self, game_stats: GameStats):
        if self.dashboard is not None:
            raise Exception("A dashboard is already running.")
        self.dashboard = Dashboard(game_stats, self.visdom_addr, self.visdom_port)
        self.dashboard.start()

    def update(self):
        self.dashboard.update()

    def stop(self):
        if self.dashboard is None:
            raise Exception("The dashboard not running.")
        self.dashboard.stop()
        self.dashboard = None

