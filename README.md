# agents-tac

Competition and Agent Frameworks for the Trading Agents Competition

## Cloning

This repository contains submodules. Clone with recursive strategy:

	  git clone git@github.com:fetchai/agents-tac.git --recursive && cd agents-tac

## Quick Start

- [x] You have followed the steps under 'Dependencies' and 'Preliminaries' below
- [x] In one terminal, you have built the sandbox and then launched it:

      cd sandbox && docker-compose build
      docker-compose up

- [x] In another terminal, you have entered the virtual environment and connected a template agent to the sandbox:

      pipenv shell
      python3 templates/v1/basic.py --name my_agent --gui

The sandbox is starting up:
<p align="center">
  <img src="https://github.com/fetchai/agents-tac/blob/master/docs/sandbox.png?raw=true" alt="Sandbox" width="60%"/>
</p>

Once the controller has started the competition, connect the agent:
<p align="center">
  <img src="https://github.com/fetchai/agents-tac/blob/master/docs/agent.png?raw=true" alt="Sandbox" width="60%"/>
</p>

The controller GUI at http://localhost:8097 provides real time insights:
![Controller GUI](../master/docs/controller_gui.png)

- [x] You have had a look at the documentation and are developing your first agent.

## Quick Links

### 📜 📜 📜 Documentation 📜 📜 📜

The [package documentation](../master/docs) introduces the key components of the agent and competition frameworks and helps agent developers getting started. _This is **required** reading material if you want to build your own agent._

### 📏 📏 📏 Specification 📏 📏 📏

The [framework specification](../master/docs/Trading_Agent_Competition____Specification.pdf) introduces the agent and competition frameworks and discusses the project vision and components. _This is complementary reading material._

### 🤖 🤖 🤖 Simulation 🤖 🤖 🤖

The [simulation](../master/simulation) provides code to simulate a competition with a population of baseline agents.

### 🛠🛠🛠 Templates 🛠🛠🛠

The [agent templates](../master/templates) provide starting points for agent development.

### 🏆 🏆 🏆 Competition 🏆 🏆 🏆

The [competition sandbox](../master/sandbox) provides the code to build the docker image to run the competiton.

## Repository structure

- `data`: default folder for storage of the simulation data.
- `docker-images`: submodule to the [docker-images](https://github.com/uvue-git/docker-images.git)
- `docker-tac-develop`: Docker image for the development of TAC related stuff.  
- `docs`: the docs for this project.
- `notebooks`: contains jupyter notebooks with exploratory code.
- `proto`: contains the protobuf schema.
- `sandbox`: setup for using Docker compose.
- `simulation`: contains scripts for simulation of the TAC.
- `tac`: the main folder containing the Python package.
- `templates`: template agents.
- `tests`: tests for the package.

## Dependencies

- All python specific dependencies are specified in the Pipfile (and installed via the commands specified in 'Preliminaries').
- The package requires that you install [Docker](https://www.docker.com/) and the sanbox requires that you in addition install [Docker Compose](https://docs.docker.com/compose/).
- The project requires oef-search-pluto which can be pulled here:
	
	  docker pull fetchai/oef-search:v4

## Preliminaries

- Create and launch a virtual environment:

      pipenv --python 3.7 && pipenv shell

- Install the package:

      python3 setup.py install

## Contribute

The following dependency is only relevant if you intend to contribute to the repository:
- the project uses [Google Protocol Buffers](https://developers.google.com/protocol-buffers/) compiler for message serialization. A guide on how to install it is found [here](https://fetchai.github.io/oef-sdk-python/user/install.html#protobuf-compiler).

The following steps are only relevant if you intend to contribute to the repository. They are not required for agent development.

- Install development dependencies:

	  pipenv install --dev

- Install package in (development mode):

	  pip3 install -e .

- After changes to the protobuf schema run:

	  python setup.py protoc

- To run tests (ensure no oef docker containers are running):

	  tox -e py37

- To run linters:

	  tox -e flake8

- We recommend you use the tested OEF build:

	  python3 oef_search_pluto_scripts/launch.py -c ./oef_search_pluto_scripts/launch_config.json

- To start OEF latest build (the latest build might not be compatible with the current repo):

	  python3 oef_search_pluto_scripts/launch.py -c ./oef_search_pluto_scripts/launch_config_latest.json

## Resources

- Detailed documentation of the OEF Python SDK is available [here](https://fetchai.github.io/oef-sdk-python/oef.html).
