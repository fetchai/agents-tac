# agents-tac

![TAC sanity checks and tests](https://github.com/fetchai/agents-tac/workflows/TAC%20sanity%20checks%20and%20tests/badge.svg)

Competition and Agent Frameworks for the Trading Agents Competition

## Cloning

This repository contains submodules. Clone with recursive strategy:

      git clone git@github.com:fetchai/agents-tac.git --recursive && cd agents-tac

## Option 1: Quick Start:

- [x] Follow the steps under 'Dependencies' and 'Preliminaries' below
- [x] Enter the virtual environment and launched the script:

      pipenv shell
      python scripts/launch.py

The controller GUI at http://localhost:8097 provides real time insights.

## Option 2: Launcher GUI:

- [x] Follow the steps under 'Dependencies' and 'Preliminaries' below
- [x] Build the sandbox:

      cd sandbox && docker-compose build && cd ..

- [x] Enter the virtual environment and start the launcher GUI. Then launch the sandbox with your prefered configs:

      pipenv shell
      python tac/gui/launcher/app.py

The controller GUI at http://localhost:8097 provides real time insights.

## Option 3: Step by step:

- [x] Follow the steps under 'Dependencies' and 'Preliminaries' below
- [x] In one terminal, build the sandbox and then launch it:

      cd sandbox && docker-compose build
      docker-compose up

- [x] Optionally, in another terminal, enter the virtual environment and connect a template agent to the sandbox:

      pipenv shell
      python templates/v1/basic.py --name my_agent --dashboard --expected-version-id tac_v1

The sandbox is starting up:
<p align="center">
  <img src="https://github.com/fetchai/agents-tac/blob/master/docs/sandbox.png?raw=true" alt="Sandbox" width="60%"/>
</p>

Once agent is connected and searching for the competition:
<p align="center">
  <img src="https://github.com/fetchai/agents-tac/blob/master/docs/agent.png?raw=true" alt="Sandbox" width="60%"/>
</p>

The controller GUI at http://localhost:8097 provides real time insights:
![Controller GUI](../master/docs/controller_gui.png)

- [x] Have a look at the documentation and start developing your first agent.

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
- `docker-agent-image`: Lightweight docker image for agent execution.
- `docker-images`: submodule to the [docker-images](https://github.com/uvue-git/docker-images.git)
- `docker-tac-develop`: Docker image for the development of TAC related stuff.  
- `docs`: the docs for this project.
- `notebooks`: contains jupyter notebooks with exploratory code.
- `sandbox`: competition setup using Docker compose.
- `scripts`: scripts to run.
- `simulation`: contains scripts for simulation of the TAC.
- `tac`: the main folder containing the Python package.
- `templates`: template agents.
- `tests`: tests for the package.

## Dependencies

- All python specific dependencies are specified in the Pipfile (and installed via the commands specified in 'Preliminaries').
- The package requires that you install [Docker](https://www.docker.com/) and the sandbox requires that in addition, you install [Docker Compose](https://docs.docker.com/compose/).
- The project requires oef-search-pluto which can be pulled here:
	
	  docker pull fetchai/oef-search:0.7

## Preliminaries

- Create and launch a virtual environment:

      pipenv --python 3.7 && pipenv shell
      
- Install the dependencies:

      pipenv install

- Install the tac package:

      python setup.py install

## Contribute

The following dependency is only relevant if you intend to contribute to the repository:
- the project uses [Google Protocol Buffers](https://developers.google.com/protocol-buffers/) compiler for message serialization. A guide on how to install it is found [here](https://fetchai.github.io/oef-sdk-python/user/install.html#protobuf-compiler).

The following steps are only relevant if you intend to contribute to the repository. They are not required for agent development.

- Clear cache

      pipenv --clear

- Install development dependencies:

      pipenv install --dev

- Install package in (development mode):

      pip install -e .

- After changes to the protobuf schema run:

      python setup.py protoc

- To run tests (ensure no oef docker containers are running):

      tox -e py37

- To run linters (code style checks):

      tox -e flake8

- To run static type checks:

      tox -e mypy

- We recommend you use the latest OEF build:

      python scripts/oef/launch.py -c ./scripts/oef/launch_config.json

## Resources

- Detailed documentation of the OEF Python SDK is available [here](https://fetchai.github.io/oef-sdk-python/oef.html).
