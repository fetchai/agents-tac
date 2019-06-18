# tac-agents

Framework for Trading Agents Competition

## Cloning

This repository contains submodules. Clone with recursive strategy:

	  git clone git@github.com:uvue-git/tac-agents.git --recursive && cd tac-agents

## Quick Links

### 📜 📜 📜 Specification 📜 📜 📜

[For the framework specification go here](../master/docs/Trading_Agent_Competition____Specification.pdf)

### 📁 📁 📁 Documentation 📁 📁 📁

[For the package documentation go here](../master/docs)

### 🤖 🤖 🤖 Simulation 🤖 🤖 🤖 

[For the simulations go here](../master/examples/simulation_demo)

### 🛠🛠🛠 Templates 🛠🛠🛠

[For the agent templates go here](../master/templates)

### 🏆 🏆 🏆 Competition 🏆 🏆 🏆 

[For the competition sandbox go here](../master/sandbox)

## Repository structure

- `data`: default folder for storage of the simulation data.
- `docker-images`: submodule to the [docker-images](https://github.com/uvue-git/docker-images.git)
- `docker-tac-develop`: Docker image for the development of TAC related stuff.  
- `docs`: the docs for this project.
- `examples`: some examples/demos showing the usage of this package (including simulation of the TAC).
- `notebooks`: contains jupyter notebooks with exploratory code.
- `proto`: contains the protobuf schema.
- `sandbox`: setup for using Docker compose.
- `tac`: the main folder containing the Python package.
- `templates`: template agents.
- `tests`: tests for the package.

## Dependencies

- The project requires the [Google Protocol Buffers](https://developers.google.com/protocol-buffers/) compiler. A guide on how to install it is found [here](https://fetchai.github.io/oef-sdk-python/user/install.html#protobuf-compiler).
- All python specific dependencies are specified in the Pipfile (and installed via the commands specified in 'Preliminaries').
- The package requires that you install [Docker](https://www.docker.com/) and the sanbox requires that you in addition install [Docker Compose](https://docs.docker.com/compose/).
- The project requires oef-search-pluto which can be pulled here:
	
	  docker pull fetchai/oef-search:v4

## Preliminaries

- Create and launch a virtual environment:

      pipenv --python 3.7 && pipenv shell

- Install the package:

      python3 setup.py install

## Development

The following steps are only relevant if you intend to contribute to the repository.

- Install development dependencies:

	  pipenv install --dev

- After each change to the codebase re-install package:

      python3 setup.py install

- After changes to the protobuf schema run:

	  python setup.py protoc

- To run tests (ensure no oef docker containers are running):

      tox -e py37

- To run linters:

      tox -e flake8

- To start OEF (latest build):

```
python3 oef_search_pluto_scripts/launch.py -c ./oef_search_pluto_scripts/launch_config_latest.json
``` 


## Resources

- Detailed documentation of the OEF Python SDK is available [here](https://fetchai.github.io/oef-sdk-python/oef.html).
