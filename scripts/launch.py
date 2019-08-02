#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Start a sandbox."""

import inspect
import os
import subprocess
from typing import Optional

CUR_PATH = inspect.getfile(inspect.currentframe())
ROOT_DIR = os.path.join(os.path.dirname(CUR_PATH), "..")

if __name__ == '__main__':
    process = None  # type: Optional[subprocess.Popen]
    try:
        process = subprocess.Popen(["docker-compose", "up", "--abort-on-container-exit"],
                                   env=os.environ,
                                   cwd=os.path.join(ROOT_DIR, "sandbox"))
        process.wait()
    finally:
        if process is not None:
            process.terminate()
