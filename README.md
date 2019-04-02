# tac-agents
OEF Agents for Trading Agents Competition

## Repository structure

- `data/`: default folder for store the simulation data.
- `docker-images`: submodule to the [docker-images](https://github.com/uvue-git/docker-images.git)
- `docker-tac-develop`: Docker image for the development of TAC related stuff.  
- `docs`: the docs for this project.
- `examples`: some examples/demos showin gthe usage of this package.
- `oef-core` and `oef-sdk-python`: submodules associated to the projects.
- `sandbox`: setup for using Docker compose.
- `scripts`: list of scripts for different purposes (e.g. do data analysis)
- `tac`: the main folder containing the Python package.
- `tests`: tests for the package.


## Dependencies

- The project requires the [Google Protocol Buffers](https://developers.google.com/protocol-buffers/) compiler. A guide on how to install it is found [here](https://fetchai.github.io/oef-sdk-python/user/install.html#protobuf-compiler).
- All python specific dependencies are specified in the Pipfile.

## Preliminaries

- Create and launch a virtual environment:

      pipenv --python 3.6.8 && pipenv shell

- Install the package:

      python3 setup.py install 


- In a different terminal window launch an OEF Node. You can find out how to do it [here](https://fetchai.github.io/oef-sdk-python/user/oef-node.html).

## Agents

- `controller`: the agent that handles the competition;
- `baseline`: a baseline agent with a trivial strategy.



