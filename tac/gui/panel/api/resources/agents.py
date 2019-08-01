# -*- coding: utf-8 -*-
import datetime
import logging
import os
import subprocess
from enum import Enum
from typing import Dict, Any, Optional

from flask_restful import Resource, reqparse

logger = logging.getLogger(__name__)

parser = reqparse.RequestParser()
parser.add_argument("name", default="my_baseline_agent", help="Name of the agent.")
parser.add_argument("agent_timeout", type=float, default=1.0, help="The time in (fractions of) seconds to time out an agent between act and react.")
parser.add_argument("max_reactions", type=int, default=100, help="The maximum number of reactions (messages processed) per call to react.")
parser.add_argument("register_as", choices=['seller', 'buyer', 'both'], default='both', help="The string indicates whether the baseline agent registers as seller, buyer or both on the oef.")
parser.add_argument("search_for", choices=['sellers', 'buyers', 'both'], default='both', help="The string indicates whether the baseline agent searches for sellers, buyers or both on the oef.")
parser.add_argument("is_world_modeling", type=bool, default=False, help="Whether the agent uses a workd model or not.")
parser.add_argument("services_interval", type=int, default=5, help="The number of seconds to wait before doing another search.")
parser.add_argument("pending_transaction_timeout", type=int, default=30, help="The timeout in seconds to wait for pending transaction/negotiations.")
parser.add_argument("private_key_pem", default=None, help="Path to a file containing a private key in PEM format.")
parser.add_argument("rejoin", type=bool, default=False, help="Whether the agent is joining a running TAC.")

current_agent = None  # type: Optional[AgentRunner]


class AgentState(Enum):
    NOT_STARTED = "not_started"
    RUNNING = "running"
    FINISHED = "finished"
    FAILED = "failed"


class AgentRunner:

    def __init__(self, id: int, params: Dict[str, Any]):
        self.id = id
        self.params = params

        self.process = None  # type: Optional[subprocess.Popen]

    def __call__(self):
        if self.status != AgentState.NOT_STARTED:
            return

        args = ["--name", str(self.params["name"]),
                "--agent-timeout", str(self.params["agent_timeout"]),
                "--max-reactions", str(self.params["max_reactions"]),
                "--register-as", str(self.params["register_as"]),
                "--search-for", str(self.params["search_for"]),
                "--services-interval", str(self.params["services_interval"]),
                "--pending-transaction-timeout", str(self.params["pending_transaction_timeout"])]

        if self.params["is_world_modeling"]:
            args.append("--is-world-modeling")
        if self.params["rejoin"]:
            args.append("--rejoin")
        if self.params["private_key_pem"] is not None:
            args.append("--private-key-pem")
            args.append(self.params["--private-key-pem"])

        self.process = subprocess.Popen([
            "python3",
            "../../../templates/v1/basic.py",
            *args,
            "--gui",
            "--visdom-addr", "127.0.0.1",
            "--visdom-port", "8097",
        ], stdout=subprocess.PIPE)

    @property
    def status(self) -> AgentState:
        if self.process is None:
            return AgentState.NOT_STARTED
        returncode = self.process.poll()
        if returncode is None:
            return AgentState.RUNNING
        elif returncode == 0:
            return AgentState.FINISHED
        elif returncode > 0:
            return AgentState.FAILED

    def to_dict(self):
        return {
            "id": self.id,
            "status": self.status.value,
            "params": self.params
        }

    def stop(self):
        try:
            self.process.terminate()
            self.process.wait()
            return True
        except Exception:
            raise


class Agent(Resource):

    def get(self):
        global current_agent
        if current_agent is not None:
            return current_agent.to_dict(), 200
        else:
            return None, 200

    def post(self):
        global current_agent
        if current_agent is not None and current_agent.status == AgentState.RUNNING:
            # a sandbox is already running
            return None, 400

        # parse the arguments
        args = parser.parse_args(strict=True)

        # create the agent runner wrapper
        agent_runner = AgentRunner(0, args)

        # save the created simulation to the global state
        current_agent = agent_runner

        # run the simulation
        agent_runner()

        return agent_runner.to_dict(), 202

    def delete(self):
        global current_agent
        if current_agent is None:
            return None, 400
        else:
            current_agent.stop()
            current_agent = None
            return {}, 204
