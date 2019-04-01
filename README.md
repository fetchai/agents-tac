# tac-agents
OEF Agents for Trading Agents Competition

Look at the `examples/` for a better understanding.

## Dependencies

- The project requires the [Google Protocol Buffers](https://developers.google.com/protocol-buffers/) compiler. A guide on how to install it is found [here](https://fetchai.github.io/oef-sdk-python/user/install.html#protobuf-compiler).
- All python specific dependencies are specified in the Pipfile.

## Preliminaries

- Create and launch a virtual environment:
	```
	pipenv --python 3.6.8 && pipenv shell
	```	

- Install the package:
	```
	python3 setup.py install 
	```

- In a different terminal window launch an OEF Node. You can find out how to do it [here](https://fetchai.github.io/oef-sdk-python/user/oef-node.html).

## Agents

- `controller`: the agent that handles the competition;
- `baseline`: a baseline agent with a trivial strategy.



