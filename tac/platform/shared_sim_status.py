import os;
from enum import Enum
from aea.agent import AgentState
import shutil

class ControllerAgentState(Enum):
    STARTING_DOCKER = "Starting docker image"
    STARTING = "Starting controller agent"
    REGISTRATION_OPEN = "Registration is open for agents to connect"
    RUNNING = "Running simulation"
    STOPPING_UNSUFFICIENT_AGENTS = "Stopping due to insufficient agente registered"
    FINISHED_INACTIVITY = "Finished due to inactivity timeout"
    FINISHED_GAME_TIMEOUT = "Finished due to game timeout"


def register_shared_dir(temp_dir) -> None:
    os.environ['TAC_SHARED_DIR'] = temp_dir

def clear_temp_dir() -> None:
    shared_dir = os.getenv('TAC_SHARED_DIR')
    shutil.rmtree(shared_dir)
    os.mkdir(shared_dir)


def construct_temp_filename(id_name) -> None:
    shared_dir = os.getenv('TAC_SHARED_DIR')
    if shared_dir is not None and os.path.isdir(shared_dir):
        return os.path.join(shared_dir, "tempfile_" + id_name + "_status.txt")
    return None


def set_str_status(id_name, status) -> None:
    temp_file_path = construct_temp_filename(id_name)
    if temp_file_path is not None:
        f = open(temp_file_path, "w+")
        f.write(status)
        f.close()

def get_str_status(id_name):
    temp_file_path = construct_temp_filename(id_name)
    if temp_file_path is not None:
        if (os.path.isfile(temp_file_path)):
            f = open(temp_file_path, "r")
            status = f.read()
            f.close()
            return status

    return ""



def set_controller_state(game_id: str, state: ControllerAgentState) -> None:
    set_str_status("controller_" + game_id, str(state.name))


def get_controller_state(game_id: str) -> ControllerAgentState:
    key = get_str_status("controller_" + game_id)
    if key != "":
        return ControllerAgentState[key]
    else:
        return None



def get_controller_last_time(game_id: str, ) -> ControllerAgentState:
    return get_last_status_time("controller_" + game_id)

def remove_controller_state(game_id: str) -> None:
    temp_file_path = construct_temp_filename("controller_" + game_id)
    if temp_file_path is not None:
        os.remove(temp_file_path)




def set_agent_state(game_id: str, state: AgentState) -> None:
    if state is not None:
        set_str_status("agent_" + game_id, str(state.name))
    else:
        set_str_status("agent_" + game_id, "")

def get_agent_state(game_id: str) -> AgentState:
    key = get_str_status("agent_" + game_id)
    if key != "":
        return AgentState[key]
    else:
        return None

def remove_agent_state(game_id: str) -> None:
    temp_file_path = construct_temp_filename("agent_" + game_id)
    if temp_file_path is not None:
        os.remove(temp_file_path)



def get_last_status_time(id_name):
    return os.path.getmtime(construct_temp_filename(id_name))
