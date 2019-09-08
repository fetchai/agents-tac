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

"""Implement the sandbox resource and other utility classes."""

# import datetime
import logging
import os
import subprocess
from enum import Enum
from queue import Queue
from typing import Dict, Any, Optional

from flask_restful import Resource, reqparse

from tac import ROOT_DIR

logger = logging.getLogger(__name__)

parser = reqparse.RequestParser()
parser.add_argument("nb_agents", type=int, default=10, help="(minimum) number of TAC agent to wait for the competition.")
parser.add_argument("nb_goods", type=int, default=10, help="Number of TAC agent to run.")
parser.add_argument("money_endowment", type=int, default=200, help="Initial amount of money.")
parser.add_argument("base_good_endowment", default=2, type=int, help="The base amount of per good instances every agent receives.")
parser.add_argument("lower_bound_factor", default=0, type=int, help="The lower bound factor of a uniform distribution.")
parser.add_argument("upper_bound_factor", default=0, type=int, help="The upper bound factor of a uniform distribution.")
parser.add_argument("tx_fee", default=0.1, type=float, help="The transaction fee.")
# parser.add_argument("start_time", default=str(datetime.datetime.now() + datetime.timedelta(0, 10)), type=str, help="The start time for the competition (in UTC format).")
parser.add_argument("registration_timeout", default=10, type=int, help="The amount of time (in seconds) to wait for agents to register before attempting to start the competition.")
parser.add_argument("inactivity_timeout", default=60, type=int, help="The amount of time (in seconds) to wait during inactivity until the termination of the competition.")
parser.add_argument("competition_timeout", default=240, type=int, help="The amount of time (in seconds) to wait from the start of the competition until the termination of the competition.")
parser.add_argument("nb_baseline_agents", type=int, default=10, help="Number of baseline agent to run. Defaults to the number of agents of the competition.")
parser.add_argument("data_output_dir", default="data", help="The output directory for the simulation data.")
parser.add_argument("experiment_id", default=None, help="The experiment ID.")
parser.add_argument("seed", default=42, help="The random seed of the simulation.")
parser.add_argument("whitelist_file", default="", type=str, help="The file that contains the list of agent names to be whitelisted.")
parser.add_argument("services_interval", default=5, type=int, help="The amount of time (in seconds) the baseline agents wait until it updates services again.")
parser.add_argument("pending_transaction_timeout", default=120, type=int, help="The amount of time (in seconds) the baseline agents wait until the transaction confirmation.")
parser.add_argument("register_as", choices=['seller', 'buyer', 'both'], default='both', help="The string indicates whether the baseline agent registers as seller, buyer or both on the oef.")
parser.add_argument("search_for", choices=['sellers', 'buyers', 'both'], default='both', help="The string indicates whether the baseline agent searches for sellers, buyers or both on the oef.")

sandboxes = {}  # type: Dict[int, SandboxRunner]
sandbox_queue = Queue()  # type: Queue


class SandboxState(Enum):
    """The state of execution of a sandbox."""

    NOT_STARTED = "Not started yet"
    RUNNING = "Running"
    FINISHED = "Finished"
    FAILED = "Failed"


class SandboxRunner:
    """Wrapper class to track the execution of a sandbox."""

    def __init__(self, id: int, params: Dict[str, Any]):
        """
        Initialize the sandbox runner.

        :param id: an identifier for the object.
        :param params: the parameters of the simulation.
        """
        self.id = id
        self.params = params

        self.process = None  # type: Optional[subprocess.Popen]

    def __call__(self):
        """Launch the sandbox."""
        if self.status != SandboxState.NOT_STARTED:
            return

        args = self.params
        env = {
            "NB_AGENTS": str(args["nb_agents"]),
            "NB_GOODS": str(args["nb_goods"]),
            "NB_BASELINE_AGENTS": str(args["nb_baseline_agents"]),
            "SERVICES_INTERVAL": str(args["services_interval"]),
            "REGISTER_AS": str(args["register_as"]),
            "SEARCH_FOR": str(args["search_for"]),
            "PENDING_TRANSACTION_TIMEOUT": str(args["pending_transaction_timeout"]),
            "OEF_ADDR": "172.28.1.1",
            "OEF_PORT": "10000",
            "DATA_OUTPUT_DIR": str(args["data_output_dir"]),
            "EXPERIMENT_ID": str(args["experiment_id"]),
            "LOWER_BOUND_FACTOR": str(args["lower_bound_factor"]),
            "UPPER_BOUND_FACTOR": str(args["upper_bound_factor"]),
            "TX_FEE": str(args["tx_fee"]),
            "REGISTRATION_TIMEOUT": str(args["registration_timeout"]),
            "INACTIVITY_TIMEOUT": str(args["inactivity_timeout"]),
            "COMPETITION_TIMEOUT": str(args["competition_timeout"]),
            "SEED": str(args["seed"]),
            "WHITELIST": str(args["whitelist_file"]),
            **os.environ
        }
        self.process = subprocess.Popen([
            "docker-compose",
            "-f",
            os.path.join(ROOT_DIR, "sandbox", "docker-compose.yml"),
            "up",
            "--abort-on-container-exit"],
            env=env)

    @property
    def status(self) -> SandboxState:
        """Return the state of the execution."""
        if self.process is None:
            return SandboxState.NOT_STARTED
        returncode = self.process.poll()
        if returncode is None:
            return SandboxState.RUNNING
        elif returncode == 0:
            return SandboxState.FINISHED
        elif returncode > 0:
            return SandboxState.FAILED
        else:
            raise ValueError("Unexpected return code.")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the object into a dictionary."""
        return {
            "id": self.id,
            "status": self.status.value,
            "params": self.params
        }

    def stop(self) -> None:
        """Stop the execution of the sandbox."""
        if self.process is None:
            return
        try:
            self.process.terminate()
            self.process.wait()
            return
        except Exception:
            raise

    def wait(self):
        """Wait for the completion of the sandbox."""
        return self.process.wait()


class Sandbox(Resource):
    """The sandbox REST resource."""

    def get(self, sandbox_id):
        """Get the current instance of the sandbox."""
        if sandbox_id in sandboxes:
            return sandboxes[sandbox_id].to_dict(), 200
        else:
            return None, 404

    def delete(self, sandbox_id):
        """Delete the current sandbox instance."""
        if sandbox_id not in sandboxes:
            return None, 404
        else:
            sandbox = sandboxes[sandbox_id]
            sandbox.stop()
            return {}, 204


class SandboxList(Resource):
    """Resource to handle sandboxes."""

    def get(self):
        """Get all the sandboxes."""
        return {sandbox_id: sandbox.to_dict() for sandbox_id, sandbox in sandboxes.items()}

    def post(self):
        """Create a sandbox instance."""
        # parse the arguments
        args = parser.parse_args()
        logger.debug("Args: \n{}".format(str(args)))
        sandbox_id = len(sandboxes)
        args = self._post_args_preprocessing(args, sandbox_id)

        # create the simulation runner wrapper
        simulation_runner = SandboxRunner(sandbox_id, args)

        # save the created simulation to the global state
        sandboxes[sandbox_id] = simulation_runner

        global sandbox_queue
        sandbox_queue.put(simulation_runner)
        return simulation_runner.to_dict(), 202

    def _post_args_preprocessing(self, args, sandbox_id):
        """Process the arguments of the POST request on /api/sandbox."""
        if args["data_output_dir"] == "":
            args["data_output_dir"] = "./data"
        if args["experiment_id"] == "" or args["experiment_id"] is None:
            args["experiment_id"] = "./experiment-{}".format(sandbox_id)
        # if args["start_time"] == "":
        #     args["start_time"] = str(datetime.datetime.now())
        # else:
        #     args["start_time"] = str(datetime.datetime.strptime(args["start_time"], "%m/%d/%Y %I:%M %p"))
        return args
