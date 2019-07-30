# -*- coding: utf-8 -*-
import datetime
import multiprocessing
import os
import subprocess

from flask_restful import Resource, reqparse

from tac.platform import simulation
from tac.platform.simulation import build_simulation_parameters

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

pool = multiprocessing.Pool(processes=1)

simulations = {}


class Simulation(Resource):

    def get(self):
        return {"get": None}

    def delete(self):
        return {}

    def create(self):
        pass


class SimulationList(Resource):

    def get(self):
        return simulations

    def post(self):
        args = parser.parse_args(strict=True)
        print(args)
        args = self._post_preprocessing(args)

        simulation_params = build_simulation_parameters(args)

        # cannot use multiprocessing module - daemonic process do not allow children processes
        pid = os.fork()
        if pid == 0:
            # here we are in the new process
            simulation.run(simulation_params)
        elif pid > 0:
            return vars(args), 201
        else:
            pass

    def _post_preprocessing(self, args):
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