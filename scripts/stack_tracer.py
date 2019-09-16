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
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------

"""
This module implements a stack tracer for multi-threaded applications.

This is based on: http://code.activestate.com/recipes/577334-how-to-debug-deadlocked-multi-threaded-programs/

Usage:

import stacktracer
stacktracer.start_trace("trace.html",interval=5,auto=True) # Set auto flag to always update file!
....
stacktracer.stop_trace()
"""

import os
import sys
import threading
import time
import traceback

from pygments import highlight
from pygments.formatters.html import HtmlFormatter
from pygments.lexers.python import PythonLexer


def stacktraces() -> str:
    """Tracks stack traces."""
    print('Stacktraces captured!')
    code = []
    for threadId, stack in sys._current_frames().items():
        code.append("\n# ThreadID: {}".format(threadId))
        for filename, lineno, name, line in traceback.extract_stack(stack):
            code.append('File: "{}", line {}, in {}'.format(filename, lineno, name))
            if line:
                code.append("  %s" % (line.strip()))

    return highlight("\n".join(code), PythonLexer(), HtmlFormatter(full=False, style="native", noclasses=True))


class TraceDumper(threading.Thread):
    """Dump stack traces into a given file periodically."""

    def __init__(self, fpath: str, interval: int, auto: bool) -> None:
        """
        Initialize.

        :param fpath: File path to output HTML (stack trace file)
        :param auto: Set flag (True) to update trace continuously.
            Clear flag (False) to update only if file not exists.
            (Then delete the file to force update.)
        :param interval: In seconds: how often to update the trace file.
        :return: None
        """
        assert(interval > 0.1)
        self.auto = auto
        self.interval = interval
        self.fpath = os.path.abspath(fpath)
        self.stop_requested = threading.Event()
        threading.Thread.__init__(self)

    def run(self) -> None:
        """
        Run.

        :return: None
        """
        while not self.stop_requested.isSet():  # type: ignore
            time.sleep(self.interval)
            if self.auto or not os.path.isfile(self.fpath):
                self.stacktraces()

    def stop(self) -> None:
        """
        Stop.

        :return: None
        """
        self.stop_requested.set()
        self.join()
        try:
            if os.path.isfile(self.fpath):
                os.unlink(self.fpath)
        except:  # noqa: E722
            pass

    def stacktraces(self) -> None:
        """
        Stacktraces write.

        :return: None
        """
        fout = open(self.fpath, "w+")
        try:
            fout.write(stacktraces())
        finally:
            fout.close()


_tracer = None


def start_trace(fpath: str, interval: int = 5, auto: bool = True) -> None:
    """
    Start tracing into the given file.

    :param fpath: File path to output HTML (stack trace file)
    :param auto: Set flag (True) to update trace continuously.
        Clear flag (False) to update only if file not exists.
        (Then delete the file to force update.)
    :param interval: In seconds: how often to update the trace file.
    :return: None
    """
    global _tracer
    if _tracer is None:
        _tracer = TraceDumper(fpath, interval, auto)
        _tracer.setDaemon(True)
        _tracer.start()
    else:
        raise Exception("Already tracing to {}".format(_tracer.fpath))


def stop_trace() -> None:
    """
    Stop tracing.

    :return: None
    """
    global _tracer
    if _tracer is None:
        raise Exception("Not tracing, cannot stop.")
    else:
        _tracer.stop()
        _tracer = None
