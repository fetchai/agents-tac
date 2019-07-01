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
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------

"""A script to run several games in a row."""

import argparse
import datetime
import inspect
import json
import logging
import os
import pprint
import random
import shutil
import subprocess
import time
from collections import defaultdict
from typing import List, Dict, Any

from tac.platform.stats import GameStats

OUR_DIRECTORY = os.path.dirname(inspect.getfile(inspect.currentframe()))
ROOT_DIR = os.path.join(OUR_DIRECTORY, "..")

logging.basicConfig(level=logging.INFO)


def parse_args() -> argparse.Namespace:
    """Argument parsing."""
    parser = argparse.ArgumentParser("run_iterated_games",
                                     description="Run the sandbox multiple times and collect scores for every run.")
    parser.add_argument("--nb_games", type=int, default=1, help="How many times the competition must be run.")
    parser.add_argument("--output_dir", type=str, default="TAC", help="The directory that will contain all the data for every game.")
    parser.add_argument("--seeds", nargs="+", type=int, default=[], help="The list of seeds to use for different games.")
    parser.add_argument("--skip", action="store_true", help="Don't ask to user for continuation.")
    parser.add_argument("--interval", type=int, default=5, help="The minimum number of minutes to wait for the next TAC."
                                                                "E.g. if 5, and the time is 09:00, "
                                                                "then the next competition will start at 09:05:00.")
    parser.add_argument("--config", type=str, default=None, help="The path for a config file (in JSON format). "
                                                                 "If None, use only command line arguments. "
                                                                 "The config file overrides the command line options.")

    arguments = parser.parse_args()
    return arguments


def build_tac_env_variables(tournament_id: str, experiment_id: str, seed: int) -> str:
    """
    Return a sequence of 'VARIABLE_1=VALUE_1 VARIABLE_2=VALUE_2 ...'.

    :param tournament_id: the id of the tournament
    :param experiment_id: the id of the experiment
    :param seed: the seed for the random module
    :return: a string encapsulating the params
    """
    return "DATA_OUTPUT_DIR={} EXPERIMENT_ID={} SEED={}".format(tournament_id, experiment_id, seed)


def ask_for_continuation(iteration: int) -> bool:
    """
    Ask the user if we can proceed to execute the sandbox.

    :param iteration: the iteration number.
    :return: True if the user decided to continue the execution, False otherwise.
    """
    try:
        answer = input("Would you like to proceed with iteration {}? [y/N]".format(iteration))
        if answer != "y":
            return False
        else:
            return True
    except EOFError:
        return False


def run_sandbox(game_name: str, seed: int, output_data_dir: str) -> int:
    """
    Run an instance of the sandbox.

    :param game_name: the name of the game
    :param seed: the seed for the random module
    :param output_data_dir: the name of the directory for the output data
    :return: the return code for the execution of Docker Compose.
    """
    cmd = "docker-compose up --abort-on-container-exit"
    custom_env = build_tac_env_variables(output_data_dir, game_name, seed)
    full_cmd = custom_env + " " + cmd
    logging.info(full_cmd)
    p = subprocess.Popen([full_cmd], shell=True)
    return_code = p.wait()
    return return_code


def wait_at_least_n_minutes(n: int):
    """
    Wait for n minutes.

    :param n: the number of minutes to wait
    :return: None
    """
    now = datetime.datetime.now()
    timedelta = datetime.timedelta(0, (n + 1) * 60 - now.second, - now.microsecond)
    start_time = now + timedelta
    seconds_to_sleep = (start_time - now).seconds

    logging.info("The next competition will start at {}".format(start_time))
    logging.info("Sleeping for {} seconds...".format(seconds_to_sleep))
    time.sleep(seconds_to_sleep)
    logging.info("... Done.")


def run_games(game_names: List[str], seeds: List[int], output_data_dir: str = "data", interval: int = 5, skip: bool = False) -> List[str]:
    """
    Run a TAC for every game name in the input list.

    :param game_names: the name of the TAC competition to run.
    :param seeds: the list of random seeds
    :param output_data_dir: the output directory
    :param interval: the number of minutes to wait between different TAC instances
    :param skip: if True, the script skips asking the user for continuation.
    :return: the list of game names executed correctly (return code equal to 0)
    """
    assert len(game_names) == len(seeds)
    correctly_executed_games: List[str] = []

    for i, game_name in enumerate(game_names):

        if not skip:
            shall_continue: bool = ask_for_continuation(i)
            if not shall_continue:
                break

        wait_at_least_n_minutes(interval)

        logging.info("Start iteration {:02d}...".format(i + 1))
        return_code = run_sandbox(game_name, seeds[i], output_data_dir)
        logging.info("Return code: {}".format(return_code))
        if return_code == 0:
            correctly_executed_games.append(game_name)

    if len(correctly_executed_games) < len(game_names):
        logging.warning("Not all the games have been executed correctly.")

    return correctly_executed_games


def collect_data(datadir: str, experiment_names: List[str]) -> List[GameStats]:
    """
    Collect data of every experiment.

    :param datadir: path to the directory where the data of the experiments are saved.
    :param experiment_names: the names of the experiments
    :return: a list of statistics about games
    """
    result = []
    for experiment_name in experiment_names:
        json_experiment_data = json.load(open(os.path.join(datadir, experiment_name, "game.json")))
        game_stats = GameStats.from_json(json_experiment_data)
        result.append(game_stats)

    return result


def compute_aggregate_scores(all_game_stats: List[GameStats]) -> Dict[str, float]:
    """
    Compute the sum of all scores for every agents.

    :param all_game_stats: the GameStats object for every instance of TAC.
    :return: a dictionary "agent_name" -> "final score"
    """
    result = defaultdict(lambda: 0)
    for game_stats in all_game_stats:
        agent_names = game_stats.game.configuration.agent_names
        agent_scores = game_stats.game.get_scores()
        for name, score in zip(agent_names, agent_scores):
            result[name] += score
    return result


def print_aggregate_scores(scores_by_name: Dict[str, float]):
    """
    Print the aggregate scores.

    :param scores_by_name: a dictionary mapping the names to scores.
    """
    if len(scores_by_name) == 0:
        print("No scores.")
    else:
        print("Final scores:")
        final_ranking = sorted(scores_by_name.items(), key=lambda x: x[1], reverse=True)
        for agent_name, score in final_ranking:
            print(agent_name, score)


def _process_seeds(arguments: Dict[str, Any]) -> List[int]:
    seeds = list(arguments["seeds"])
    if len(seeds) < arguments["nb_games"]:
        logging.info("Filling missing random seeds...")
        seeds += [random.randint(1, 1000) for _ in range(arguments["nb_games"] - len(seeds))]

    return seeds


def main():
    """Run the script."""
    arguments = parse_args()

    # process input
    args_dict = vars(arguments)
    json_dict = json.load(open(arguments.config)) if arguments.config is not None else {}
    args_dict.update(json_dict)

    logging.info("Arguments: {}".format(pprint.pformat(args_dict)))

    game_names = ["game_{:02d}".format(i) for i in range(args_dict["nb_games"])]
    seeds = _process_seeds(args_dict)
    output_dir = args_dict["output_dir"]
    logging.info("Removing directory {}...".format(repr(output_dir)))
    shutil.rmtree(output_dir, ignore_errors=True)

    # do the job
    correctly_executed_games: List[str] = run_games(game_names, seeds, output_data_dir=output_dir, interval=args_dict["interval"], skip=args_dict["skip"])

    # process the output
    all_game_stats = collect_data(output_dir, correctly_executed_games)
    scores_by_name = compute_aggregate_scores(all_game_stats)
    print_aggregate_scores(scores_by_name)


if __name__ == '__main__':
    main()
