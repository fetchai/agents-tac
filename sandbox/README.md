# Sandbox

This folders contains the `docker-compose` scripts to run an ensemble of 
Docker image to support TAC.

Please install [Docker](https://www.docker.com/) and [Docker Compose](https://docs.docker.com/compose/).

## Build

    docker-compose build

## Configuration

To configure the execution of TAC, you can tune the following parameters:
- `NB_AGENTS` is the minimum number of agents required for the competition to start.
- `NB_GOODS` is the number of types of goods available for trade in the competition.
- `NB_BASELINE_AGENTS` is the number of baseline agents spawned in the TAC instance. 
- `REGISTRATION_TIME` is the time (in seconds) that the controller waits for agent registrations for TAC. 

To change the parameters:

- Either, export the variable before the command:

      export NB_BASELINE_AGENTS=2
      docker-compose up

- Or, set the variable in one command:

      NB_BASELINE_AGENTS=2 docker-compose up

- Or, specify the values in the [`.env`](.env) file and then run command:
	  docker-compose up


To double-check whether the variable has been set successfully, use:

    docker-compose config

### Run TAC with baseline agents only

To run a TAC instance with only baseline agents, set `NB_AGENTS` equal to `NB_BASELINE_AGENTS`.
`REGISTRATION_TIME` should be high enough (e.g. 5-10 seconds) to allow all the baseline agents to register to TAC.
    
Notice: if `NB_AGENTS` > `NB_BASELINE_AGENTS`, there are not enough agents to start the TAC.
    
### Run TAC with baseline agents and your own agent implementation(s)

If you want to include your own agents:  

- Set up an OEF-Node, a Controller agent and a list of baseline agents:

      docker-compose up
      
- Connect your agent to `localhost:3333`, e.g.:

      python3 ../scripts/template_basic.py
      
In this case, be careful of the values of `NB_AGENTS` and `NB_BASELINE_AGENTS`:
- if `NB_AGENTS` <= `NB_BASELINE_AGENTS`, the competition might start even though you didn't register your agent;
- if  `NB_AGENTS` > `NB_BASELINE_AGENTS`, the competition waits until `NB_AGENTS` = `NB_BASELINE_AGENTS` agents to start.
  But if you're planning to run only one of your own agents, the difference should be just `1`, e.g. `NB_AGENTS=10` and `NB_BASELINE_AGENTS=9`. 
  