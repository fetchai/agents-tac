# tac-agents
Agents for Trading Agents Competition

## Cloning

This repository contains submodules. Clone with recursive strategy:

	  git clone git@github.com:uvue-git/tac-agents.git --recursive && cd tac-agents

## Repository structure

- `data`: default folder for storage of the simulation data.
- `docker-images`: submodule to the [docker-images](https://github.com/uvue-git/docker-images.git)
- `docker-tac-develop`: Docker image for the development of TAC related stuff.  
- `docs`: the docs for this project.
- `examples`: some examples/demos showing the usage of this package (including simulation of the TAC).
- `notebooks`: contains jupyter notebooks with exploratory code.
- `proto`: contains the protobuf schema.
- `sandbox`: setup for using Docker compose.
- `scripts`: list of scripts for different purposes (e.g. do data analysis)
- `tac`: the main folder containing the Python package.
- `tests`: tests for the package.

## Dependencies

- The project requires the [Google Protocol Buffers](https://developers.google.com/protocol-buffers/) compiler. A guide on how to install it is found [here](https://fetchai.github.io/oef-sdk-python/user/install.html#protobuf-compiler).
- All python specific dependencies are specified in the Pipfile.
- The project requires oef-search-pluto which can be pulled here:

	  docker pull qati/oef:latest

## Preliminaries

- Create and launch a virtual environment:

      pipenv --python 3.7 && pipenv shell

- Install the package:

      python3 setup.py install

## Development

- Install development dependencies:

	  pipenv install --dev

- After each change to the codebase re-install package:

      python3 setup.py install

- After changes to the protobuf schema run:

	  python setup.py protoc

- To run tests:

      tox -e py37

- To run linters:

      tox -e flake8
