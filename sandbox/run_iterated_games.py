#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import inspect
import json
import os
import pprint
import random
import subprocess
from collections import defaultdict
from typing import List, Dict, Any

from tac.platform.stats import GameStats

OUR_DIRECTORY = os.path.dirname(inspect.getfile(inspect.currentframe()))
ROOT_DIR = os.path.join(OUR_DIRECTORY, "..")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser("run_iterated_games",
                                     description="Run the sandbox multiple times and collect scores for every run.")
    parser.add_argument("--nb_games", type=int, default=1, help="How many times the competition must be run.")
    parser.add_argument("--output_dir", type=str, default="TAC", help="The directory that will contain all the data for every game.")
    parser.add_argument("--seeds", nargs="+", type=int, default=[], help="The list of seeds to use for different games.")
    parser.add_argument("--config", type=str, default=None, help="The path for a config file (in JSON format). "
                                                                 "If None, use only command line arguments. "
                                                                 "The config file overrides the command line options.")

    arguments = parser.parse_args()
    return arguments


def build_tac_env_variables(tournament_id: str, experiment_id: str, seed: int) -> str:
    """
    Return a sequence of
    'VARIABLE_1=VALUE_1 VARIABLE_2=VALUE_2 ...'
    """

    return "DATA_OUTPUT_DIR={} EXPERIMENT_ID={} SEED={}".format(tournament_id, experiment_id, seed)


def run_games(game_names: List[str], seeds: List[int], output_data_dir: str = "data"):
    """
    Run a TAC for every game name in the input list.
    :param game_names: the name of the TAC competition to run.
    :param seeds: the list of random seeds
    :param output_data_dir: the output directory
    :return:
    """
    assert len(game_names) == len(seeds)
    for i, game_name in enumerate(game_names):
        print("Start iteration {:02d}...".format(i + 1))
        cmd = "docker-compose up --abort-on-container-exit"
        custom_env = build_tac_env_variables(output_data_dir, game_name, seeds[i])
        full_cmd = custom_env + " " + cmd
        print(full_cmd)
        p = subprocess.Popen([full_cmd], shell=True)
        p.wait()


def collect_data(datadir: str, experiment_names: List[str]) -> List[GameStats]:
    """
    Collect data of every experiment.
    :param datadir: path to the directory where the data of the experiments are saved.
    :param experiment_names: the names of the experiments
    :return:
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
    print("Final scores:")
    for agent_name, score in scores_by_name.items():
        print(agent_name, score)


def _process_seeds(arguments: Dict[str, Any]) -> List[int]:
    seeds = list(arguments["seeds"])
    if len(seeds) < arguments["nb_games"]:
        print("Filling missing random seeds...")
        seeds += [random.randint(1, 1000) for _ in range(arguments["nb_games"] - len(seeds))]

    return seeds


def main():
    arguments = parse_args()

    # process input
    args_dict = vars(arguments)
    json_dict = json.load(open(arguments.config)) if arguments.config is not None else {}
    pprint.pprint(json_dict)
    args_dict.update(json_dict)

    print("Arguments:")
    pprint.pprint(args_dict)

    game_names = ["game_{:02d}".format(i) for i in range(args_dict["nb_games"])]
    seeds = _process_seeds(args_dict)
    output_dir = args_dict["output_dir"]

    # do the job
    run_games(game_names, seeds, output_data_dir=output_dir)

    # process the output
    all_game_stats = collect_data(output_dir, game_names)
    scores_by_name = compute_aggregate_scores(all_game_stats)
    print_aggregate_scores(scores_by_name)


if __name__ == '__main__':
    main()
