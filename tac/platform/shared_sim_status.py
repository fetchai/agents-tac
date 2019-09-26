import os;


def register_shared_dir(temp_dir) -> None:
    os.environ['TAC_SHARED_DIR'] = temp_dir

def construct_temp_filename(id_name) -> None:
    shared_dir = os.getenv('TAC_SHARED_DIR')
    if shared_dir is not None and os.path.isdir(shared_dir):
        return os.path.join(shared_dir, "temp_" + id_name + "_status.txt")
    return None



def set_shared_status(id_name, status) -> None:
    temp_file_path = construct_temp_filename(id_name)
    if temp_file_path is not None:
        f = open(temp_file_path, "w+")
        f.write(status)
        f.close()

def get_shared_status(id_name):
    temp_file_path = construct_temp_filename(id_name)
    if temp_file_path is not None:
        if (os.path.isfile(temp_file_path)):
            f = open(temp_file_path, "r")
            status = f.read()
            f.close()
            return status

    return "Invalid status"


def get_last_status_time(id_name):
    return os.path.getmtime(construct_temp_filename(id_name))
