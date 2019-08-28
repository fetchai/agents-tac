# Docker agent image

Lightweight Docker image for agent execution, based on [`python:3.7-alpine`](https://hub.docker.com/r/jfloff/alpine-python/).

## Build

From the root of the repository:

    ./docker-agent-image/scripts/docker-build.sh
    
## Run

    ./docker-agent-image/scripts/docker-run.sh -- sh
    
## Example

- run an OEF Node:
```
curl https://raw.githubusercontent.com/fetchai/oef-search-pluto/master/scripts/node_config.json > node_config.json

docker run -it -v $(pwd):/config -v $(pwd):/app/fetch-logs \
  -p 20000:20000 -p 10000:10000 \
  -p 40000:40000 -p 7500 \
  fetchai/oef-search:latest /config/node_config.json
```
- Run a Visdom server:
```
pipenv shell
python -m visdom.server
```
- Run the controller: 
```
./docker-agent-image/scripts/docker-run.sh --network host -- sh
python tac/agents/controller/agent.py --nb-agents 2  --dashboard 
```
- Run Agent 1: 
```
./docker-agent-image/scripts/docker-run.sh --network host -- sh
python templates/v1/basic.py --name agent1 
```
- Run Agent 2: 
```
./docker-agent-image/scripts/docker-run.sh --network host -- sh
python templates/v1/basic.py --name agent2 
```
