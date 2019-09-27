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

"""Pass status of systems between docker images and processes using the file system and a bind mount in docker."""

import glob
import os
import shutil
from enum import Enum

from aea.agent import AgentState


class ControllerAgentState(Enum):
    """The state of execution of the TAC cotnroller agent."""

    NONE = "State not set"
    STARTING_DOCKER = "Starting docker image"
    STARTING = "Starting controller agent"
    REGISTRATION_OPEN = "Registration is open for agents to connect"
    RUNNING = "Running simulation"
    STOPPING_UNSUFFICIENT_AGENTS = "Stopping due to insufficient agente registered"
    FINISHED_INACTIVITY = "Finished due to inactivity timeout"
    FINISHED_GAME_TIMEOUT = "Finished due to game timeout"


def register_shared_dir(temp_dir) -> None:
    """Call this from somewhere near the entry point of the program to set he location of the temp directory."""
    os.environ['TAC_SHARED_DIR'] = temp_dir


def clear_temp_dir() -> None:
    """Call this once at the beginning (after registering the temp director) - cleans out dir of old status files."""
    shared_dir = str(os.getenv('TAC_SHARED_DIR'))
    # Get a list of all the file paths that ends with .txt from in specified directory
    file_list = glob.glob(os.path.join(shared_dir, '*.txt'))

    # Iterate over the list of filepaths & remove each file.
    for filePath in file_list:
        try:
            os.remove(filePath)
        except:
            print("Error while deleting file : ", filePath)


def set_controller_state(game_id: str, state: ControllerAgentState) -> None:
    """Set controller state."""
    _set_str_status("controller_" + game_id, str(state.name))


def get_controller_state(game_id: str) -> ControllerAgentState:
    """Get controller state."""
    key = _get_str_status("controller_" + game_id)
    if key != "":
        return ControllerAgentState[key]
    else:
        return ControllerAgentState.NONE


def get_controller_last_time(game_id: str, ) -> float:
    """Return the last time the controller state was changed as UTC time."""
    return _get_last_status_time("controller_" + game_id)


def remove_controller_state(game_id: str) -> None:
    """Remove the status file from the temp folder."""
    temp_file_path = _construct_temp_filename("controller_" + game_id)
    if temp_file_path is not None:
        os.remove(temp_file_path)


def set_agent_state(game_id: str, state: AgentState) -> None:
    """Set agent state."""
    if state is not None:
        _set_str_status("agent_" + game_id, str(state.name))
    else:
        _set_str_status("agent_" + game_id, "")


def get_agent_state(game_id: str) -> AgentState:
    """Get agent state."""
    key = _get_str_status("agent_" + game_id)
    if key != "":
        return AgentState[key]
    else:
        # This is well dodgy, but I don't have a good thing to return in this case
        return AgentState.INITIATED


def remove_agent_state(game_id: str) -> None:
    """Remove the status file from the temp folder."""
    temp_file_path = _construct_temp_filename("agent_" + game_id)
    if temp_file_path is not None:
        os.remove(temp_file_path)


def _get_last_status_time(id_name) -> float:
    """Return the last time the agent state was changed as UTC time."""
    return os.path.getmtime(_construct_temp_filename(id_name))


def _construct_temp_filename(id_name) -> str:
    shared_dir = os.getenv('TAC_SHARED_DIR')
    if shared_dir is not None and os.path.isdir(shared_dir):
        return os.path.join(shared_dir, "tempfile_" + id_name + "_status.txt")
    return ""


def _set_str_status(id_name, status) -> None:
    temp_file_path = _construct_temp_filename(id_name)
    if temp_file_path is not None:
        f = open(temp_file_path, "w+")
        f.write(status)
        f.close()


def _get_str_status(id_name):
    temp_file_path = _construct_temp_filename(id_name)
    if temp_file_path is not None:
        if (os.path.isfile(temp_file_path)):
            f = open(temp_file_path, "r")
            status = f.read()
            f.close()
            return status

    return ""
