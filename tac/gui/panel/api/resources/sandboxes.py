# -*- coding: utf-8 -*-
import datetime
import logging
import os
import subprocess
from enum import Enum
from typing import Dict

import marshmallow as marshmallow
from flask import jsonify
from flask_restful import Resource, reqparse
from marshmallow import fields, Schema

import tac.platform.simulation
from tac.platform.simulation import build_simulation_parameters, SimulationParams

logger = logging.getLogger(__name__)

parser = reqparse.RequestParser()
parser.add_argument("nb_agents", type=int, default=10, help="(minimum) number of TAC agent to wait for the competition.")
parser.add_argument("nb_goods", type=int, default=10, help="Number of TAC agent to run.")
parser.add_argument("money_endowment", type=int, default=200, help="Initial amount of money.")
parser.add_argument("base_good_endowment", default=2, type=int, help="The base amount of per good instances every agent receives.")
parser.add_argument("lower_bound_factor", default=0, type=int, help="The lower bound factor of a uniform distribution.")
parser.add_argument("upper_bound_factor", default=0, type=int, help="The upper bound factor of a uniform distribution.")
parser.add_argument("tx_fee", default=0.1, type=float, help="The transaction fee.")
parser.add_argument("start_time", default=str(datetime.datetime.now() + datetime.timedelta(0, 10)), type=str, help="The start time for the competition (in UTC format).")
parser.add_argument("registration_timeout", default=10, type=int, help="The amount of time (in seconds) to wait for agents to register before attempting to start the competition.")
parser.add_argument("inactivity_timeout", default=60, type=int, help="The amount of time (in seconds) to wait during inactivity until the termination of the competition.")
parser.add_argument("competition_timeout", default=240, type=int, help="The amount of time (in seconds) to wait from the start of the competition until the termination of the competition.")
parser.add_argument("oef_addr", default="127.0.0.1", help="TCP/IP address of the OEF Agent")
parser.add_argument("oef_port", default=10000, help="TCP/IP port of the OEF Agent")
parser.add_argument("nb_baseline_agents", type=int, default=10, help="Number of baseline agent to run. Defaults to the number of agents of the competition.")
parser.add_argument("services_interval", default=5, type=int, help="The amount of time (in seconds) the baseline agents wait until it updates services again.")
parser.add_argument("pending_transaction_timeout", default=120, type=int, help="The amount of time (in seconds) the baseline agents wait until the transaction confirmation.")
parser.add_argument("register_as", choices=['seller', 'buyer', 'both'], default='both', help="The string indicates whether the baseline agent registers as seller, buyer or both on the oef.")
parser.add_argument("search_for", choices=['sellers', 'buyers', 'both'], default='both', help="The string indicates whether the baseline agent searches for sellers, buyers or both on the oef.")
parser.add_argument("data_output_dir", default="data", help="The output directory for the simulation data.")
parser.add_argument("experiment_id", default=None, help="The experiment ID.")
parser.add_argument("seed", default=42, help="The random seed of the simulation.")
parser.add_argument("whitelist_file", default=None, type=str, help="The file that contains the list of agent names to be whitelisted.")

sandboxes = {}  # type: Dict[int, SandboxRunner]


class SandboxState(Enum):
    NOT_STARTED = "Not started yet"
    RUNNING = "Running"
    STOPPED = "Stopped"
    FINISHED = "Finished"
    FAILED = "Failed"


class SandboxRunner:

    def __init__(self, id: int, params: SimulationParams):
        self.id = id
        self.params = params
        self.status = SandboxState.NOT_STARTED  # type: SandboxState

    def __call__(self):
        try:
            self.status = SandboxState.RUNNING
            tac.platform.simulation.run(self.params)
        except KeyboardInterrupt:
            self.status = SandboxState.STOPPED
        except Exception:
            self.status = SandboxState.FAILED

        self.status = SandboxState.FINISHED

    def __dict__(self):
        return {
            "id": self.id,
            "status": self.status,
            "params": self.params
        }


class Sandbox(Resource):

    def get(self, sandbox_id):
        return {}

    def delete(self, sandbox_id):
        return {}


class SandboxList(Resource):

    def get(self):
        return jsonify(list(sandboxes.items()))

    def post(self):
        args = parser.parse_args(strict=True)
        args = self._post_args_preprocessing(args)

        simulation_params = build_simulation_parameters(args)

        # # cannot use multiprocessing module - daemonic process do not allow children processes
        sandbox_id = len(sandboxes)
        # simulation_runner = SandboxRunner(sandbox_id, simulation_params)
        # sandboxes[len(sandboxes)] = simulation_runner
        # tac.platform.simulation.run(simulation_params)
        env = {
            "NB_AGENTS": "10",
            "NB_GOODS": "10",
            "NB_BASELINE_AGENTS": "10",
            "SERVICES_INTERVAL": "5",
            "OEF_ADDR": "172.28.1.1",
            "OEF_PORT": "10000",
            "DATA_OUTPUT_DIR": "data",
            "EXPERIMENT_ID": str(sandbox_id),
            "LOWER_BOUND_FACTOR": "0",
            "UPPER_BOUND_FACTOR": "0",
            "TX_FEE": "0.1",
            "REGISTRATION_TIMEOUT": "30",
            "INACTIVITY_TIMEOUT": "180",
            "COMPETITION_TIMEOUT": "300",
            "SEED": "42",
            "WHITELIST": "''",
            **os.environ
        }

        p = subprocess.Popen([
            "docker-compose",
            "-f",
            "../../../sandbox/docker-compose.yml",
            "up",
            "--abort-on-container-exit"],
            env=env)
        p.wait()
        p.communicate()
        print(p.returncode())
        return args, 201

    def _post_args_preprocessing(self, args):
        if args["data_output_dir"] == "":
            args["data_output_dir"] = "./data"
        if args["experiment_id"] == "":
            args["experiment_id"] = "./experiment"
        if args["start_time"] == "":
            args["start_time"] = str(datetime.datetime.now())
        args["start_time"] = str(args["start_time"])
        args["gui"] = True
        args["visdom_addr"] = "localhost"
        args["visdom_port"] = 8097
        return args