# Docker development image

Docker image for development.

## Build

From the root of the repository:

    ./docker-tac-develop/scripts/docker-build.sh
    
## Run

    ./docker-tac-develop/scripts/docker-run.sh -- /bin/bash
    
## Examples

Check if you have an OEF Node running. Then:

    ./docker-tac-develop/scripts/docker-run.sh --network="host" -- /bin/bash
    
The `--network="host"` flag is needed in order to connect the docker image to 
`localhost`.    

Then:

    python3 examples/baseline_demo/tac_agent_spawner.py 2